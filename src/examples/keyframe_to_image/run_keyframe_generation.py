# klingdemo/scripts/run_keyframe_generation.py  (Suggested new file name and location)

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional

from loguru import logger

from examples.keyframe_to_image.create_keyframe import GeneratedKeyframeInfo, KeyframeGenerator
from examples.keyframe_to_image.keyframe_parser import KeyframeData, parse_keyframe_file
# Using project's existing utilities
from klingdemo.api import KlingAPIClient, KlingAPIError, NetworkError
from klingdemo.utils import load_config, setup_logging, ConfigurationError
from klingdemo.models import ImageReference

# --- Constants ---
DEFAULT_KEYFRAMES_FILENAME = "keyframes.txt"
DEFAULT_INPUT_DIR = Path("Input")
DEFAULT_OUTPUT_DIR = Path("output_keyframes")
DEFAULT_MODEL_NAME = "kling-v1-5"
DEFAULT_IMAGE_FIDELITY = 0.5 # Default fidelity if reference image is used

def main() -> None:
    """
    Command-line interface for generating keyframe images using the Kling API.

    Parses keyframe descriptions from a file, optionally uses a reference image,
    calls the appropriate Kling API client method to generate images,
    and saves the results.
    """
    parser = argparse.ArgumentParser(
        description="Generate keyframe images using the Kling API."
    )
    parser.add_argument(
        "--keyframes-file",
        type=Path,
        default=DEFAULT_INPUT_DIR / DEFAULT_KEYFRAMES_FILENAME,
        help=f"Path to the .txt file containing keyframe descriptions. "
             f"Default: {DEFAULT_INPUT_DIR / DEFAULT_KEYFRAMES_FILENAME}"
    )
    parser.add_argument(
        "--reference-image",
        type=Path,
        default=None,
        help="Optional path to a reference image file (e.g., for face or subject)."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save the generated keyframe images. "
             f"Default: {DEFAULT_OUTPUT_DIR}"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help=f"Name of the model to use for generation. Default: {DEFAULT_MODEL_NAME}"
    )
    parser.add_argument(
        "--image-fidelity",
        type=float,
        default=DEFAULT_IMAGE_FIDELITY,
        help=f"Image fidelity strength when using a reference image (0.0 to 1.0). "
             f"Default: {DEFAULT_IMAGE_FIDELITY}"
    )
    parser.add_argument(
        "--image-reference",
        type=str,
        default="FACE",
        choices=["FACE", "SUBJECT"],
        help="Type of reference the image provides (face or subject features). Default: FACE"
    )
    parser.add_argument(
        "--human-fidelity",
        type=float,
        default=0.8,
        help="Human fidelity strength when using face reference (0.0 to 1.0). Default: 0.8"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Path to a specific .env file to load"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level"
    )

    args = parser.parse_args()

    # --- Setup ---
    setup_logging(args.log_level) # Use project's existing logging setup

    try:
        # Use the project's existing config loading mechanism
        config = load_config(args.env_file)
        logger.info("Configuration loaded successfully")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # --- Initialize API Client ---
    try:
        client = KlingAPIClient(
            access_key=config.get('access_key'),
            secret_key=config.get('secret_key'),
            base_url=config.get('api_base_url', 'https://api.klingai.com'),
            timeout=config.get('timeout', 60),
            max_retries=config.get('max_retries', 3),
        )
        logger.info("Kling API Client initialized successfully.")
        
        # Initialize our KeyframeGenerator with the client
        generator = KeyframeGenerator(client)
        logger.info("KeyframeGenerator initialized")
    except Exception as e:
         logger.error(f"Failed to initialize Kling API Client: {e}")
         sys.exit(1)

    # --- Prepare Output Directory ---
    output_dir: Path = args.output_dir
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured output directory exists: {output_dir}")
    except OSError as e:
        logger.error(f"Failed to create output directory {output_dir}: {e}")
        sys.exit(1)

    # --- Parse Keyframes ---
    keyframes_file: Path = args.keyframes_file
    try:
        if not keyframes_file.is_file():
             raise FileNotFoundError(f"Keyframes file not found: {keyframes_file}")
        keyframes_data: List[KeyframeData] = parse_keyframe_file(keyframes_file)
        if not keyframes_data:
            logger.warning(f"No keyframes found or parsed from {keyframes_file}. Exiting.")
            sys.exit(0) # Not necessarily an error, just nothing to do
        logger.info(f"Successfully parsed {len(keyframes_data)} keyframes from {keyframes_file}")
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(1)
    except Exception as e: # Catch parsing errors (e.g., validation errors if parser raises them)
        logger.error(f"Failed to parse keyframes file {keyframes_file}: {e}", exc_info=True)
        sys.exit(1)

    # --- Generate Keyframes ---
    generated_results: List[GeneratedKeyframeInfo] = []
    reference_image_path: Optional[Path] = args.reference_image
    use_reference_image = reference_image_path is not None and reference_image_path.is_file()

    # Convert string image reference to enum
    image_reference = ImageReference.FACE if args.image_reference == "FACE" else ImageReference.SUBJECT

    generation_successful = False
    try:
        if use_reference_image:
            logger.info(f"Attempting to generate keyframes using reference image: {reference_image_path}")
            # Use generate_keyframes_with_reference for image+text generation
            generated_results = generator.generate_keyframes_with_reference(
                keyframes=keyframes_data,
                reference_image_path=reference_image_path,
                output_dir=output_dir,
                model_name=args.model,
                image_reference=image_reference,
                image_fidelity=args.image_fidelity,
                human_fidelity=args.human_fidelity,
            )
            generation_successful = True
        else:
            if reference_image_path: # Path provided but file not found
                logger.warning(f"Reference image specified but not found at: {reference_image_path}. Proceeding with text-only generation.")
            logger.info("Generating keyframes using text prompts only.")
            # Use text-only method
            generated_results = generator.generate_keyframes_text_only(
                keyframes=keyframes_data,
                output_dir=output_dir,
                model_name=args.model,
            )
            generation_successful = True

    except KlingAPIError as e:
        # Handle specific API errors, like "No face detected" for fallback
        if use_reference_image and "No face detected" in str(e): # Check if fallback is applicable
             logger.warning(f"No face detected in reference image {reference_image_path}. Attempting fallback to text-only generation.")
             try:
                 # Fallback to text-only generation
                 generated_results = generator.generate_keyframes_text_only(
                     keyframes=keyframes_data,
                     output_dir=output_dir,
                     model_name=args.model,
                 )
                 generation_successful = True # Fallback succeeded
                 logger.info("Successfully generated keyframes using text-only fallback.")
             except (KlingAPIError, NetworkError, Exception) as fallback_e:
                 logger.error(f"Text-only fallback generation also failed: {fallback_e}", exc_info=True)
        else:
            # Handle other API or Network errors
            logger.error(f"API or Network error during keyframe generation: {e}", exc_info=True)
    except FileNotFoundError as e:
         # This might occur if the reference image exists initially but disappears
         logger.error(f"File not found during generation process: {e}", exc_info=True)
    except Exception as e:
        # Catch any other unexpected errors during the generation process
        logger.error(f"An unexpected error occurred during keyframe generation: {e}", exc_info=True)

    # --- Report Results ---
    if generated_results:
        print("\n--- Generated Keyframe Results ---")
        for result in generated_results:
            # Access attributes from the Pydantic model
            print(f"Keyframe (Original Frame Num: {result.frame_id}):")
            print(f"  Task ID:    {result.task_id}")
            print(f"  Image URL:  {result.image_url}")
            print(f"  Local Path: {result.local_path}")
        print(f"\nSuccessfully generated {len(generated_results)} keyframe images in {output_dir}.")
    elif generation_successful:
         # Process completed but yielded no results (e.g., API returned empty list)
         logger.warning("Keyframe generation process completed, but no results were returned.")
         print("\nKeyframe generation process completed, but no images were successfully generated.")
    else:
        # Generation failed before producing any results
        print("\nKeyframe generation failed. Check logs for details.")
        sys.exit(1) # Exit with error code if the core process failed

if __name__ == "__main__":
    main()