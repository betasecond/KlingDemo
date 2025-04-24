"""
Kling AI API Client for image-to-video generation.

This module provides a client for interacting with Kling AI's API,
with a focus on the image-to-video generation functionality.
"""
import json
import time
from typing import Any, Dict, List, Optional, Union

import requests
from loguru import logger
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..models.image2video import (
    ImageToVideoRequest,
    ImageToVideoResponse,
    TaskResponseData,
    TaskStatus,
)
from ..utils.config import generate_jwt_token


class KlingAPIError(Exception):
    """Exception raised for errors returned by the Kling AI API."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[int] = None,
        request_id: Optional[str] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id
        super().__init__(message)


class NetworkError(Exception):
    """Exception raised for network-related errors when calling the API."""

    pass


class KlingAPIClient:
    """Client for interacting with the Kling AI API."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        base_url: str = "https://api.klingai.com",
        timeout: int = 60,
        max_retries: int = 3,
        token_expiration: int = 1800,  # Default token expiration: 30 minutes
    ):
        """
        Initialize the Kling AI API client.

        Args:
            access_key: API access key (ak) for authentication
            secret_key: API secret key (sk) for authentication
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            token_expiration: Token validity period in seconds
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")  # Remove trailing slash if present
        self.timeout = timeout
        self.max_retries = max_retries
        self.token_expiration = token_expiration
        
        # Initialize token
        self.token = None
        self.token_timestamp = 0
    
    def _get_token(self) -> str:
        """
        Get a valid JWT token, generating a new one if needed.
        
        Returns:
            Valid JWT token for authentication
        """
        current_time = int(time.time())
        
        # Check if we need to generate a new token
        # Refresh the token when it's within 10% of expiration
        if (
            self.token is None 
            or current_time > self.token_timestamp + (self.token_expiration * 0.9)
        ):
            logger.debug("Generating new JWT token")
            self.token = generate_jwt_token(
                self.access_key, 
                self.secret_key, 
                self.token_expiration
            )
            self.token_timestamp = current_time
            
        return self.token

    def _get_headers(self) -> Dict[str, str]:
        """
        Get the headers required for API requests.

        Returns:
            Dict containing authorization and content type headers
        """
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle the API response, checking for errors.

        Args:
            response: Response from the API

        Returns:
            Dict containing the parsed response data

        Raises:
            KlingAPIError: If the API returns an error response
            NetworkError: If there's an issue with the response format
        """
        try:
            # Check for HTTP errors
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Check for API-level errors
            if data.get("code", 0) != 0:
                raise KlingAPIError(
                    message=data.get("message", "Unknown API error"),
                    status_code=response.status_code,
                    error_code=data.get("code"),
                    request_id=data.get("request_id"),
                )

            return data
        except requests.exceptions.JSONDecodeError:
            raise NetworkError(f"Invalid JSON response: {response.text}")
        except requests.exceptions.HTTPError as err:
            # Try to parse error response if possible
            try:
                error_data = response.json()
                raise KlingAPIError(
                    message=error_data.get("message", str(err)),
                    status_code=response.status_code,
                    error_code=error_data.get("code"),
                    request_id=error_data.get("request_id"),
                )
            except (ValueError, KeyError):
                # If we can't parse the error response, raise the original error
                raise KlingAPIError(
                    message=str(err),
                    status_code=response.status_code,
                )

    @retry(
        retry=retry_if_exception_type(
            (requests.exceptions.ConnectionError, requests.exceptions.Timeout)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _request(
        self, method: str, path: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: Query parameters
            json_data: Request body data

        Returns:
            Dict containing the parsed response data

        Raises:
            NetworkError: If there's a network-related error
            KlingAPIError: If the API returns an error response
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug(f"{method} {url}")
        if json_data:
            logger.debug(f"Request data: {json.dumps(json_data)}")

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
            logger.error(f"Network error: {err}")
            raise NetworkError(f"Network error: {err}")
        except KlingAPIError as err:
            # If we get a 401 with error code 1004 (token expired),
            # try to regenerate the token and retry once
            if (
                hasattr(err, 'status_code') 
                and err.status_code == 401 
                and hasattr(err, 'error_code') 
                and err.error_code == 1004
            ):
                logger.warning("Token expired, regenerating and retrying...")
                self.token = None  # Force token regeneration
                
                # Retry the request once
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=self._get_headers(),
                    timeout=self.timeout,
                )
                return self._handle_response(response)
            else:
                # For other types of API errors, just reraise
                raise

    def create_image_to_video_task(
        self, request: Union[Dict, ImageToVideoRequest]
    ) -> TaskResponseData:
        """
        Create an image-to-video generation task.

        Args:
            request: Image-to-video request parameters, either as a dictionary
                    or an ImageToVideoRequest object

        Returns:
            TaskResponseData object containing the task information

        Raises:
            ValueError: If validation of the request data fails
            KlingAPIError: If the API returns an error response
            NetworkError: If there's a network-related error
        """
        # Convert to request model if dictionary is provided
        if isinstance(request, dict):
            try:
                request = ImageToVideoRequest(**request)
            except ValidationError as e:
                raise ValueError(f"Invalid request data: {e}")

        # Convert to dictionary for requests library
        request_dict = request.model_dump(exclude_none=True)

        # Make the API request
        try:
            response = self._request("POST", "/v1/videos/image2video", json_data=request_dict)
            response_model = ImageToVideoResponse(**response)

            # Handle the response data which should contain a task object
            if isinstance(response_model.data, dict):
                return TaskResponseData(**response_model.data)
            else:
                raise ValueError("Unexpected response format")
        except ValidationError as e:
            logger.error(f"Error parsing API response: {e}")
            raise ValueError(f"Unexpected response format: {e}")

    def get_task_by_id(self, task_id: str) -> TaskResponseData:
        """
        Get information about an image-to-video task by its task_id.

        Args:
            task_id: The task ID to retrieve

        Returns:
            TaskResponseData object containing the task information

        Raises:
            KlingAPIError: If the API returns an error response
            NetworkError: If there's a network-related error
            ValueError: If the response doesn't match expected format
        """
        try:
            response = self._request("GET", f"/v1/videos/image2video/{task_id}")
            response_model = ImageToVideoResponse(**response)

            # Handle the response data
            if isinstance(response_model.data, dict):
                return TaskResponseData(**response_model.data)
            else:
                raise ValueError("Unexpected response format")
        except ValidationError as e:
            logger.error(f"Error parsing API response: {e}")
            raise ValueError(f"Unexpected response format: {e}")

    def get_task_by_external_id(self, external_task_id: str) -> TaskResponseData:
        """
        Get information about an image-to-video task by its external_task_id.

        Args:
            external_task_id: The client-defined task ID to retrieve

        Returns:
            TaskResponseData object containing the task information

        Raises:
            KlingAPIError: If the API returns an error response
            NetworkError: If there's a network-related error
            ValueError: If the response doesn't match expected format
        """
        try:
            response = self._request(
                "GET", "/v1/videos/image2video", params={"external_task_id": external_task_id}
            )
            response_model = ImageToVideoResponse(**response)

            # Handle the response data
            if isinstance(response_model.data, dict):
                return TaskResponseData(**response_model.data)
            else:
                raise ValueError("Unexpected response format")
        except ValidationError as e:
            logger.error(f"Error parsing API response: {e}")
            raise ValueError(f"Unexpected response format: {e}")

    def list_tasks(self, page_num: int = 1, page_size: int = 30) -> List[TaskResponseData]:
        """
        List image-to-video tasks.

        Args:
            page_num: Page number for pagination (1-indexed)
            page_size: Number of items per page

        Returns:
            List of TaskResponseData objects

        Raises:
            KlingAPIError: If the API returns an error response
            NetworkError: If there's a network-related error
            ValueError: If the response doesn't match expected format
        """
        try:
            response = self._request(
                "GET", "/v1/videos/image2video", params={"pageNum": page_num, "pageSize": page_size}
            )
            response_model = ImageToVideoResponse(**response)

            # Handle the response data which should be a list of tasks
            if isinstance(response_model.data, list):
                return [TaskResponseData(**task_data) for task_data in response_model.data]
            else:
                raise ValueError("Unexpected response format")
        except ValidationError as e:
            logger.error(f"Error parsing API response: {e}")
            raise ValueError(f"Unexpected response format: {e}")

    def wait_for_task_completion(
        self, task_id: str, check_interval: int = 5, timeout: int = 300
    ) -> TaskResponseData:
        """
        Wait for an image-to-video task to complete.

        Args:
            task_id: The task ID to wait for
            check_interval: How frequently to check task status (in seconds)
            timeout: Maximum time to wait (in seconds)

        Returns:
            TaskResponseData object containing the completed task information

        Raises:
            TimeoutError: If the timeout is reached before the task completes
            KlingAPIError: If the API returns an error response
            NetworkError: If there's a network-related error
        """
        start_time = time.time()
        while True:
            # Check if timeout has been reached
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")

            # Get the task status
            task = self.get_task_by_id(task_id)
            
            # Check if the task is complete
            if task.task_status == TaskStatus.SUCCEED:
                logger.info(f"Task {task_id} completed successfully")
                return task
                
            elif task.task_status == TaskStatus.FAILED:
                error_msg = f"Task {task_id} failed: {task.task_status_msg or 'Unknown error'}"
                logger.error(error_msg)
                raise KlingAPIError(error_msg)
                
            # Task is still processing, wait before checking again
            logger.debug(f"Task {task_id} is still {task.task_status}, waiting {check_interval}s...")
            time.sleep(check_interval)