import os
import sys
import glob
import json
import shutil
import requests
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dotenv import load_dotenv

from klingdemo.api import KlingAPIClient
from klingdemo.models import ImageToVideoRequest, TaskStatus
from klingdemo.utils import (
    encode_image_to_base64,
    load_config,
    setup_logging,
    ConfigurationError,
)
from loguru import logger


class DifyProcessingError(Exception):
    """Exception raised for errors in Dify API processing."""
    pass


def load_dify_config() -> Dict[str, str]:
    """
    Load Dify configuration from environment variables.
    
    Returns:
        Dictionary containing Dify configuration
        
    Raises:
        ConfigurationError: If required environment variables are missing
    """
    dify_api_url = os.getenv("DIFY_API_URL")
    dify_api_key = os.getenv("DIFY_API_KEY")
    workflow_id = os.getenv("DIFY_WORKFLOW_ID")
    
    if not dify_api_url:
        raise ConfigurationError("DIFY_API_URL environment variable is required")
    if not dify_api_key:
        raise ConfigurationError("DIFY_API_KEY environment variable is required")
    if not workflow_id:
        raise ConfigurationError("DIFY_WORKFLOW_ID environment variable is required")
    
    return {
        "api_url": dify_api_url,
        "api_key": dify_api_key,
        "workflow_id": workflow_id,
    }


def call_dify_workflow(description: str) -> str:
    """
    Call the Dify workflow to process the description text.
    
    Args:
        description: Input image description text
        
    Returns:
        Processed description text
        
    Raises:
        DifyProcessingError: If the Dify API call fails
    """
    try:
        config = load_dify_config()
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "workflow_id": config["workflow_id"],
            "inputs": {"P_dsp": description},
            "response_mode": "blocking",
            "user": "user-123"
        }

        logger.debug(f"Calling Dify API: {config['api_url']}")
        response = requests.post(
            config["api_url"], 
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        logger.debug(f"Dify API raw response: {response.text}")
        response.raise_for_status()
        
        result = response.json()
        processed_description = result.get("data", {}).get("outputs", {}).get("V_dsp", "")
        
        if not processed_description:
            raise DifyProcessingError("Dify workflow did not return valid output (V_dsp field)")
        
        return processed_description
    
    except requests.RequestException as e:
        logger.error(f"Failed to call Dify workflow: {e}")
        raise DifyProcessingError(f"Failed to call Dify API: {e}")


def process_image_to_video(image_path: str, prompt: str, **kwargs) -> str:
    """
    Process image-to-video conversion using KlingDemo API.
    
    Args:
        image_path: Path to input image
        prompt: Processed description text
        **kwargs: Additional parameters to pass to ImageToVideoRequest
        
    Returns:
        Path to saved generated video
    """
    # Get configured output directory
    output_dir = os.getenv("KLING_OUTPUT_DIR", "./output")
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Load KlingDemo configuration
        config = load_config()
        
        # Create API client with access_key and secret_key instead of api_key
        client = KlingAPIClient(
            access_key=config.get('access_key'),
            secret_key=config.get('secret_key'),
            base_url=config.get('api_base_url', 'https://api.klingai.com'),
            timeout=config.get('timeout', 60),
            max_retries=config.get('max_retries', 3),
        )
        
        # Prepare image data
        logger.info(f"Processing input image: {image_path}")
        # Check if URL
        if image_path.startswith(('http://', 'https://')):
            image = image_path
        else:
            # Encode local file to base64
            image = encode_image_to_base64(image_path)
            logger.debug("Image encoded to base64")
        
        # Get parameter values from kwargs or use defaults
        model_name = kwargs.get("model_name", "kling-v1-6")
        cfg_scale = kwargs.get("cfg_scale", 0.5)
        mode = kwargs.get("mode", "pro")
        duration = kwargs.get("duration", "5")
        
        # Prepare request
        request = ImageToVideoRequest(
            model_name=model_name,
            image=image,
            prompt=prompt,
            cfg_scale=cfg_scale,
            mode=mode,
            duration=duration,
            external_task_id=f"dify_integration_{int(__import__('time').time())}",
        )
        
        # Submit task
        logger.info("Submitting image-to-video generation task...")
        task = client.create_image_to_video_task(request)
        logger.info(f"Task created with ID: {task.task_id}")
        
        # Wait for task to complete
        logger.info("Waiting for task to complete...")
        timeout = int(kwargs.get("timeout", os.getenv("KLING_API_TIMEOUT", "1000")))
        task = client.wait_for_task_completion(
            task.task_id,
            check_interval=5,
            timeout=timeout
        )
        
        # Process results
        if task.task_status == TaskStatus.SUCCEED and task.task_result:
            # Save video
            videos = task.task_result.videos
            if not videos:
                raise RuntimeError("Task succeeded but no videos were returned")
            
            video_url = videos[0].url
            return save_video(str(video_url), image_path, output_dir)
        else:
            error_msg = task.task_status_msg or f"Task failed with status: {task.task_status}"
            raise RuntimeError(error_msg)
            
    except Exception as e:
        logger.error(f"Failed to process image-to-video: {e}")
        raise


def save_video(video_url: str, image_path: str, output_dir: str) -> str:
    """
    Download video and rename based on original image name.
    
    Args:
        video_url: Video URL
        image_path: Original image path
        output_dir: Output directory
        
    Returns:
        Saved video file path
    """
    import requests
    import time
    
    # Extract base name from image path
    image_name = Path(image_path).stem
    target_video_path = os.path.join(output_dir, f"{image_name}.mp4")
    
    # Download video
    logger.info(f"Downloading video from {video_url}")
    response = requests.get(video_url, stream=True)
    response.raise_for_status()
    
    # Save video
    with open(target_video_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    logger.info(f"Video saved to {target_video_path}")
    return target_video_path


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments using argparse.
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="KlingDemo external integration with Dify for image-to-video generation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Description input options
    description_group = parser.add_mutually_exclusive_group(required=True)
    description_group.add_argument(
        "--description", "-d", 
        type=str,
        help="Text description for video generation"
    )
    description_group.add_argument(
        "--description-file", "-df",
        type=str,
        help="Path to a text file containing the description"
    )
    
    # Image input options
    parser.add_argument(
        "--image", "-i",
        type=str,
        required=True,
        help="Path to the input image file or image URL"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=os.getenv("KLING_OUTPUT_DIR", "./output"),
        help="Directory to save the generated video"
    )
    
    # Configuration options
    parser.add_argument(
        "--env-file", "-e",
        type=str,
        default=None,
        help="Path to a specific .env file to load"
    )
    
    # Advanced options
    advanced_group = parser.add_argument_group("Advanced Options")
    advanced_group.add_argument(
        "--model",
        type=str,
        default="kling-v1-6",
        choices=["kling-v1", "kling-v1-5", "kling-v1-6"],
        help="Model to use for video generation"
    )
    advanced_group.add_argument(
        "--mode",
        type=str,
        default="pro",
        choices=["std", "pro"],
        help="Generation mode to use"
    )
    advanced_group.add_argument(
        "--duration",
        type=str,
        default="5",
        choices=["5", "10"],
        help="Video duration in seconds"
    )
    advanced_group.add_argument(
        "--cfg-scale",
        type=float,
        default=0.5,
        help="Generation freedom factor (0-1)"
    )
    advanced_group.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("KLING_API_TIMEOUT", "1000")),
        help="Maximum time to wait for task completion in seconds"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level"
    )
    
    return parser.parse_args()


