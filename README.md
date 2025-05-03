# KlingDemo

A Python client library and demo application for Kling AI's Image-to-Video and Image Generation APIs. This project provides a well-structured, strongly-typed interface to the Kling AI APIs, using best practices for error handling, data validation, and configuration management.

## Features

- **Full API Coverage**: Implements all capabilities of the Kling AI Image-to-Video and Image Generation APIs
- **JWT Authentication**: Uses JWT-based authentication as specified in the Kling AI API documentation
- **Type Safety**: Uses Pydantic for input validation and type checking
- **Robust Error Handling**: Comprehensive error handling with descriptive error messages
- **Retries and Timeout Support**: Automatic retries for transient errors
- **Token Management**: Automatic JWT token generation and renewal
- **Flexible Configuration**: Environment variable support via dotenv
- **Comprehensive Documentation**: Fully documented code with docstrings and examples
- **Advanced Examples**: Demo scripts showing all API features

## Installation

### Prerequisites

- Python 3.8 or higher
- `uv` (recommended) or `pip` package manager

### Using UV (Recommended)

```bash
uv venv -p python3.8 .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using Pip

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Configuration

The library can be configured using environment variables or a `.env` file. Create a `.env` file in the root of the project with the following content:

```
# Required: Your Kling AI Access Key and Secret Key for JWT authentication
ACCESSKEY_API=your_access_key_here
ACCESSKEY_SECRET=your_secret_key_here

# Optional configurations
KLING_API_BASE_URL=https://api.klingai.com
KLING_TOKEN_EXPIRATION=1800  # JWT token expiration in seconds (30 minutes)
KLING_API_TIMEOUT=60
KLING_API_MAX_RETRIES=3
```

## Authentication

The Kling API uses JWT (JSON Web Token) for authentication. The client automatically:

1. Generates a JWT token using your Access Key and Secret Key
2. Includes the token in the Authorization header for all API requests
3. Refreshes the token when it's about to expire
4. Handles token-related errors and retries with a fresh token when needed

## Basic Usage

### Image-to-Video Generation

```python
from klingdemo.api import KlingAPIClient
from klingdemo.models import ImageToVideoRequest
from klingdemo.utils import load_config, setup_logging

# Set up logging
setup_logging()

# Load configuration
config = load_config()

# Create client with JWT authentication
client = KlingAPIClient(
    access_key=config["access_key"],
    secret_key=config["secret_key"]
)

# Create a request
request = ImageToVideoRequest(
    model_name="kling-v1",
    image="https://example.com/image.jpg",  # URL to image
    prompt="A dog running in the park",
    mode="std",
    duration="5"
)

# Submit the task
task = client.create_image_to_video_task(request)
print(f"Task created with ID: {task.task_id}")

# Wait for task to complete
completed_task = client.wait_for_task_completion(task.task_id)

# Process the result
if completed_task.task_result:
    for video in completed_task.task_result.videos:
        print(f"Generated video: {video.url}")
```

### Image Generation (Text-to-Image and Image-to-Image)

```python
from klingdemo.api import KlingAPIClient
from klingdemo.models import ImageGenerationRequest, ImageReference
from klingdemo.utils import load_config, setup_logging
from pathlib import Path

# Set up logging
setup_logging()

# Load configuration
config = load_config()

# Create client with JWT authentication
client = KlingAPIClient(
    access_key=config["access_key"],
    secret_key=config["secret_key"]
)

# Example 1: Text-to-Image
text_to_img_request = ImageGenerationRequest(
    model_name="kling-v1-5",
    prompt="A beautiful mountain landscape with a lake",
    negative_prompt="blurry, low quality",
    n=1,
    aspect_ratio="16:9"
)

# Submit the task
task = client.create_image_generation_task(text_to_img_request)
print(f"Task created with ID: {task.task_id}")

# Wait for task to complete
completed_task = client.wait_for_image_generation_completion(task.task_id)

# Process the result
if completed_task.task_result:
    for image in completed_task.task_result.images:
        print(f"Generated image: {image.url}")

# Example 2: Image-to-Image (with a reference image)
from klingdemo.examples.image_gen_demo import encode_image_to_base64

# Load and encode a local image
image_path = "path/to/reference_image.jpg"
encoded_image = encode_image_to_base64(image_path)

img_to_img_request = ImageGenerationRequest(
    model_name="kling-v1-5",
    prompt="A person in a sci-fi environment",
    image=encoded_image,
    image_reference=ImageReference.SUBJECT,  # Use the image as a subject reference
    image_fidelity=0.6,  # Higher adherence to reference image
    n=1,
    aspect_ratio="16:9"
)

