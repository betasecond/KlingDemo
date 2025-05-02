# klingdemo/utils/keyframe_parser.py

import re
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError, field_validator # Use field_validator for Pydantic v2+

# --- Pydantic Model Definition ---

class KeyframeData(BaseModel):
    """
    Represents the data associated with a single keyframe.

    Uses Pydantic for data validation and type coercion.
    Allows extra fields not explicitly defined here to accommodate
    custom parameters in the keyframe file.
    """
    # Define common/expected fields. Use aliases to match the typical
    # casing found in text files (e.g., PascalCase) while using
    # snake_case in Python code. Mark them as Optional if they might
    # not be present in every frame.
    prompt: Optional[str] = Field(None, alias='Prompt')
    negative_prompt: Optional[str] = Field(None, alias='NegativePrompt')
    aspect_ratio: Optional[str] = Field(None, alias='AspectRatio')
    seed: Optional[int] = Field(None, alias='Seed')
    steps: Optional[int] = Field(None, alias='Steps')
    # Add other known fields here, e.g.:
    # cfg_scale: Optional[float] = Field(None, alias='CfgScale')
    # motion_scale: Optional[float] = Field(None, alias='MotionScale')

    # Store the original frame number if needed, extracted from the marker
    frame_number: Optional[int] = Field(None, exclude=True) # Exclude from model dump if not needed in output dict

    # Configuration to allow arbitrary extra fields
    class Config:
        extra = 'allow' # Allow fields not explicitly defined in the model
        populate_by_name = True # Allows using both alias and field name for population (Pydantic v2+)


# --- Parsing Function ---

