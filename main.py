#!/usr/bin/env python3
"""
Omotiv v1.0 - Main Application Entry Point

This is the main entry point for the Omotiv desktop application. It initializes
logging, error handling, and starts the main application with proper exception
handling and resource cleanup.

The application provides audio recording, playback, and processing capabilities
with a user-friendly graphical interface.

Author: Omotiv Team
Version: 1.0.0
"""

import sys
import os
import logging
import traceback
import signal
from pathlib import Path
from typing import Optional

# Import Omotiv modules
from audio import AudioHandler
from ui import MainWindow, ToolTipHelper


class OmotivApplication:
    """
    Main application class for Omotiv v1.0.
    
    This class manages the lifecycle of the Omotiv application, including
    initialization, error handling, logging setup, and graceful shutdown.
    
    Attributes:
        logger (logging.Logger): Application logger
        audio_handler (AudioHandler): Audio processing system
        main_window (MainWindow): Main application window
        tooltip_helper (ToolTipHelper): Tooltip management system
        is_running (bool): Application running state
    """
    
    def __init__(self):
        """
        Initialize the Omotiv application.
        
        Sets up logging, error handling, and prepares application components
        for initialization.
        """
        self.logger: Optional[logging.Logger] = None
        self.audio_handler: Optional[AudioHandler] = None
        self.main_window: Optional[MainWindow] = None
        self.tooltip_helper: Optional[ToolTipHelper] = None
        self.is_running = False
        
        # Setup logging first so we can log any initialization issues
        self._setup_logging()
        
        if self.logger:
            self.logger.info("Omotiv application instance created")
    
    def _setup_logging(self) -> None:
        """
        Setup application logging to both console and file.
        
        Configures logging to write to both the console (for development)
        and to a log file (omotiv_error.log) for debugging and error tracking.
        This helps with troubleshooting issues after deployment.
        """
        try:
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Configure logging format
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            date_format = '%Y-%m-%d %H:%M:%S'
            
            # Setup root logger
            logging.basicConfig(
                level=logging.INFO,
                format=log_format,
                datefmt=date_format,
                handlers=[
                    # Console handler for real-time monitoring
                    logging.StreamHandler(sys.stdout),
                    # File handler for persistent error logging
                    logging.FileHandler(
                        'omotiv_error.log',
                        mode='a',
                        encoding='utf-8'
                    )
                ]
            )
            
            # Get application logger
            self.logger = logging.getLogger('omotiv.main')
            self.logger.info("Logging system initialized successfully")
            self.logger.info(f"Log file: {os.path.abspath('omotiv_error.log')}")
            
        except Exception as e:
            # Fallback to basic console logging if file logging fails
            logging.basicConfig(level=logging.ERROR)
            self.logger = logging.getLogger('omotiv.main')
            self.logger.error(f"Failed to setup file logging: {str(e)}")
            print(f"Warning: Could not setup file logging: {str(e)}")
    
    def _setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for graceful shutdown.
        
        Configures signal handlers to ensure proper cleanup when the
        application receives termination signals (SIGINT, SIGTERM).
        """
        try:
            def signal_handler(signum, frame):
                """Handle termination signals gracefully."""
                if self.logger:
                    self.logger.info(f"Received signal {signum}, shutting down gracefully...")
                self.shutdown()
                sys.exit(0)
            
            # Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
            signal.signal(signal.SIGTERM, signal_handler)  # Termination request
            
            if self.logger:
                self.logger.debug("Signal handlers registered")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to setup signal handlers: {str(e)}")
    
    def initialize(self) -> bool:
        """
        Initialize all application components.
        
        Returns:
            bool: True if initialization successful, False otherwise
            
        This method initializes the audio system, UI components, and other
        application subsystems with proper error handling and logging.
        """
        try:
            if self.logger:
                self.logger.info("Initializing Omotiv application...")
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Initialize audio handling system
            if self.logger:
                self.logger.info("Initializing audio system...")
            self.audio_handler = AudioHandler()
            
            # Initialize tooltip helper
            if self.logger:
                self.logger.info("Initializing tooltip system...")
            self.tooltip_helper = ToolTipHelper()
            
            # Initialize main window
            if self.logger:
                self.logger.info("Initializing main window...")
            self.main_window = MainWindow("Omotiv v1.0")
            
            # Initialize main window with components
            if not self.main_window.initialize(
                audio_handler=self.audio_handler,
                tooltip_helper=self.tooltip_helper
            ):
                raise RuntimeError("Failed to initialize main window")
            
            self.is_running = True
            
            if self.logger:
                self.logger.info("Omotiv application initialized successfully")
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize application: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                print(f"ERROR: {error_msg}")
            return False
    
    def run(self) -> int:
        """
        Start and run the main application.
        
        Returns:
            int: Exit code (0 for success, non-zero for error)
            
        This method starts the main application loop and handles any
        runtime errors that occur during execution.
        """
        try:
            if not self.is_running:
                if self.logger:
                    self.logger.error("Application not properly initialized")
                return 1
            
            if self.logger:
                self.logger.info("Starting Omotiv application")
            
            # Show the main window
            if self.main_window and not self.main_window.show():
                raise RuntimeError("Failed to show main window")
            
            if self.logger:
                self.logger.info("Omotiv application started successfully")
            
            # Main application loop (placeholder)
            # In a real GUI application, this would be the main event loop
            print("Omotiv v1.0 is now running...")
            print("Press Ctrl+C to exit")
            
            # Keep the application running
            # In a real implementation, this would be replaced by the GUI event loop
            try:
                while self.is_running:
                    # Simulate main application work
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                if self.logger:
                    self.logger.info("Received keyboard interrupt, shutting down...")
                self.shutdown()
            
            return 0
            
        except Exception as e:
            error_msg = f"Runtime error: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                print(f"ERROR: {error_msg}")
            
            # Attempt graceful shutdown even on error
            self.shutdown()
            return 1
    
    def shutdown(self) -> None:
        """
        Gracefully shutdown the application.
        
        Performs cleanup of all application components and resources,
        ensuring that threads are stopped and files are properly closed.
        """
        try:
            if self.logger:
                self.logger.info("Shutting down Omotiv application...")
            
            self.is_running = False
            
            # Cleanup main window
            if self.main_window:
                try:
                    self.main_window.close()
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error closing main window: {str(e)}")
            
            # Cleanup audio system
            if self.audio_handler:
                try:
                    self.audio_handler.cleanup()
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error cleaning up audio system: {str(e)}")
            
            if self.logger:
                self.logger.info("Omotiv application shutdown complete")
            
        except Exception as e:
            error_msg = f"Error during shutdown: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(f"ERROR: {error_msg}")


def main() -> int:
    """
    Main entry point for the Omotiv application.
    
    Returns:
        int: Exit code (0 for success, non-zero for error)
        
    This function creates and runs the main application instance with
    top-level exception handling to catch any unhandled errors.
    """
    try:
        # Create and initialize application
        app = OmotivApplication()
        
        if not app.initialize():
            print("Failed to initialize Omotiv application")
            return 1
        
        # Run the application
        return app.run()
        
    except Exception as e:
        # Last resort error handling
        error_msg = f"Unhandled exception in main: {str(e)}"
        print(f"FATAL ERROR: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Try to log to file if possible
        try:
            with open('omotiv_error.log', 'a') as f:
                f.write(f"\n{error_msg}\n")
                f.write(f"Traceback: {traceback.format_exc()}\n")
        except:
            pass  # If we can't log, continue with exit
        
        return 1


# Application entry point
if __name__ == '__main__':
    print('Starting Omotiv v1.0...')
    exit_code = main()
    print(f'Omotiv v1.0 exited with code: {exit_code}')
    sys.exit(exit_code)
