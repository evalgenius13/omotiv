# Omotiv v1.0

A powerful and user-friendly desktop audio application for recording, playback, and audio processing. Omotiv provides an intuitive interface for managing audio content with advanced features and robust error handling.

## Features

- **Audio Recording**: High-quality audio recording with multiple format support
- **Audio Playback**: Play various audio formats with volume control
- **User-Friendly Interface**: Intuitive GUI with helpful tooltips and responsive design
- **Error Handling**: Comprehensive error logging and user feedback
- **Threading Support**: Responsive UI with background audio processing
- **Device Management**: Support for multiple audio input/output devices
- **Format Support**: Multiple audio formats (MP3, WAV, FLAC, etc.)
- **Quality Settings**: Configurable audio quality and bitrate options

## Installation

### Prerequisites

- Python 3.7 or higher
- Operating System: Windows, macOS, or Linux

### Quick Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/evalgenius13/omotiv.git
   cd omotiv
   ```

2. **Install dependencies** (if any):
   ```bash
   pip install -r requirements.txt
   ```
   *Note: If requirements.txt doesn't exist, the application currently has no external dependencies.*

3. **Run the application:**
   ```bash
   python main.py
   ```

### Development Installation

For development purposes, you may want to install the application in development mode:

```bash
# Clone the repository
git clone https://github.com/evalgenius13/omotiv.git
cd omotiv

# Create a virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install in development mode
pip install -e .
```

## Usage

### Basic Usage

1. **Start the application:**
   ```bash
   python main.py
   ```

2. **Main Interface:**
   - The main window will open with audio controls
   - Use the Record button to start/stop audio recording
   - Use the Play button to play audio files
   - Use the Stop button to stop current operations
   - Adjust volume with the volume slider

3. **Recording Audio:**
   - Click the "Record" button to start recording
   - Speak into your microphone
   - Click "Record" again or "Stop" to end recording
   - Save your recording using the "Save File" button

4. **Playing Audio:**
   - Click "Open File" to select an audio file
   - Click "Play" to start playback
   - Use the volume slider to adjust playback volume
   - Click "Stop" to halt playback

### Advanced Features

#### Audio Device Selection
- Use the device selector dropdown to choose your preferred audio input/output device
- The application automatically detects available audio devices

#### Format and Quality Settings
- Select recording format from the format selector (MP3, WAV, FLAC)
- Choose quality settings for optimal file size vs. audio quality balance

#### Tooltips and Help
- Hover over any control to see helpful tooltips
- Click the "Help" button for detailed documentation
- All tooltips can be toggled on/off in settings

## Configuration

### Log Files

Omotiv automatically creates log files for debugging and error tracking:
- **Location**: `omotiv_error.log` in the application directory
- **Content**: Application events, errors, and debugging information
- **Rotation**: Logs are appended to the file (automatic cleanup not implemented)

### Settings

Access application settings through the "Settings" button:
- Audio device preferences
- Recording quality settings
- UI preferences (tooltips, themes)
- Error reporting options

## Troubleshooting

### Common Issues

1. **Application won't start:**
   - Check that Python 3.7+ is installed: `python --version`
   - Verify all files are present in the directory
   - Check the `omotiv_error.log` file for error details

2. **No audio devices detected:**
   - Ensure your audio devices are properly connected
   - Check system audio settings
   - Restart the application after connecting devices

3. **Recording not working:**
   - Verify microphone permissions on your system
   - Check that the correct input device is selected
   - Ensure the microphone is not being used by another application

4. **Playback issues:**
   - Check that the audio file format is supported
   - Verify output device selection
   - Ensure system volume is not muted

### Debug Mode

To run with verbose logging for troubleshooting:

```bash
# Set logging level to DEBUG
export OMOTIV_LOG_LEVEL=DEBUG
python main.py
```

### Log Analysis

Check the `omotiv_error.log` file for detailed error information:
```bash
# View recent log entries
tail -f omotiv_error.log

# Search for specific errors
grep "ERROR" omotiv_error.log
```

## Architecture

### Module Structure

```
omotiv/
├── main.py              # Main application entry point
├── audio/               # Audio processing modules
│   ├── __init__.py      # Audio module exports
│   └── audio_handler.py # Core audio handling logic
├── ui/                  # User interface modules
│   ├── __init__.py      # UI module exports
│   ├── main_window.py   # Main application window
│   └── tooltips.py      # Tooltip management system
├── logs/                # Log directory (created automatically)
├── omotiv_error.log     # Main error log file
└── README.md            # This file
```

### Key Components

- **AudioHandler**: Manages audio recording, playback, and device interaction
- **MainWindow**: Provides the main user interface and event handling
- **ToolTipHelper**: Manages tooltips and user guidance throughout the application
- **Error Logging**: Comprehensive logging system for debugging and monitoring

## Contributing

### Development Guidelines

1. **Code Style**: Follow PEP 8 Python style guidelines
2. **Documentation**: Add docstrings to all classes and methods
3. **Error Handling**: Include proper exception handling and logging
4. **Testing**: Test all changes thoroughly before submitting

### Making Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with proper documentation
4. Test the changes thoroughly
5. Submit a pull request with a clear description

### Reporting Issues

When reporting issues, please include:
- Operating system and version
- Python version
- Steps to reproduce the issue
- Contents of `omotiv_error.log` if available
- Expected vs. actual behavior

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For support and questions:
- Check the troubleshooting section above
- Review the `omotiv_error.log` file for error details
- Create an issue on the GitHub repository
- Check existing documentation and help resources

## Changelog

### Version 1.0.0
- Initial release
- Basic audio recording and playback functionality
- User-friendly interface with tooltips
- Comprehensive error handling and logging
- Multi-threaded audio processing
- Cross-platform compatibility

## Acknowledgments

- Built with Python for cross-platform compatibility
- Designed with user experience and reliability in mind
- Comprehensive error handling for production use

---

**Omotiv v1.0** - Empowering audio creativity with reliable, user-friendly tools.
