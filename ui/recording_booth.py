from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QSlider, QLabel,
    QComboBox, QPushButton, QFileDialog, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import threading

# ------ AudioPlayer with real volume and output metering ------
class AudioPlayer:
    def __init__(self):
        self.stream = None
        self.data = None
        self.samplerate = 44100
        self.position = 0
        self.is_playing = False
        self.output_device = None
        self._lock = threading.Lock()
        self._last_chunk = None  # For output level metering
        self.volume = 1.0  # Real volume applied during playback

    def load(self, file_path):
        self.data, self.samplerate = sf.read(file_path, dtype="float32")
        if self.data.ndim == 1:
            self.data = np.expand_dims(self.data, axis=1)
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

        # Apply real-time volume
        chunk = chunk * self.volume

        # Store chunk for output metering
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
        # RMS calculation for last chunk played
        chunk = self._last_chunk
        if chunk is None or len(chunk) == 0:
            return 0.0
        rms = np.sqrt(np.mean(chunk**2))
        return min(rms * 5, 1.0)  # scale for meter (tweak as needed)

# ------ Colored Level Meter ------
class ColoredLevelMeter(QProgressBar):
    def __init__(self, label_text="Level", parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setFormat(f"{self.label_text}: %p%")
        self.setTextVisible(True)
        self.setFixedHeight(22)
        self.setStyleSheet("""
        QProgressBar {
            border: 1px solid #bbb;
            border-radius: 8px;
            background: #222;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #44cc44;
            border-radius: 8px;
        }
        """)

    def update_level(self, value):
        # value: 0.0 ... 1.0
        percent = int(value * 100)
        self.setValue(percent)
        # Change color based on level
        if percent < 60:
            color = "#44cc44"  # green
        elif percent < 85:
            color = "#dddd44"  # yellow
        else:
            color = "#dd4444"  # red
        self.setStyleSheet(f"""
        QProgressBar {{
            border: 1px solid #bbb;
            border-radius: 8px;
            background: #222;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {color};
            border-radius: 8px;
        }}
        """)

# ------ Main Booth Dialog ------
class RecordingBooth(QDialog):
    """
    Modal dialog for overdubbing vocals over a track.
    Features: input selector, input+output level meters (real, colored), volume sliders, play/pause for track & vocal, export, disables as needed.
    """
    def __init__(self, input_file, output_dir, trim_start=None, trim_end=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recording Booth")
        self.input_file = input_file
        self.output_dir = output_dir
        self.trim_start = trim_start
        self.trim_end = trim_end

        self.audio_input_device = None
        self.input_stream = None
        self.input_level = 0.0

        self.recorded_vocal = None
        self.is_recording = False

        self.track_player = AudioPlayer()
        self.vocal_player = AudioPlayer()

        self.init_ui()
        self.update_ui_state()

        # Output level polling
        self.output_monitor_timer = QTimer()
        self.output_monitor_timer.timeout.connect(self.poll_output_level)
        self.output_monitor_timer.start(100)

        # Input level polling (only started when device selected)
        self.input_monitor_timer = QTimer()
        self.input_monitor_timer.timeout.connect(self.update_input_meter)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Input Selector
        input_layout = QHBoxLayout()
        input_label = QLabel("Select Input Device:")
        self.input_selector = QComboBox()
        self.populate_inputs()
        self.input_selector.currentIndexChanged.connect(self.on_input_selected)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_selector)
        layout.addLayout(input_layout)

        # Level Meters (colored and real)
        self.level_meter = ColoredLevelMeter("Input Level")
        layout.addWidget(self.level_meter)
        self.output_level_meter = ColoredLevelMeter("Output Level")
        layout.addWidget(self.output_level_meter)

        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red;")
        layout.addWidget(self.warning_label)

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

        # Control Buttons
        btn_layout = QHBoxLayout()
        self.play_track_btn = QPushButton("Play Track")
        self.play_track_btn.clicked.connect(self.on_play_pause_track)
        btn_layout.addWidget(self.play_track_btn)
        self.test_track_btn = QPushButton("Test Track")
        self.test_track_btn.clicked.connect(self.on_test_track)
        btn_layout.addWidget(self.test_track_btn)
        self.record_btn = QPushButton("Record Take")
        self.record_btn.clicked.connect(self.on_record)
        btn_layout.addWidget(self.record_btn)
        self.play_vocal_btn = QPushButton("Play Vocal")
        self.play_vocal_btn.clicked.connect(self.on_play_pause_vocal)
        btn_layout.addWidget(self.play_vocal_btn)
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.on_export)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        # Export options dialog (radio buttons)
        self.export_group = QGroupBox("Export Options")
        self.export_radio_mix = QPushButton("Export Mix (Track + Vocal)")
        self.export_radio_mix.setCheckable(True)
        self.export_radio_vocal = QPushButton("Export Vocal Only")
        self.export_radio_vocal.setCheckable(True)
        self.export_radio_mix.setChecked(True)
        export_radio_layout = QHBoxLayout()
        export_radio_layout.addWidget(self.export_radio_mix)
        export_radio_layout.addWidget(self.export_radio_vocal)
        self.export_group.setLayout(export_radio_layout)
        layout.addWidget(self.export_group)
        self.export_group.setVisible(False)

        # Status label
        self.status_label = QLabel("Ready")
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
        # Stop previous input stream if any
        self.stop_input_stream()
        self.input_level = 0.0
        self.level_meter.update_level(0.0)
        if selected_text == "None" or "No devices" in selected_text:
            self.audio_input_device = None
            self.warning_label.setText("No input device selected. Recording and vocal playback disabled.")
            self.input_monitor_timer.stop()
        else:
            self.audio_input_device = selected_text
            self.warning_label.setText("")
            self.start_input_stream(selected_text)
            self.input_monitor_timer.start(100)
        self.update_ui_state()

    def start_input_stream(self, device_name):
        # Find device index
        device_index = None
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d.get('name') == device_name:
                device_index = i
                break
        if device_index is None:
            return
        # Start a stream for metering
        def callback(indata, frames, time, status):
            if status:
                print("Input stream status:", status)
            # Compute RMS for input
            rms = np.sqrt(np.mean(indata ** 2))
            self.input_level = min(rms * 5, 1.0)  # scale for meter

        try:
            self.input_stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=44100,
                blocksize=1024,
                callback=callback
            )
            self.input_stream.start()
        except Exception as e:
            print("Mic meter failed:", e)
            self.input_stream = None

    def stop_input_stream(self):
        try:
            if self.input_stream is not None:
                self.input_stream.stop()
                self.input_stream.close()
                self.input_stream = None
        except Exception:
            self.input_stream = None

    def update_input_meter(self):
        self.level_meter.update_level(self.input_level)

    def poll_output_level(self):
        # Output level from currently playing track or vocal
        level = 0.0
        if self.track_player.is_playing:
            level = self.track_player.get_output_level()
        elif self.vocal_player.is_playing:
            level = self.vocal_player.get_output_level()
        self.output_level_meter.update_level(level)

    def update_ui_state(self):
        has_input = self.audio_input_device is not None
        self.record_btn.setEnabled(has_input)
        self.play_vocal_btn.setEnabled(has_input and self.recorded_vocal is not None)
        self.export_btn.setEnabled(True)
        self.play_track_btn.setEnabled(True)
        self.test_track_btn.setEnabled(True)
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
        if not self.input_file or not os.path.exists(self.input_file):
            QMessageBox.warning(self, "No Track", "No track loaded or file missing.")
            return
        if self.track_player.is_playing:
            self.track_player.pause()
            self.play_track_btn.setText("Play Track")
            self.status_label.setText("Track paused.")
        else:
            if self.track_player.data is None:
                self.track_player.load(self.input_file)
            self.track_player.play()
            self.play_track_btn.setText("Pause Track")
            self.status_label.setText("Playing track...")

    def on_test_track(self):
        # Alias for Play Track, but disables record so user can safely test their setup before recording
        if self.track_player.is_playing:
            self.on_play_pause_track()
            self.test_track_btn.setText("Test Track")
            self.status_label.setText("Track test stopped.")
            self.record_btn.setEnabled(True)
        else:
            if not self.input_file or not os.path.exists(self.input_file):
                QMessageBox.warning(self, "No Track", "No track loaded or file missing.")
                return
            if self.track_player.data is None:
                self.track_player.load(self.input_file)
            self.track_player.play()
            self.test_track_btn.setText("Stop Test")
            self.status_label.setText("Testing track output...")
            self.record_btn.setEnabled(False)

    def on_record(self):
        # Stop playback before recording
        if self.track_player.is_playing:
            self.track_player.pause()
            self.play_track_btn.setText("Play Track")
            self.test_track_btn.setText("Test Track")
            self.record_btn.setEnabled(True)
        self.is_recording = True
        self.status_label.setText("Recording... (mic input required)")
        self.record_btn.setEnabled(False)

        duration = 5  # seconds (adjust as needed)
        samplerate = 44100
        channels = 1

        try:
            device_index = None
            if self.audio_input_device:
                # Find device index from name
                devices = sd.query_devices()
                for i, d in enumerate(devices):
                    if d.get('name') == self.audio_input_device:
                        device_index = i
                        break
            recording = sd.rec(
                int(duration * samplerate),
                samplerate=samplerate,
                channels=channels,
                dtype='float32',
                device=device_index,
            )
            sd.wait()
            vocal_path = os.path.join(self.output_dir, "vocal_take.wav")
            sf.write(vocal_path, recording, samplerate)
            self.recorded_vocal = vocal_path
            self.status_label.setText("Recording finished.")
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", str(e))
            self.status_label.setText("Recording failed.")
            self.recorded_vocal = None

        self.is_recording = False
        self.record_btn.setEnabled(True)
        self.update_ui_state()

    def on_play_pause_vocal(self):
        if not self.recorded_vocal or not os.path.exists(self.recorded_vocal):
            QMessageBox.warning(self, "No Vocal Take", "No vocal recording available.")
            return
        if self.vocal_player.is_playing:
            self.vocal_player.pause()
            self.play_vocal_btn.setText("Play Vocal")
            self.status_label.setText("Vocal paused.")
        else:
            if self.vocal_player.data is None:
                self.vocal_player.load(self.recorded_vocal)
            self.vocal_player.play()
            self.play_vocal_btn.setText("Pause Vocal")
            self.status_label.setText("Playing vocal take...")

    def on_export(self):
        self.export_group.setVisible(True)
        mix_selected = self.export_radio_mix.isChecked()
        vocal_only_selected = self.export_radio_vocal.isChecked()
        file_path, _ = QFileDialog.getSaveFileName(self, "Export", self.output_dir, "WAV Files (*.wav)")
        if not file_path:
            self.status_label.setText("Export cancelled.")
            self.export_group.setVisible(False)
            return

        try:
            if mix_selected and self.input_file and self.recorded_vocal:
                track, sr_t = sf.read(self.input_file, always_2d=True)
                vocal, sr_v = sf.read(self.recorded_vocal, always_2d=True)
                sr = sr_t  # Assumes same samplerate for both
                min_len = min(len(track), len(vocal))
                # Apply volume sliders (normalize to 0..1)
                track_vol = self.track_volume_slider.value() / 100.0
                vocal_vol = self.vocal_volume_slider.value() / 100.0
                mix = (track[:min_len] * track_vol) + (vocal[:min_len] * vocal_vol)
                mix /= max(np.abs(mix).max(), 1e-6)
                sf.write(file_path, mix, sr)
                self.status_label.setText(f"Exported mix to {file_path}")
            elif vocal_only_selected and self.recorded_vocal:
                vocal, sr = sf.read(self.recorded_vocal, always_2d=True)
                sf.write(file_path, vocal, sr)
                self.status_label.setText(f"Exported vocal to {file_path}")
            else:
                QMessageBox.warning(self, "Export Error", "No data to export.")
                self.status_label.setText("Export failed.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            self.status_label.setText("Export failed.")

        self.export_group.setVisible(False)

    def closeEvent(self, event):
        self.stop_input_stream()
        if self.track_player.is_playing:
            self.track_player.stop()
        if self.vocal_player.is_playing:
            self.vocal_player.stop()
        event.accept()

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    booth = RecordingBooth(
        input_file="your_track.wav",  # <-- Set to your audio track file
        output_dir=os.getcwd()
    )
    booth.show()
    sys.exit(app.exec())