def parse_keyframe_file(file_path: Path) -> List[KeyframeData]:
    """
    Parses a keyframe definition file (.txt) and returns a list of structured keyframe data.

    The expected file format consists of blocks starting with '[Frame N]',
    followed by 'Key: Value' pairs. Example:

    [Frame 1]
    Prompt: A futuristic cityscape at dawn
    NegativePrompt: blurry, low quality
    AspectRatio: 16:9
    Seed: 12345

    [Frame 2]
    Prompt: A close-up of a cybernetic eye
    Steps: 30
    CustomParameter: SomeValue

    Args:
        file_path: A Path object pointing to the keyframe definition file.

    Returns:
        A list of KeyframeData objects, each representing a validated frame.
        Frames that fail validation or lines that are malformed might be skipped
        with warnings printed to stderr (or logged, depending on setup).

    Raises:
        FileNotFoundError: If the specified file_path does not exist or is not a file.
        IOError: If there's an error reading the file.
        # Note: ValidationErrors during parsing are currently caught and logged as warnings,
        #       the function will return successfully parsed frames only. Modify if strict
        #       validation failure should halt the process.
    """
    if not isinstance(file_path, Path):
        # Ensure input is a Path object for consistency
        file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(f"Keyframe file not found: {file_path}")

    keyframes: List[KeyframeData] = []
    current_frame_data: Dict[str, Any] = {}
    current_frame_number: Optional[int] = None

    # Regex to identify the start of a new frame definition block and capture frame number
    # Matches "[Frame N]" at the start of a line
    frame_marker_pattern = re.compile(r'^\[Frame (\d+)\]$')

    try:
        with file_path.open('r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue # Skip empty lines

                frame_match = frame_marker_pattern.match(line)
                if frame_match:
                    # --- Start of a new frame ---
                    # 1. Validate and store the previous frame's data (if any)
                    if current_frame_data:
                        try:
                            # Add frame number if captured
                            if current_frame_number is not None:
                                current_frame_data['frame_number'] = current_frame_number

                            # Create and validate Pydantic model instance
                            keyframe = KeyframeData(**current_frame_data)
                            keyframes.append(keyframe)
                        except ValidationError as e:
                            # Handle validation errors (e.g., wrong data type for 'Seed')
                            logging.warning(f"Skipping frame ending before line {line_num} due to validation error(s):\n{e}")
                            # Consider using logging instead of print in a real application
                            # logging.warning(...)

                    # 2. Reset for the new frame
                    current_frame_data = {}
                    current_frame_number = int(frame_match.group(1)) # Extract frame number

                elif ':' in line:
                    # --- Key-Value pair line ---
                    try:
                        key, value = map(str.strip, line.split(':', 1))
                        if key: # Ensure key is not empty
                            current_frame_data[key] = value
                        else:
                             logging.warning(f"Skipping line {line_num} with empty key: '{line}'")
                    except ValueError:
                        # Handle lines with ':' but incorrect format (e.g., ":value" or "key:")
                        logging.warning(f"Skipping malformed key-value line {line_num}: '{line}'")
                else:
                    # --- Unrecognized line format ---
                    # Ignore or log lines that are not frame markers, comments (if any), or K:V pairs
                    logging.warning(f"Skipping unrecognized line format {line_num}: '{line}'")


        # --- After the loop: Process the last frame ---
        if current_frame_data:
            try:
                 # Add frame number if captured
                if current_frame_number is not None:
                    current_frame_data['frame_number'] = current_frame_number
                keyframe = KeyframeData(**current_frame_data)
                keyframes.append(keyframe)
            except ValidationError as e:
                logging.warning(f"Skipping the last frame due to validation error(s):\n{e}")

    except FileNotFoundError: # Should be caught earlier, but defensive check
         raise
    except IOError as e:
        # Catch potential file reading errors
        raise IOError(f"Error reading file {file_path}: {e}") from e
    except Exception as e:
        # Catch unexpected errors during processing
        raise RuntimeError(f"An unexpected error occurred while parsing {file_path}: {e}") from e

    return keyframes

# --- Example Usage (Optional - typically in a test file or main script) ---
if __name__ == '__main__':
    # Create a dummy file for demonstration
    dummy_file_content = """
[Frame 1]
Prompt: A peaceful meadow at sunset
NegativePrompt: buildings, people, noise
AspectRatio: 16:9
Seed: 1000
CustomField: ValueA

[Frame 10]
# This frame has a different number
Prompt: A bustling market scene
Steps: 25
Seed: 2000
MotionScale: 1.2

[Frame 11]
Prompt: Abstract swirling colors
AspectRatio: 1:1
Seed: not_an_integer # This will cause a validation warning

[Frame 12]
Invalid line without colon
AnotherKey: AnotherValue
Weird Line:
: EmptyKeyTest

[Frame 15]
Prompt: Final keyframe concept
Steps: 50
    """ # Indented line test
    dummy_file_path = Path("./temp_keyframes.txt")
    try:
        dummy_file_path.write_text(dummy_file_content, encoding='utf-8')
        print(f"Created dummy file: {dummy_file_path}")

        # Parse the file
        parsed_keyframes = parse_keyframe_file(dummy_file_path)

        print(f"\n--- Successfully parsed {len(parsed_keyframes)} keyframes ---")
        for i, frame in enumerate(parsed_keyframes):
            print(f"\nFrame Index {i} (Original Frame Num: {frame.frame_number}):")
            # Use model_dump() in Pydantic v2+ (dict() in v1)
            # Exclude unset fields for cleaner output, exclude internal frame_number
            print(frame.model_dump(exclude_unset=True, exclude={'frame_number'}))
            # You can access fields directly with type safety:
            # print(f"  Prompt: {frame.prompt}")
            # print(f"  Seed: {frame.seed}") # Will be int or None

    except (FileNotFoundError, IOError, RuntimeError, ValidationError) as e:
        print(f"\n--- Error during parsing ---")
        print(e)
    finally:
        # Clean up the dummy file
        if dummy_file_path.exists():
            dummy_file_path.unlink()
            print(f"\nCleaned up dummy file: {dummy_file_path}")