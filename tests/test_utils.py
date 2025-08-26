"""
Tests for audio utilities in Omotiv v1.0
Simple tests for audio mixing functionality.
"""

import unittest
import os
import sys

# Add parent directory to path to import audio modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audio.utils import AudioTrack, AudioMixer, AudioExporter, create_test_audio_data


class TestAudioTrack(unittest.TestCase):
    """Tests for AudioTrack class."""
    
    def setUp(self):
        """Set up test data."""
        self.test_data = [0.1, 0.2, 0.3, 0.4, 0.5]
        self.track = AudioTrack("Test Track", self.test_data)
    
    def test_track_creation(self):
        """Test track creation with data."""
        self.assertEqual(self.track.name, "Test Track")
        self.assertEqual(self.track.data, self.test_data)
        self.assertEqual(self.track.volume, 1.0)
        self.assertFalse(self.track.muted)
    
    def test_empty_track_creation(self):
        """Test creating a track without data."""
        empty_track = AudioTrack("Empty")
        self.assertEqual(empty_track.name, "Empty")
        self.assertEqual(empty_track.data, [])
    
    def test_volume_control(self):
        """Test volume setting and boundaries."""
        # Normal volume
        self.track.set_volume(0.5)
        self.assertEqual(self.track.volume, 0.5)
        
        # Volume above 1.0 should be clamped
        self.track.set_volume(1.5)
        self.assertEqual(self.track.volume, 1.0)
        
        # Volume below 0.0 should be clamped
        self.track.set_volume(-0.5)
        self.assertEqual(self.track.volume, 0.0)
    
    def test_apply_volume(self):
        """Test volume application to audio data."""
        self.track.set_volume(0.5)
        processed_data = self.track.apply_volume()
        expected = [x * 0.5 for x in self.test_data]
        self.assertEqual(processed_data, expected)
    
    def test_muted_track(self):
        """Test muted track behavior."""
        self.track.muted = True
        processed_data = self.track.apply_volume()
        expected = [0.0] * len(self.test_data)
        self.assertEqual(processed_data, expected)
    
    def test_empty_track_volume(self):
        """Test volume application on empty track."""
        empty_track = AudioTrack("Empty")
        processed_data = empty_track.apply_volume()
        self.assertEqual(processed_data, [])


class TestAudioMixer(unittest.TestCase):
    """Tests for AudioMixer class."""
    
    def setUp(self):
        """Set up test mixer and tracks."""
        self.mixer = AudioMixer()
        self.track1 = AudioTrack("Track 1", [0.1, 0.2, 0.3])
        self.track2 = AudioTrack("Track 2", [0.2, 0.3, 0.4])
    
    def test_mixer_creation(self):
        """Test mixer initialization."""
        self.assertEqual(len(self.mixer.tracks), 0)
        self.assertEqual(self.mixer.master_volume, 1.0)
    
    def test_add_remove_tracks(self):
        """Test adding and removing tracks."""
        self.mixer.add_track(self.track1)
        self.assertEqual(len(self.mixer.tracks), 1)
        self.assertIn(self.track1, self.mixer.tracks)
        
        self.mixer.add_track(self.track2)
        self.assertEqual(len(self.mixer.tracks), 2)
        
        self.mixer.remove_track(self.track1)
        self.assertEqual(len(self.mixer.tracks), 1)
        self.assertNotIn(self.track1, self.mixer.tracks)
        self.assertIn(self.track2, self.mixer.tracks)
    
    def test_master_volume_control(self):
        """Test master volume setting."""
        self.mixer.set_master_volume(0.7)
        self.assertEqual(self.mixer.master_volume, 0.7)
        
        # Test clamping
        self.mixer.set_master_volume(1.5)
        self.assertEqual(self.mixer.master_volume, 1.0)
        
        self.mixer.set_master_volume(-0.3)
        self.assertEqual(self.mixer.master_volume, 0.0)
    
    def test_simple_mixing(self):
        """Test mixing two tracks of equal length."""
        self.mixer.add_track(self.track1)
        self.mixer.add_track(self.track2)
        
        mixed = self.mixer.mix_tracks()
        expected = [0.3, 0.5, 0.7]  # Sum of both tracks
        
        # Use approximate equality for floating point comparison
        self.assertEqual(len(mixed), len(expected))
        for i, (actual, exp) in enumerate(zip(mixed, expected)):
            self.assertAlmostEqual(actual, exp, places=5, msg=f"Sample {i}")
    
    def test_mixing_different_lengths(self):
        """Test mixing tracks of different lengths."""
        short_track = AudioTrack("Short", [0.1, 0.2])
        long_track = AudioTrack("Long", [0.3, 0.4, 0.5, 0.6])
        
        self.mixer.add_track(short_track)
        self.mixer.add_track(long_track)
        
        mixed = self.mixer.mix_tracks()
        expected = [0.4, 0.6, 0.5, 0.6]  # Short track contributes 0 to last two samples
        
        # Use approximate equality for floating point comparison
        self.assertEqual(len(mixed), len(expected))
        for i, (actual, exp) in enumerate(zip(mixed, expected)):
            self.assertAlmostEqual(actual, exp, places=5, msg=f"Sample {i}")
    
    def test_mixing_with_volume(self):
        """Test mixing with volume adjustments."""
        self.track1.set_volume(0.5)
        self.track2.set_volume(0.8)
        
        self.mixer.add_track(self.track1)
        self.mixer.add_track(self.track2)
        
        mixed = self.mixer.mix_tracks()
        # track1: [0.05, 0.1, 0.15], track2: [0.16, 0.24, 0.32]
        expected = [0.21, 0.34, 0.47]
        
        # Use approximate equality for floating point comparison
        for i, (actual, exp) in enumerate(zip(mixed, expected)):
            self.assertAlmostEqual(actual, exp, places=5, msg=f"Sample {i}")
    
    def test_mixing_with_master_volume(self):
        """Test mixing with master volume applied."""
        self.mixer.add_track(self.track1)
        self.mixer.add_track(self.track2)
        self.mixer.set_master_volume(0.5)
        
        mixed = self.mixer.mix_tracks()
        expected = [0.15, 0.25, 0.35]  # Sum then multiply by master volume
        
        # Use approximate equality for floating point comparison
        self.assertEqual(len(mixed), len(expected))
        for i, (actual, exp) in enumerate(zip(mixed, expected)):
            self.assertAlmostEqual(actual, exp, places=5, msg=f"Sample {i}")
    
    def test_empty_mixer(self):
        """Test mixing with no tracks."""
        mixed = self.mixer.mix_tracks()
        self.assertEqual(mixed, [])
    
    def test_mixing_empty_tracks(self):
        """Test mixing tracks with no data."""
        empty_track = AudioTrack("Empty")
        self.mixer.add_track(empty_track)
        
        mixed = self.mixer.mix_tracks()
        self.assertEqual(mixed, [])


