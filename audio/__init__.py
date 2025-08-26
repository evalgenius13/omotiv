"""
Audio processing module for Omotiv v1.0.

This module handles audio-related functionality including audio playback,
recording, and processing for the Omotiv desktop application.
"""

__version__ = "1.0.0"
__author__ = "Omotiv Team"

# Export main audio classes and functions
from .audio_handler import AudioHandler

__all__ = ['AudioHandler']