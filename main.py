"""
Omotiv v1.0 - Main Application Entry Point
Desktop audio application with recording booth, volume controls, and export functionality.
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.recording_booth import create_recording_booth


def main():
    """Main application entry point."""
    print('Starting Omotiv v1.0...')
    
    try:
        # Create and run the recording booth UI
        root, app = create_recording_booth()
        print('Recording Booth UI launched successfully')
        root.mainloop()
    except Exception as e:
        print(f'Error starting application: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