def get_description(args: argparse.Namespace) -> str:
    """
    Get the description from either direct input or a file.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Description text
    
    Raises:
        FileNotFoundError: If the description file doesn't exist
        ValueError: If the description file is empty
    """
    if args.description:
        return args.description
    
    if args.description_file:
        if not os.path.exists(args.description_file):
            raise FileNotFoundError(f"Description file not found: {args.description_file}")
        
        with open(args.description_file, 'r', encoding='utf-8') as f:
            description = f.read().strip()
        
        if not description:
            raise ValueError(f"Description file is empty: {args.description_file}")
        
        logger.info(f"Loaded description from file: {args.description_file}")
        return description
    
    # This should never happen due to mutual exclusion in argparse
    raise ValueError("No description provided")


def validate_image_path(image_path: str) -> bool:
    """
    Validate that the image path is either a valid file or URL.
    
    Args:
        image_path: Path to image or URL
    
    Returns:
        True if valid, False otherwise
    """
    if image_path.startswith(('http://', 'https://')):
        return True
    
    return os.path.isfile(image_path)


def load_environment(env_file: Optional[str] = None) -> None:
    """
    Load environment variables from .env files.
    
    Args:
        env_file: Optional specific .env file path
    """
    # If a specific env file is provided, try to load it first
    if env_file:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"Loaded environment variables from {env_file}")
            return
        else:
            logger.warning(f"Specified .env file not found: {env_file}")
    
    # Otherwise, try common locations
    env_paths = ['.env', '../.env', '../../.env']
    for path in env_paths:
        if os.path.exists(path):
            load_dotenv(path)
            logger.info(f"Loaded environment variables from {path}")
            return
    
    logger.warning("No .env file found, using system environment variables")


def main():
    """Main function."""
    try:
        # Parse command-line arguments
        args = parse_args()
        
        # Set up logging with custom format
        setup_logging(args.log_level)
        
        # Load environment variables
        load_environment(args.env_file)
        
        # Validate image path
        if not validate_image_path(args.image):
            logger.error(f"Invalid image path: {args.image}")
            sys.exit(1)
        
        # Get description (either direct or from file)
        try:
            input_description = get_description(args)
            logger.debug(f"Using description: {input_description[:50]}..." if len(input_description) > 50 else input_description)
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            sys.exit(1)
        
        # Call Dify workflow to process description
        logger.info("Calling Dify workflow to process description...")
        processed_description = call_dify_workflow(input_description)
        logger.info(f"Dify workflow output: {processed_description}")
        
        # Create output directory if it doesn't exist
        os.makedirs(args.output, exist_ok=True)

        # Use KlingDemo API to generate video
        logger.info("Calling KlingDemo API to generate video...")
        # Pass the additional parameters to the process function
        video_path = process_image_to_video(
            image_path=args.image,
            prompt=processed_description
        )
        
        logger.info(f"Video generation successful, saved to: {video_path}")
        
    except DifyProcessingError as e:
        logger.error(f"Dify processing error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()