"""
User Interface module for Omotiv v1.0.

This module provides the graphical user interface components for the Omotiv
desktop application, including the main window, controls, and user interaction
handling with proper error handling and tooltips.
"""

__version__ = "1.0.0"
__author__ = "Omotiv Team"

# Export main UI classes and functions
from .main_window import MainWindow
from .tooltips import ToolTipHelper

__all__ = ['MainWindow', 'ToolTipHelper']