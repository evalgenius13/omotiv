from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QSlider, QLabel,
    QComboBox, QPushButton, QFileDialog, QMessageBox, QLineEdit, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from ui.level_meter import LevelMeter
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import threading
from datetime import datetime
import sys

class AudioPlayer:
    def __init__(self):
        self.stream = None
        self.data = None
        self.samplerate = 44100
        self.position = 0
        self.is_playing = False
        self._lock = threading.Lock()
        self._last_chunk = None
        self.volume = 1.0

    def load(self, file_path):
        self.data, self.samplerate = sf.read(file_path, dtype="float32", always_2d=True)
        with self._lock:
            self.position = 0

    def trim(self, start_sec=None, end_sec=None):
        if self.data is not None:
            sr = self.samplerate
            total = len(self.data)
            start_frame = int(start_sec * sr) if start_sec else 0
            end_frame = int(end_sec * sr) if end_sec else total
            self.data = self.data[start_frame:end_frame]
            with self._lock:
                self.position = 0

    def _callback(self, outdata, frames, time, status):
        if status:
            print("Playback:", status)
        with self._lock:
            start = self.position
            end = min(start + frames, len(self.data))
            chunk = self.data[start:end]
            self.position = end
        chunk = chunk * self.volume
        self._last_chunk = chunk.copy() if len(chunk) > 0 else None

        if len(chunk) < frames:
            pad = np.zeros((frames - len(chunk), self.data.shape[1]), dtype="float32")
            chunk = np.vstack((chunk, pad))
            outdata[:] = chunk
            raise sd.CallbackStop()
        else:
            outdata[:] = chunk

    def play(self):
        if self.data is None:
            return
        self.stop()
        try:
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=self.data.shape[1],
                callback=self._callback,
                blocksize=2048,
                latency="high",
                finished_callback=self._on_finished,
            )
            self.stream.start()
            self.is_playing = True
        except Exception as e:
            print(f"Playback failed: {e}")
            self.is_playing = False

    def _on_finished(self):
        self.is_playing = False
        with self._lock:
            self.position = 0

    def pause(self):
        if self.stream and self.stream.active:
            self.stream.stop()
            self.is_playing = False

    def stop(self):
        if self.stream:
            try:
                if self.stream.active:
                    self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.is_playing = False

    def seek(self, seconds):
        if self.data is None:
            return
        frame = int(seconds * self.samplerate)
        with self._lock:
            self.position = max(0, min(frame, len(self.data)))

    def get_position(self):
        with self._lock:
            return self.position / self.samplerate if self.data is not None else 0.0

    def get_duration(self):
        return len(self.data) / self.samplerate if self.data is not None else 0.0

    def get_output_level(self):
        chunk = self._last_chunk
        if chunk is None or len(chunk) == 0:
            return 0.0
        rms = np.sqrt(np.mean(chunk**2))
        return min(rms * 5, 1.0)

