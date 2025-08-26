"""
Tooltip Helper Module for Omotiv v1.0.

This module provides tooltip functionality for UI elements to improve user
experience by providing helpful hints and explanations for controls and buttons.
"""

import logging
from typing import Dict, Optional


class ToolTipHelper:
    """
    Helper class for managing tooltips throughout the Omotiv application.
    
    This class provides a centralized way to manage tooltips for UI elements,
    ensuring consistent messaging and easy maintenance of user guidance text.
    
    Attributes:
        tooltips (Dict[str, str]): Dictionary mapping element IDs to tooltip text
        enabled (bool): Whether tooltips are currently enabled
    """
    
    def __init__(self):
        """
        Initialize the ToolTipHelper with default tooltip definitions.
        
        Sets up logging and initializes the default tooltip messages for
        common UI elements in the Omotiv application.
        """
        self.logger = logging.getLogger(__name__)
        self.enabled = True
        
        # Default tooltip messages for common UI elements
        self.tooltips: Dict[str, str] = {
            "record_button": "Start or stop audio recording. Click to begin capturing audio input.",
            "play_button": "Play the selected audio file. Click to start audio playback.",
            "stop_button": "Stop current audio operation (recording or playback).",
            "volume_slider": "Adjust audio volume level. Drag to change playback volume (0-100%).",
            "file_open": "Open an audio file for playback. Supports common audio formats.",
            "file_save": "Save the current recording to a file. Choose location and format.",
            "settings_button": "Open application settings and preferences.",
            "help_button": "View help documentation and user guide.",
            "exit_button": "Close the Omotiv application. Unsaved work will be lost.",
            "device_selector": "Select audio input/output device for recording and playback.",
            "format_selector": "Choose audio format for recording (MP3, WAV, FLAC, etc.).",
            "quality_selector": "Set audio quality/bitrate for recordings."
        }
        
        self.logger.info("ToolTipHelper initialized with default tooltips")
    
    def get_tooltip(self, element_id: str) -> Optional[str]:
        """
        Get tooltip text for a specific UI element.
        
        Args:
            element_id (str): Unique identifier for the UI element
            
        Returns:
            Optional[str]: Tooltip text if found, None otherwise
        """
        try:
            if not self.enabled:
                return None
                
            tooltip = self.tooltips.get(element_id)
            if tooltip:
                self.logger.debug(f"Retrieved tooltip for {element_id}")
            else:
                self.logger.debug(f"No tooltip found for element: {element_id}")
                
            return tooltip
            
        except Exception as e:
            self.logger.error(f"Error retrieving tooltip for {element_id}: {str(e)}")
            return None
    
    def set_tooltip(self, element_id: str, tooltip_text: str) -> bool:
        """
        Set or update tooltip text for a UI element.
        
        Args:
            element_id (str): Unique identifier for the UI element
            tooltip_text (str): The tooltip text to display
            
        Returns:
            bool: True if tooltip was set successfully, False otherwise
        """
        try:
            if not element_id or not tooltip_text:
                raise ValueError("Element ID and tooltip text cannot be empty")
                
            self.tooltips[element_id] = tooltip_text
            self.logger.debug(f"Set tooltip for {element_id}: {tooltip_text[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting tooltip for {element_id}: {str(e)}")
            return False
    
    def remove_tooltip(self, element_id: str) -> bool:
        """
        Remove tooltip for a specific UI element.
        
        Args:
            element_id (str): Unique identifier for the UI element
            
        Returns:
            bool: True if tooltip was removed, False if not found
        """
        try:
            if element_id in self.tooltips:
                del self.tooltips[element_id]
                self.logger.debug(f"Removed tooltip for {element_id}")
                return True
            else:
                self.logger.debug(f"No tooltip to remove for {element_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error removing tooltip for {element_id}: {str(e)}")
            return False
    
    def enable_tooltips(self) -> None:
        """Enable tooltip display throughout the application."""
        self.enabled = True
        self.logger.info("Tooltips enabled")
    
    def disable_tooltips(self) -> None:
        """Disable tooltip display throughout the application."""
        self.enabled = False
        self.logger.info("Tooltips disabled")
    
    def get_all_tooltips(self) -> Dict[str, str]:
        """
        Get all currently defined tooltips.
        
        Returns:
            Dict[str, str]: Copy of all tooltip definitions
        """
        try:
            return self.tooltips.copy()
        except Exception as e:
            self.logger.error(f"Error getting all tooltips: {str(e)}")
            return {}
    
    def clear_all_tooltips(self) -> None:
        """
        Clear all tooltip definitions.
        
        This removes all custom tooltips but preserves the ability to add new ones.
        """
        try:
            self.tooltips.clear()
            self.logger.info("All tooltips cleared")
        except Exception as e:
            self.logger.error(f"Error clearing tooltips: {str(e)}")
    
    def load_tooltips_from_config(self, config: Dict[str, str]) -> bool:
        """
        Load tooltip definitions from configuration.
        
        Args:
            config (Dict[str, str]): Dictionary of element_id -> tooltip_text mappings
            
        Returns:
            bool: True if tooltips loaded successfully, False otherwise
        """
        try:
            if not isinstance(config, dict):
                raise ValueError("Config must be a dictionary")
                
            self.tooltips.update(config)
            self.logger.info(f"Loaded {len(config)} tooltips from configuration")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading tooltips from config: {str(e)}")
            return False