"""
Data models for the Kling AI API.
"""
from .image2video import (
    CameraControl, 
    CameraControlConfig,
    DynamicMask, 
    ImageToVideoRequest, 
    ImageToVideoResponse, 
    TaskInfo,
    TaskResponseData, 
    TaskResult, 
    TaskStatus, 
    TrajectoryPoint, 
    VideoResult
)

__all__ = [
    "CameraControl", 
    "CameraControlConfig",
    "DynamicMask", 
    "ImageToVideoRequest", 
    "ImageToVideoResponse", 
    "TaskInfo",
    "TaskResponseData", 
    "TaskResult", 
    "TaskStatus", 
    "TrajectoryPoint", 
    "VideoResult"
]