class RecordingBooth(QDialog):
    def __init__(self, input_file, output_dir, trim_start=0, trim_end=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recording Booth")
        self.input_file = input_file
        self.output_dir = output_dir
        self.trim_start = trim_start
        self.trim_end = trim_end

        self.audio_input_device_index = None
        self.input_level = 0.0
        self._level_lock = threading.Lock()
        self.input_meter_stream = None

        self.recorded_vocal = None
        self.is_recording = False
        self.recording_data = []
        self._record_lock = threading.Lock()
        self.record_stream = None
        self.record_timer = None
        self.elapsed_seconds = 0
        self.max_record_seconds = 600
        self.max_recording_chunks = self.max_record_seconds * 44

        self.track_player = AudioPlayer()
        self.vocal_player = AudioPlayer()

        self.track_player.load(self.input_file)
        self.track_duration_seconds = self.track_player.get_duration()
        
        self.init_ui()
        self.update_ui_state()

        self.output_monitor_timer = QTimer()
        self.output_monitor_timer.timeout.connect(self.poll_output_level)
        self.output_monitor_timer.start(100)

        self.input_monitor_timer = QTimer()
        self.input_monitor_timer.timeout.connect(self.update_input_meter)

        self.elapsed_timer = QTimer()
        self.elapsed_timer.timeout.connect(self.update_elapsed_time)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Booth info header
        info_label = QLabel("Recording Booth - Use main page for seeking and waveform control")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #888; font-style: italic; padding: 10px;")
        layout.addWidget(info_label)

        # Input Selector
        input_layout = QHBoxLayout()
        input_label = QLabel("Select Input Device:")
        self.input_selector = QComboBox()
        self.populate_inputs()
        self.input_selector.currentIndexChanged.connect(self.on_input_selected)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_selector)
        layout.addLayout(input_layout)

        # Level Meters
        input_label = QLabel("INPUT")
        input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(input_label)
        self.input_meter = LevelMeter(channels=1)
        layout.addWidget(self.input_meter)
        
        playback_label = QLabel("PLAYBACK")
        playback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(playback_label)
        self.output_meter = LevelMeter(channels=1)
        layout.addWidget(self.output_meter)

        # Track info display (read-only from main page settings)
        track_group = QGroupBox("Recording Section (Set on Main Page)")
        track_layout = QVBoxLayout(track_group)
        self.track_info_label = QLabel("")
        self.track_info_label.setStyleSheet("font-weight: bold;")
        track_layout.addWidget(self.track_info_label)
        
        # Add note about changing settings
        change_note = QLabel("To change recording section, close booth and adjust on main page")
        change_note.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")
        track_layout.addWidget(change_note)
        
        self.update_track_info_label()
        layout.addWidget(track_group)

        # Volume Controls
        volume_group = QGroupBox("Volume Controls")
        volume_layout = QHBoxLayout()
        self.track_volume_label = QLabel("Track Volume")
        self.track_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.track_volume_slider.setRange(0, 100)
        self.track_volume_slider.setValue(50)
        self.track_volume_slider.valueChanged.connect(self.on_track_volume_changed)
        self.vocal_volume_label = QLabel("Vocal Volume")
        self.vocal_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.vocal_volume_slider.setRange(0, 100)
        self.vocal_volume_slider.setValue(50)
        self.vocal_volume_slider.valueChanged.connect(self.on_vocal_volume_changed)
        volume_layout.addWidget(self.track_volume_label)
        volume_layout.addWidget(self.track_volume_slider)
        volume_layout.addWidget(self.vocal_volume_label)
        volume_layout.addWidget(self.vocal_volume_slider)
        volume_group.setLayout(volume_layout)
        layout.addWidget(volume_group)

        # Recording timer
        self.recording_timer_label = QLabel("")
        self.recording_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.recording_timer_label)

        # Control Buttons - focused on recording workflow
        btn_layout = QHBoxLayout()
        
        # Recording controls
        self.record_btn = QPushButton("Record Take")
        self.record_btn.clicked.connect(self.on_record)
        btn_layout.addWidget(self.record_btn)
        
        self.stop_btn = QPushButton("Stop Recording")
        self.stop_btn.clicked.connect(self.on_stop_recording)
        self.stop_btn.setVisible(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.cancel_btn = QPushButton("Cancel Recording")
        self.cancel_btn.clicked.connect(self.on_cancel_recording)
        self.cancel_btn.setVisible(False)
        btn_layout.addWidget(self.cancel_btn)
        
        # Playback controls (simplified)
        self.play_track_btn = QPushButton("Play Track Section")
        self.play_track_btn.clicked.connect(self.on_play_pause_track)
        btn_layout.addWidget(self.play_track_btn)
        
        self.play_vocal_btn = QPushButton("Play Vocal")
        self.play_vocal_btn.clicked.connect(self.on_play_pause_vocal)
        btn_layout.addWidget(self.play_vocal_btn)
        
        # Export
        self.export_btn = QPushButton("Export Mix")
        self.export_btn.clicked.connect(self.on_export)
        btn_layout.addWidget(self.export_btn)
        
        layout.addLayout(btn_layout)

        # Status label
        self.status_label = QLabel("Ready - Select input device to begin")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def populate_inputs(self):
        self.input_selector.clear()
        self.input_selector.addItem("None")
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d.get('max_input_channels', 0) > 0:
                    self.input_selector.addItem(f"{d['name']}")
        except Exception as e:
            self.input_selector.addItem("No devices found")

    def on_input_selected(self, idx):
        selected_text = self.input_selector.currentText()
        with self._level_lock:
            self.input_level = 0.0
        self.input_meter.update_levels([0.0])
        if selected_text == "None" or "No devices" in selected_text:
            self.audio_input_device_index = None
            self.input_monitor_timer.stop()
            self.stop_input_meter_stream()
            self.status_label.setText("No input selected - recording disabled")
        else:
            self.audio_input_device_index = self._find_device_index(selected_text)
            if self.audio_input_device_index is not None:
                self.start_input_meter_stream()
                self.input_monitor_timer.start(50)
                self.status_label.setText("Input ready - you can now record")
            else:
                self.status_label.setText("Input device not found")
        self.update_ui_state()

    def _find_device_index(self, device_name):
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if device_name in d.get('name', '') and d.get('max_input_channels', 0) > 0:
                    return i
        except Exception as e:
            print(f"Error finding device index: {e}")
        return None

    def update_input_meter(self):
        with self._level_lock:
            current_level = self.input_level
        self.input_meter.update_levels([current_level])

    def start_input_meter_stream(self):
        if self.audio_input_device_index is None:
            return
        def meter_callback(indata, frames, time, status):
            try:
                rms = np.sqrt(np.mean(indata ** 2))
                with self._level_lock:
                    self.input_level = min(rms * 5, 1.0)
            except Exception:
                pass
        try:
            self.input_meter_stream = sd.InputStream(
                device=self.audio_input_device_index,
                channels=1,
                samplerate=44100,
                callback=meter_callback,
                dtype='float32',
                blocksize=1024
            )
            self.input_meter_stream.start()
        except Exception as e:
            print(f"Input meter stream failed: {e}")
            self.input_meter_stream = None

    def stop_input_meter_stream(self):
        try:
            if self.input_meter_stream is not None:
                self.input_meter_stream.stop()
                self.input_meter_stream.close()
                self.input_meter_stream = None
        except Exception:
            self.input_meter_stream = None

    def poll_output_level(self):
        level = 0.0
        if self.track_player.is_playing:
            level = self.track_player.get_output_level()
        elif self.vocal_player.is_playing:
            level = self.vocal_player.get_output_level()
        self.output_meter.update_levels([level])

    def update_ui_state(self):
        has_input = self.audio_input_device_index is not None
        self.record_btn.setEnabled(has_input and not self.is_recording)
        self.stop_btn.setVisible(self.is_recording)
        self.cancel_btn.setVisible(self.is_recording)
        self.play_vocal_btn.setEnabled(has_input and self.recorded_vocal is not None and not self.is_recording)
        self.export_btn.setEnabled(self.recorded_vocal is not None and not self.is_recording)
        self.play_track_btn.setEnabled(not self.is_recording)
        
        if not has_input:
            self.record_btn.setStyleSheet("color: grey;")
            self.play_vocal_btn.setStyleSheet("color: grey;")
        else:
            self.record_btn.setStyleSheet("")
            self.play_vocal_btn.setStyleSheet("")

    def on_track_volume_changed(self, value):
        self.track_player.volume = value / 100.0

    def on_vocal_volume_changed(self, value):
        self.vocal_player.volume = value / 100.0

    def on_play_pause_track(self):
        """Play the trimmed section of the track"""
        if self.track_player.is_playing:
            self.track_player.pause()
            self.play_track_btn.setText("Play Track Section")
            self.status_label.setText("Track paused.")
        else:
            # Load and trim the track to the specified section
            self.track_player.load(self.input_file)
            self.track_player.trim(self.trim_start, self.trim_end)
            self.track_player.play()
            self.play_track_btn.setText("Pause Track")
            self.status_label.setText(f"Playing track section ({self.trim_start}s to {self.trim_end if self.trim_end else 'end'}s)")

    def on_record(self):
        """Start recording with backing track"""
        # Start backing track for timing
        self.track_player.load(self.input_file)
        self.track_player.trim(self.trim_start, self.trim_end)
        self.track_player.play()
        
        # Stop input monitoring during recording
        self.input_monitor_timer.stop()
        
        self.is_recording = True
        self.status_label.setText("Recording... (max 10:00)")
        self.elapsed_seconds = 0
        self.recording_timer_label.setText("Recording: 00:00 / 10:00")
        self.recording_data = []
        self._record_lock = threading.Lock()
        self.update_ui_state()
        
        try:
            def record_callback(indata, frames, time, status):
                try:
                    if status:
                        print(f"Recording status: {status}")
                    with self._record_lock:
                        if len(self.recording_data) < self.max_recording_chunks:
                            self.recording_data.append(indata.copy())
                        else:
                            print("Warning: Recording buffer full, dropping frames")
                except Exception as e:
                    print(f"Recording callback error: {e}")
                    
            self.record_stream = sd.InputStream(
                device=self.audio_input_device_index,
                channels=1,
                samplerate=44100,
                callback=record_callback,
                dtype='float32',
                blocksize=1024
            )
            
            self.record_stream.start()
            self.elapsed_timer.start(1000)
            
            # Auto-stop timer
            self.auto_stop_timer = QTimer()
            self.auto_stop_timer.setSingleShot(True)
            self.auto_stop_timer.timeout.connect(self.on_auto_stop_recording)
            self.auto_stop_timer.start(self.max_record_seconds * 1000)
            
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", str(e))
            self.status_label.setText("Recording failed.")
            self.is_recording = False
            self.update_ui_state()

    def update_elapsed_time(self):
        self.elapsed_seconds += 1
        mins = self.elapsed_seconds // 60
        secs = self.elapsed_seconds % 60
        self.recording_timer_label.setText(f"Recording: {mins:02d}:{secs:02d} / 10:00")
        if self.elapsed_seconds >= self.max_record_seconds:
            self.on_auto_stop_recording()

    def on_stop_recording(self):
        self.finish_recording(save=True)

    def on_cancel_recording(self):
        self.finish_recording(save=False)

    def on_auto_stop_recording(self):
        self.finish_recording(save=True, auto=True)

    def finish_recording(self, save=True, auto=False):
        self.elapsed_timer.stop()
        self.recording_timer_label.setText("")
        
        # Clean up recording stream
        try:
            if self.record_stream:
                self.record_stream.stop()
                self.record_stream.close()
                self.record_stream = None
            if hasattr(self, 'auto_stop_timer') and self.auto_stop_timer:
                self.auto_stop_timer.stop()
        except Exception as e:
            print(f"Recording stream close error: {e}")
            
        if save:
            with self._record_lock:
                if self.recording_data:
                    recording = np.concatenate(self.recording_data, axis=0)
                    fname = f"vocal_take_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_omotiv.wav"
                    vocal_path = os.path.join(self.output_dir, fname)
                    sf.write(vocal_path, recording, 44100)
                    self.recorded_vocal = vocal_path
                    status = f"Take saved as {os.path.basename(vocal_path)}"
                    if auto:
                        status += " (auto-stopped at 10:00)"
                    self.status_label.setText(status)
                else:
                    self.status_label.setText("No audio recorded.")
                    self.recorded_vocal = None
        else:
            self.status_label.setText("Recording cancelled.")
            self.recorded_vocal = None
            
        self.is_recording = False
        self.update_ui_state()
        
        # Restart input monitoring
        if self.audio_input_device_index is not None:
            self.input_monitor_timer.start(50)

    def on_play_pause_vocal(self):
        if not self.recorded_vocal or not os.path.exists(self.recorded_vocal):
            QMessageBox.warning(self, "No Vocal Take", "No vocal recording available.")
            return
        if self.vocal_player.is_playing:
            self.vocal_player.pause()
            self.play_vocal_btn.setText("Play Vocal")
            self.status_label.setText("Vocal paused.")
        else:
            self.vocal_player.load(self.recorded_vocal)
            self.vocal_player.play()
            self.play_vocal_btn.setText("Pause Vocal")
            self.status_label.setText("Playing vocal take...")

    def on_export(self):
        default_fname = f"vocal_mix_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_omotiv.wav"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Vocal Mix", 
            os.path.join(self.output_dir, default_fname), 
            "WAV files (*.wav)"
        )
        if not file_path:
            return
            
        try:
            track, sr_t = sf.read(self.input_file, always_2d=True)
            vocal, sr_v = sf.read(self.recorded_vocal, always_2d=True)
            sr = sr_t
            
            # Use trimmed segment for mix
            start_frame = int(self.trim_start * sr)
            end_frame = int(self.trim_end * sr) if self.trim_end else len(track)
            track_trimmed = track[start_frame:end_frame]
            
            # Match vocal length to track section
            vocal_trimmed = vocal[:end_frame-start_frame] if len(vocal) >= (end_frame-start_frame) else np.pad(vocal, ((0, (end_frame-start_frame)-len(vocal)), (0,0)))
            
            # Mix with volume controls
            track_vol = self.track_volume_slider.value() / 100.0
            vocal_vol = self.vocal_volume_slider.value() / 100.0
            mix = (track_trimmed * track_vol) + (vocal_trimmed * vocal_vol)
            
            # Normalize to prevent clipping
            max_val = np.abs(mix).max()
            if max_val > 0.5:
                mix = mix / max_val * 0.95
                
            sf.write(file_path, mix, sr)
            self.status_label.setText(f"Exported mix to {os.path.basename(file_path)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            self.status_label.setText("Export failed.")

    def update_track_info_label(self):
        """Display read-only track info based on trim settings from main page"""
        mins = int(self.track_duration_seconds) // 60
        secs = int(self.track_duration_seconds) % 60
        
        # Show the recording section that was set on main page
        if self.trim_end and self.trim_end < self.track_duration_seconds:
            section_duration = self.trim_end - self.trim_start
            section_mins = int(section_duration) // 60
            section_secs = int(section_duration) % 60
            info_text = f"Recording section: {self.trim_start:.1f}s to {self.trim_end:.1f}s ({section_mins:02d}:{section_secs:02d})"
        else:
            remaining_duration = self.track_duration_seconds - self.trim_start
            remaining_mins = int(remaining_duration) // 60
            remaining_secs = int(remaining_duration) % 60
            info_text = f"Recording section: {self.trim_start:.1f}s to end ({remaining_mins:02d}:{remaining_secs:02d})"
            
        info_text += f"\nFull track length: {mins:02d}:{secs:02d}"
        self.track_info_label.setText(info_text)

    def closeEvent(self, event):
        """Clean shutdown"""
        self.input_monitor_timer.stop()
        self.elapsed_timer.stop()
        if hasattr(self, 'auto_stop_timer') and self.auto_stop_timer:
            self.auto_stop_timer.stop()
            
        # Stop recording if active
        if self.record_stream:
            try:
                self.record_stream.stop()
                self.record_stream.close()
            except Exception:
                pass
                
        self.stop_input_meter_stream()
        
        # Stop any playing audio
        if self.track_player.is_playing:
            self.track_player.stop()
        if self.vocal_player.is_playing:
            self.vocal_player.stop()
            
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    booth = RecordingBooth(
        input_file="your_track.wav",
        output_dir=os.getcwd()
    )
    booth.show()
    sys.exit(app.exec())