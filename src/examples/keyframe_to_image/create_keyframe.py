from pathlib import Path
from typing import List, Dict, Any, Optional
import time
from pydantic import BaseModel, Field, HttpUrl, ValidationError
from loguru import logger

from klingdemo.api import KlingAPIClient, KlingAPIError, NetworkError
from klingdemo.models import TaskStatus
from klingdemo.models.image_generation import (
    ImageGenerationRequest,
    ImageGenerationTaskResponseData,
    ImageReference,
)
from klingdemo.utils.image import encode_image_to_base64, download_image, ImageError

from examples.keyframe_to_image.keyframe_parser import KeyframeData


# --- Pydantic Model for Return Structure ---

class GeneratedKeyframeInfo(BaseModel):
    """
    Represents the information for a single generated keyframe image.
    """
    frame_id: int = Field(..., description="Sequential ID of the keyframe processed (starting from 1).")
    task_id: str = Field(..., description="The task ID returned by the image generation API.")
    image_url: HttpUrl = Field(..., description="The URL of the generated image.")
    local_path: Path = Field(..., description="The local path where the generated image was saved.")


# --- KeyframeGenerator Class ---

class KeyframeGenerator:
    """
    Class responsible for generating keyframe images based on descriptions and reference images.
    Uses the KlingDemo API Client to interact with the image generation services.
    """
    
    def __init__(self, client: KlingAPIClient):
        """
        Initialize the KeyframeGenerator with a KlingAPIClient instance.
        
        Args:
            client: An initialized KlingAPIClient with valid authentication
        """
        self.client = client

    def _generate_keyframes(
        self,
        keyframes: List[KeyframeData],
        output_dir: Path,
        model_name: str,
        image: Optional[str] = None,
        image_reference: Optional[ImageReference] = None,
        image_fidelity: Optional[float] = None,
        human_fidelity: Optional[float] = None,
    ) -> List[GeneratedKeyframeInfo]:
        """
        Shared logic for generating keyframes, used by both text-only and reference-based methods.

        Args:
            keyframes: A list of KeyframeData objects.
            output_dir: Directory to save the generated images.
            model_name: The model to use for generation.
            image: Base64-encoded reference image (optional).
            image_reference: Type of reference the image provides (optional).
            image_fidelity: Adherence strength to the reference image (optional).
            human_fidelity: Adherence strength to human features (optional).

        Returns:
            A list of GeneratedKeyframeInfo objects.
        """
        generated_results: List[GeneratedKeyframeInfo] = []

        for i, frame_data in enumerate(keyframes, 1):
            logger.info(f"Processing keyframe {i}/{len(keyframes)} (Original frame num: {frame_data.frame_number or 'N/A'})...")

            # Prepare the image generation request
            request = ImageGenerationRequest(
                model_name=model_name,
                prompt=frame_data.prompt or "",
                negative_prompt=frame_data.negative_prompt if image is None else None,
                image=image,
                image_reference=image_reference,
                image_fidelity=image_fidelity,
                human_fidelity=human_fidelity,
                n=1,
                aspect_ratio=frame_data.aspect_ratio or "16:9",
                seed=frame_data.seed,
            )

            try:
                # Submit task
                task_response = self.client.create_image_generation_task(request)
                task_id = task_response.task_id
                logger.info(f"Keyframe {i}: Task created with ID: {task_id}")

                # Wait for completion
                completed_task = self.client.wait_for_image_generation_completion(task_id)
                logger.info(f"Keyframe {i}: Task {task_id} completed with status: {completed_task.task_status}")

                # Process result
                if (completed_task.task_status == TaskStatus.SUCCEED and 
                    completed_task.task_result and
                    completed_task.task_result.images and 
                    len(completed_task.task_result.images) > 0):

                    image_info = completed_task.task_result.images[0]
                    image_url = image_info.url

                    # Define local path
                    image_filename = f"keyframe_{i:04d}.jpg"
                    local_image_path = output_dir / image_filename

                    try:
                        download_image(image_url, local_image_path)
                        logger.info(f"Downloaded image to {local_image_path}")
                    except ImageError as e:
                        logger.error(f"Keyframe {i}: Failed to download image from {image_url}: {e}")
                        continue

                    try:
                        result_info = GeneratedKeyframeInfo(
                            frame_id=i,
                            task_id=task_id,
                            image_url=image_url,
                            local_path=local_image_path
                        )
                        generated_results.append(result_info)
                        logger.success(f"Keyframe {i}: Successfully generated and saved to {local_image_path}")
                    except ValidationError as ve:
                        logger.error(f"Keyframe {i}: Failed to validate generated info: {ve}")
                        continue

                else:
                    failure_reason = getattr(completed_task, 'task_error', None) or "No image data in result"
                    logger.warning(f"Keyframe {i} (Task {task_id}): Generation failed. Status: {completed_task.task_status}. Reason: {failure_reason}")

            except (KlingAPIError, NetworkError) as e:
                logger.error(f"Keyframe {i}: API or network error: {e}")
                continue
            except Exception as e:
                logger.error(f"Keyframe {i}: Unexpected error: {e}", exc_info=True)
                continue

        logger.info(f"Finished processing keyframes. Generated {len(generated_results)} images.")
        return generated_results

    def generate_keyframes_with_reference(
        self,
        keyframes: List[KeyframeData],
        reference_image_path: Path,
        output_dir: Path = Path("output_keyframes"),
        model_name: str = "kling-v1-5",
        image_reference: ImageReference = ImageReference.FACE,
        image_fidelity: float = 0.6,
        human_fidelity: float = 0.8,
    ) -> List[GeneratedKeyframeInfo]:
        """
        Generates keyframe images based on descriptions and a reference image using the Kling API.
        """
        if not reference_image_path.is_file():
            raise FileNotFoundError(f"Reference image not found: {reference_image_path}")

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured output directory exists: {output_dir}")
        except OSError as e:
            raise IOError(f"Could not create output directory {output_dir}: {e}") from e

        try:
            encoded_image = encode_image_to_base64(reference_image_path)
        except ImageError as e:
            raise IOError(f"Failed to encode reference image: {e}") from e

        return self._generate_keyframes(
            keyframes=keyframes,
            output_dir=output_dir,
            model_name=model_name,
            image=encoded_image,
            image_reference=image_reference,
            image_fidelity=image_fidelity,
            human_fidelity=human_fidelity,
        )

    def generate_keyframes_text_only(
        self,
        keyframes: List[KeyframeData],
        output_dir: Path = Path("output_keyframes"),
        model_name: str = "kling-v1-5",
    ) -> List[GeneratedKeyframeInfo]:
        """
        Generates keyframe images based only on text descriptions using the Kling API.
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured output directory exists: {output_dir}")
        except OSError as e:
            raise IOError(f"Could not create output directory {output_dir}: {e}") from e

        return self._generate_keyframes(
            keyframes=keyframes,
            output_dir=output_dir,
            model_name=model_name,
        )


