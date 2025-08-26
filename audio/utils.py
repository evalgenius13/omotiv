"""
Audio utilities for Omotiv v1.0
Handles basic audio operations including mixing, volume control, and export.
"""

import os
from typing import List, Tuple, Optional


class AudioTrack:
    """Represents an audio track with volume control."""
    
    def __init__(self, name: str, data: Optional[List[float]] = None):
        self.name = name
        self.data = data or []
        self.volume = 1.0  # Volume level (0.0 to 1.0)
        self.muted = False
    
    def set_volume(self, volume: float):
        """Set track volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
    
    def apply_volume(self) -> List[float]:
        """Apply volume to track data."""
        if self.muted or not self.data:
            return [0.0] * len(self.data)
        return [sample * self.volume for sample in self.data]


class AudioMixer:
    """Handles mixing multiple audio tracks."""
    
    def __init__(self):
        self.tracks: List[AudioTrack] = []
        self.master_volume = 1.0
    
    def add_track(self, track: AudioTrack):
        """Add a track to the mixer."""
        self.tracks.append(track)
    
    def remove_track(self, track: AudioTrack):
        """Remove a track from the mixer."""
        if track in self.tracks:
            self.tracks.remove(track)
    
    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)."""
        self.master_volume = max(0.0, min(1.0, volume))
    
    def mix_tracks(self) -> List[float]:
        """Mix all tracks into a single audio stream."""
        if not self.tracks:
            return []
        
        # Find the longest track to determine output length
        track_lengths = [len(track.data) for track in self.tracks if track.data]
        if not track_lengths:
            return []
        
        max_length = max(track_lengths)
        if max_length == 0:
            return []
        
        mixed_audio = [0.0] * max_length
        
        for track in self.tracks:
            track_audio = track.apply_volume()
            for i in range(min(len(track_audio), max_length)):
                mixed_audio[i] += track_audio[i]
        
        # Apply master volume
        return [sample * self.master_volume for sample in mixed_audio]


class AudioExporter:
    """Handles exporting audio to various formats."""
    
    @staticmethod
    def export_wav(audio_data: List[float], filename: str, sample_rate: int = 44100) -> bool:
        """
        Export audio data to WAV format.
        This is a simplified implementation - in a real app you'd use a library like soundfile.
        """
        try:
            # Create export directory if it doesn't exist
            export_dir = os.path.dirname(filename)
            if export_dir and not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # For this MVP, we'll just write a simple text representation
            # In a real implementation, you'd use proper WAV encoding
            with open(filename + '.txt', 'w') as f:
                f.write(f"Sample Rate: {sample_rate}\n")
                f.write(f"Samples: {len(audio_data)}\n")
                f.write("Audio Data:\n")
                for i, sample in enumerate(audio_data[:100]):  # Limit output for readability
                    f.write(f"{i}: {sample:.6f}\n")
                if len(audio_data) > 100:
                    f.write(f"... and {len(audio_data) - 100} more samples\n")
            
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    @staticmethod
    def export_stems(mixer: AudioMixer, base_filename: str) -> bool:
        """Export individual tracks as stems."""
        try:
            for i, track in enumerate(mixer.tracks):
                track_filename = f"{base_filename}_track_{i}_{track.name}"
                track_audio = track.apply_volume()
                AudioExporter.export_wav(track_audio, track_filename)
            return True
        except Exception as e:
            print(f"Stem export error: {e}")
            return False


def create_test_audio_data(duration_samples: int, frequency: float = 440.0) -> List[float]:
    """
    Create test audio data (sine wave).
    In a real app, this would come from actual audio recording/playback.
    """
    import math
    samples = []
    for i in range(duration_samples):
        # Simple sine wave
        sample = math.sin(2 * math.pi * frequency * i / 44100) * 0.5
        samples.append(sample)
    return samples