# Submit and process as before
```

## Demo Scripts

The project includes example scripts that demonstrate how to use the library:

### Basic Image-to-Video Demo

This script demonstrates the basic functionality of creating an image-to-video task:

```bash
python -m src.examples.basic_demo \
    --image path/to/image.jpg \
    --prompt "A cat dancing" \
    --model kling-v1 \
    --mode std \
    --duration 5 \
    --output-dir ./custom_output
```

Key parameters:
- `--image`: Path to input image or URL
- `--prompt`: Text description for the generated video
- `--model`: Model to use (e.g., kling-v1, kling-v1-5, kling-v1-6)
- `--mode`: Generation mode, "std" (standard) or "pro" (professional quality)
- `--duration`: Video duration in seconds (5 or 10)
- `--negative-prompt`: Text describing content to avoid
- `--cfg-scale`: Generation freedom factor (0.0-1.0, higher means more adherence to prompt)
- `--output-dir`: Custom directory to save generated videos (defaults to ./output)
- `--env-file`: Path to custom .env file for configuration

### Advanced Image-to-Video Demo

This script demonstrates advanced features like dynamic masks, static masks, camera control, and image tails:

```bash
# Example with dynamic mask
python -m src.examples.advanced_demo \
    --image path/to/image.jpg \
    --feature dynamic_mask \
    --dynamic-mask path/to/mask.png \
    --trajectories '[{"x": 100, "y": 200}, {"x": 300, "y": 400}]' \
    --prompt "A person walking" \
    --output-dir ./motion_outputs
    
# Example with camera control
python -m src.examples.advanced_demo \
    --image path/to/image.jpg \
    --feature camera_control \
    --camera-type simple \
    --camera-param zoom \
    --camera-value 5.0 \
    --prompt "Zooming into a landscape" \
    --output-dir ./camera_outputs
    
# Example with image tail (start and end frames)
python -m src.examples.advanced_demo \
    --image path/to/start_image.jpg \
    --feature image_tail \
    --image-tail path/to/end_image.jpg \
    --prompt "Morphing from day to night" \
    --output-dir ./morph_outputs
    
# Example with static mask (keeping areas still)
python -m src.examples.advanced_demo \
    --image path/to/image.jpg \
    --feature static_mask \
    --static-mask path/to/mask.png \
    --prompt "Moving background with static foreground" \
    --output-dir ./static_outputs
```

Key parameters (in addition to basic demo parameters):
- `--feature`: The advanced feature to use (dynamic_mask, static_mask, camera_control, image_tail)
- `--dynamic-mask`: Path to dynamic mask image when using dynamic_mask feature
- `--trajectories`: JSON array of coordinate points for motion path when using dynamic_mask
- `--static-mask`: Path to static mask image when using static_mask feature
- `--camera-type`: Camera movement type (simple, down_back, etc.) when using camera_control
- `--camera-param`: Camera parameter to adjust (zoom, pan, tilt, etc.) when using simple camera_control
- `--camera-value`: Value for camera parameter (-10.0 to 10.0) when using simple camera_control
- `--image-tail`: Path to ending image when using image_tail feature

### Image Generation Demo

This script demonstrates how to use the image generation capabilities (both text-to-image and image-to-image):

```bash
# Text-to-Image example
python -m src.examples.image_gen_demo \
    --prompt "A beautiful sunset over mountains" \
    --model kling-v1-5 \
    --aspect-ratio 16:9 \
    --n 2 \
    --output-dir ./sunset_images

# Image-to-Image example with subject reference
python -m src.examples.image_gen_demo \
    --prompt "A cyberpunk version of the person" \
    --model kling-v1-5 \
    --image path/to/reference_image.jpg \
    --image-reference subject \
    --image-fidelity 0.7 \
    --output-dir ./cyberpunk_outputs

# Image-to-Image example with face reference
python -m src.examples.image_gen_demo \
    --prompt "A portrait of the person as a medieval knight" \
    --model kling-v1-5 \
    --image path/to/face_image.jpg \
    --image-reference face \
    --image-fidelity 0.6 \
    --human-fidelity 0.8 \
    --output-dir ./knight_portraits \
    --negative-prompt "modern clothing, glasses"
```

Key parameters:
- `--prompt`: Text description of desired image
- `--model`: Model name (kling-v1, kling-v1-5, kling-v2)
- `--negative-prompt`: Text describing content to avoid (only for text-to-image)
- `--image`: Path to reference image (for image-to-image generation)
- `--image-reference`: How to use the reference image: "face" (human face reference) or "subject" (general subject features)
- `--image-fidelity`: How closely to follow the reference image (0.0-1.0)
- `--human-fidelity`: How closely to follow facial features when using face reference (0.0-1.0)
- `--n`: Number of images to generate (1-9)
- `--aspect-ratio`: Output image dimensions (16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3, 21:9)
- `--seed`: Set specific seed for reproducible results
- `--output-dir`: Custom directory to save generated images

### Keyframe Generation Demo

This script enables generating multiple images based on keyframe descriptions with optional reference image support:

```bash
# Text-to-Image keyframe generation
python -m src.examples.keyframe_to_image.run_keyframe_generation \
    --keyframes-file path/to/keyframes.txt \
    --output-dir ./story_keyframes \
    --model kling-v1-5 \
    --log-level DEBUG