class TestAudioExporter(unittest.TestCase):
    """Tests for AudioExporter class."""
    
    def setUp(self):
        """Set up test data and temporary directory."""
        self.test_audio = [0.1, 0.2, 0.3, 0.4, 0.5]
        self.test_dir = "/tmp/omotiv_test_exports"
        os.makedirs(self.test_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test files."""
        # Clean up any test files created
        import glob
        test_files = glob.glob(os.path.join(self.test_dir, "*"))
        for file in test_files:
            try:
                os.remove(file)
            except:
                pass
        try:
            os.rmdir(self.test_dir)
        except:
            pass
    
    def test_export_wav(self):
        """Test WAV export functionality."""
        filename = os.path.join(self.test_dir, "test_export")
        success = AudioExporter.export_wav(self.test_audio, filename)
        
        self.assertTrue(success)
        # Check that the text file was created (our simplified implementation)
        self.assertTrue(os.path.exists(filename + ".txt"))
        
        # Verify file contents
        with open(filename + ".txt", 'r') as f:
            content = f.read()
            self.assertIn("Sample Rate: 44100", content)
            self.assertIn("Samples: 5", content)
            self.assertIn("Audio Data:", content)
    
    def test_export_stems(self):
        """Test stem export functionality."""
        # Create a mixer with test tracks
        mixer = AudioMixer()
        track1 = AudioTrack("Bass", [0.1, 0.2])
        track2 = AudioTrack("Melody", [0.3, 0.4])
        mixer.add_track(track1)
        mixer.add_track(track2)
        
        base_filename = os.path.join(self.test_dir, "test_stems")
        success = AudioExporter.export_stems(mixer, base_filename)
        
        self.assertTrue(success)
        # Check that stem files were created
        self.assertTrue(os.path.exists(base_filename + "_track_0_Bass.txt"))
        self.assertTrue(os.path.exists(base_filename + "_track_1_Melody.txt"))


class TestCreateTestAudioData(unittest.TestCase):
    """Tests for test audio data generation."""
    
    def test_basic_generation(self):
        """Test basic audio data generation."""
        samples = create_test_audio_data(100, 440.0)
        self.assertEqual(len(samples), 100)
        
        # Check that we get reasonable sine wave values
        for sample in samples:
            self.assertGreaterEqual(sample, -0.5)
            self.assertLessEqual(sample, 0.5)
    
    def test_zero_duration(self):
        """Test generation with zero duration."""
        samples = create_test_audio_data(0, 440.0)
        self.assertEqual(len(samples), 0)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)