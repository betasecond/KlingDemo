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

        For each keyframe description provided, this method submits an image
        generation task, waits for completion, downloads the resulting image,
        and saves it locally.

        Args:
            keyframes: A list of KeyframeData objects, each containing parameters
                     like prompt, negative_prompt, aspect_ratio, etc.
            reference_image_path: Path to the reference image file (e.g., face/subject).
            output_dir: Directory where the generated keyframe images will be saved.
                      Defaults to 'output_keyframes'. Created if it doesn't exist.
            model_name: The name of the generation model to use. Defaults to 'kling-v1-5'.
            image_reference: Type of reference the image provides (FACE or SUBJECT).
                           Defaults to ImageReference.FACE.
            image_fidelity: Adherence strength to the reference image (0.0 to 1.0).
                          Defaults to 0.6.
            human_fidelity: Adherence strength to human features (0.0 to 1.0).
                          Defaults to 0.8.

        Returns:
            A list of GeneratedKeyframeInfo objects, each containing details
            about a successfully generated keyframe image.
            Frames that fail during generation are logged and skipped.

        Raises:
            FileNotFoundError: If the reference_image_path does not point to a valid file.
            IOError: If there's an error reading the reference image.
        """
        # --- Input Validation and Setup ---
        if not isinstance(reference_image_path, Path):
            reference_image_path = Path(reference_image_path)
        if not isinstance(output_dir, Path):
            output_dir = Path(output_dir)

        if not reference_image_path.is_file():
            raise FileNotFoundError(f"Reference image not found: {reference_image_path}")

        try:
            # Ensure the output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured output directory exists: {output_dir}")
        except OSError as e:
            # Handle potential permission errors during directory creation
            raise IOError(f"Could not create output directory {output_dir}: {e}") from e

        try:
            # Encode the reference image to base64
            encoded_image = encode_image_to_base64(reference_image_path)
        except ImageError as e:
            # Catch specific image errors for better debugging
            raise IOError(f"Failed to read or encode reference image {reference_image_path}: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors
            raise IOError(f"Unexpected error processing reference image {reference_image_path}: {e}") from e

        # --- Process Keyframes ---
        generated_results: List[GeneratedKeyframeInfo] = []
        for i, frame_data in enumerate(keyframes, 1):
            logger.info(f"Processing keyframe {i}/{len(keyframes)} (Original frame num: {frame_data.frame_number or 'N/A'})...")

            # Prepare the image generation request using data from KeyframeData
            request = ImageGenerationRequest(
                model_name=model_name,
                prompt=frame_data.prompt or "",
                # Don't include negative_prompt for image-to-image generation as it's not supported
                image=encoded_image,
                image_reference=image_reference,
                image_fidelity=image_fidelity,
                human_fidelity=human_fidelity,
                n=1,  # Generate one image per keyframe
                aspect_ratio=frame_data.aspect_ratio or "16:9",
                seed=frame_data.seed,
                # Include other supported parameters that might be in frame_data
                # Not including steps as it's not documented in the API
            )

            try:
                # --- API Interaction ---
                # 1. Submit task
                task_response = self.client.create_image_generation_task(request)
                task_id = task_response.task_id
                logger.info(f"Keyframe {i}: Task created with ID: {task_id}")

                # 2. Wait for completion
                completed_task = self.client.wait_for_image_generation_completion(task_id)
                logger.info(f"Keyframe {i}: Task {task_id} completed with status: {completed_task.task_status}")

                # --- Process Result ---
                if (completed_task.task_status == TaskStatus.SUCCEED and 
                    completed_task.task_result and
                    completed_task.task_result.images and 
                    len(completed_task.task_result.images) > 0):

                    image_info = completed_task.task_result.images[0]
                    image_url = image_info.url

                    # Define local path using pathlib
                    image_filename = f"keyframe_{i:04d}.jpg"  # Use padding for sorting
                    local_image_path = output_dir / image_filename

                    # 3. Download the image using project's utility
                    try:
                        download_image(image_url, local_image_path)
                        logger.info(f"Downloaded image to {local_image_path}")
                    except ImageError as e:
                        logger.error(f"Keyframe {i}: Failed to download image from {image_url}: {e}")
                        continue

                    # --- Store Result ---
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
                        logger.error(f"Keyframe {i}: Failed to validate generated info (URL='{image_url}'): {ve}")
                        # Continue to the next keyframe

                else:
                    # Log failure reason more specifically if possible
                    failure_reason = getattr(completed_task, 'task_error', None) or "No image data in result"
                    logger.warning(f"Keyframe {i} (Task {task_id}): Generation failed or produced no image. Status: {completed_task.task_status}. Reason: {failure_reason}")

            except KlingAPIError as e:
                logger.error(f"Keyframe {i}: API error during generation: {e}")
                continue
            except NetworkError as e:
                logger.error(f"Keyframe {i}: Network error during generation or download: {e}")
                continue
            except Exception as e:
                logger.error(f"Keyframe {i}: An unexpected error occurred: {e}", exc_info=True)
                continue

        logger.info(f"Finished processing keyframes. Generated {len(generated_results)} images.")
        return generated_results
    
    def generate_keyframes_text_only(
        self,
        keyframes: List[KeyframeData],
        output_dir: Path = Path("output_keyframes"),
        model_name: str = "kling-v1-5",
    ) -> List[GeneratedKeyframeInfo]:
        """
        Generates keyframe images based only on text descriptions using the Kling API.
        
        This method is similar to generate_keyframes_with_reference but doesn't use a reference image,
        making it suitable for text-to-image generation.
        
        Args:
            keyframes: A list of KeyframeData objects
            output_dir: Directory to save the generated images
            model_name: The model to use for generation
            
        Returns:
            A list of GeneratedKeyframeInfo objects
            
        Raises:
            IOError: If output directory cannot be created
        """
        if not isinstance(output_dir, Path):
            output_dir = Path(output_dir)
            
        try:
            # Ensure the output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured output directory exists: {output_dir}")
        except OSError as e:
            raise IOError(f"Could not create output directory {output_dir}: {e}") from e
            
        # --- Process Keyframes ---
        generated_results: List[GeneratedKeyframeInfo] = []
        for i, frame_data in enumerate(keyframes, 1):
            logger.info(f"Processing keyframe {i}/{len(keyframes)} (Original frame num: {frame_data.frame_number or 'N/A'})...")
            
            # For text-to-image generation, we can include negative_prompt
            request = ImageGenerationRequest(
                model_name=model_name,
                prompt=frame_data.prompt or "",
                negative_prompt=frame_data.negative_prompt,
                n=1,
                aspect_ratio=frame_data.aspect_ratio or "16:9",
                seed=frame_data.seed,
            )
            
            try:
                # Submit task
                task_response = self.client.create_image_generation_task(request)
                task_id = task_response.task_id
                logger.info(f"Keyframe {i}: Text-to-image task created with ID: {task_id}")
                
                # Wait for completion
                completed_task = self.client.wait_for_image_generation_completion(task_id)
                logger.info(f"Keyframe {i}: Text-to-image task {task_id} completed with status: {completed_task.task_status}")
                
                # Process result - same logic as above
                if (completed_task.task_status == TaskStatus.SUCCEED and 
                    completed_task.task_result and
                    completed_task.task_result.images and 
                    len(completed_task.task_result.images) > 0):
                    
                    image_info = completed_task.task_result.images[0]
                    image_url = image_info.url
                    
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
                    logger.warning(f"Keyframe {i} (Task {task_id}): Text-to-image generation failed. Status: {completed_task.task_status}. Reason: {failure_reason}")
                    
            except (KlingAPIError, NetworkError) as e:
                logger.error(f"Keyframe {i}: API or network error during text-to-image generation: {e}")
                continue
            except Exception as e:
                logger.error(f"Keyframe {i}: Unexpected error during text-to-image generation: {e}", exc_info=True)
                continue
                
        logger.info(f"Finished processing text-to-image keyframes. Generated {len(generated_results)} images.")
        return generated_results