# Image-to-Image keyframe generation with face reference
python -m src.examples.keyframe_to_image.run_keyframe_generation \
    --keyframes-file path/to/character_keyframes.txt \
    --reference-image path/to/face.jpg \
    --image-reference FACE \
    --image-fidelity 0.7 \
    --human-fidelity 0.8 \
    --output-dir ./character_scenes \
    --model kling-v1-5

# Image-to-Image keyframe generation with subject reference
python -m src.examples.keyframe_to_image.run_keyframe_generation \
    --keyframes-file path/to/object_keyframes.txt \
    --reference-image path/to/subject.jpg \
    --image-reference SUBJECT \
    --image-fidelity 0.6 \
    --output-dir ./object_variations
```

Keyframes file format:
```
[Frame 1]
Prompt: A futuristic cityscape at dawn
NegativePrompt: blurry, low quality
AspectRatio: 16:9
Seed: 12345

[Frame 2]
Prompt: A close-up of a cybernetic eye
Steps: 30
AspectRatio: 1:1
```

Key parameters:
- `--keyframes-file`: Path to text file containing keyframe descriptions (default: Input/keyframes.txt)
- `--reference-image`: Optional path to a reference image for image-to-image generation
- `--output-dir`: Directory to save generated keyframe images (default: output_keyframes)
- `--model`: Model name to use (default: kling-v1-5)
- `--image-reference`: Type of reference: "FACE" or "SUBJECT" (default: FACE)
- `--image-fidelity`: Image reference strength (0.0-1.0, default: 0.5)
- `--human-fidelity`: Face reference strength when using FACE reference (0.0-1.0, default: 0.8)
- `--env-file`: Path to specific .env configuration file
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

The keyframes file supports various parameters per frame including Prompt, NegativePrompt, AspectRatio, Seed, and any other custom parameters you wish to include.

Run any example script with `--help` for full usage instructions.

## External Integration Demo

Additionally, there's a demo showing how to integrate with external services like Dify:

```bash
python -m src.examples.external_dify_demo \
    --image path/to/image.jpg \
    --env-file ./custom_env_file.env \
    --output-dir ./dify_outputs
```

Key parameters:
- `--image`: Path to input image or URL
- `--env-file`: Path to custom environment file with Dify API keys
- `--output-dir`: Directory to save generated outputs

## API Features

The KlingDemo library supports all features of the Kling AI APIs:

### Image-to-Video Features
- **Basic Image-to-Video**: Generate videos from a single image
- **Dynamic Masks**: Control motion in specific areas of the image
- **Static Masks**: Keep specific areas of the image static
- **Camera Control**: Set up camera movements like pan, tilt, zoom
- **Image Tail**: Control both the start and end frames of the video

### Image Generation Features
- **Text-to-Image**: Generate images from text prompts
- **Image-to-Image**: Generate images using a reference image
- **Multiple Models**: Support for all Kling AI image models (kling-v1, kling-v1-5, kling-v2)
- **Negative Prompts**: Specify what to avoid in the generated image
- **Multiple Outputs**: Generate multiple variations in a single request
- **Aspect Ratio Control**: Control the dimensions of the generated image
- **Reference Types**: Use reference images for subject features or face similarity
- **Fidelity Control**: Adjust how closely the generated image follows the reference

## Project Structure

```
klingdemo/
├── api/              # API client implementation
│   └── client.py     # Main API client with JWT authentication
├── models/           # Pydantic models
│   ├── image2video.py # Image-to-Video data models
│   └── image_generation.py # Image Generation data models
├── utils/            # Utility functions
│   ├── config.py     # Configuration management and JWT token generation
│   └── image.py      # Image handling utilities
└── examples/         # Example scripts
    ├── basic_demo.py     # Basic Image-to-Video example
    ├── advanced_demo.py  # Advanced Image-to-Video features
    └── image_gen_demo.py # Image generation examples
```

## Development

Install development dependencies:

```bash
uv pip install -e ".[dev]"  # With UV
# or
pip install -e ".[dev]"      # With Pip
```

Run tests:

```bash
pytest
```

Format code:

```bash
black src tests
isort src tests
```

## License

MIT

## Credits

Developed for demonstration purposes using the Kling AI API documentation.