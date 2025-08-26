import os
import torch
import torchaudio
import numpy as np

from PyQt6.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon, QBrush, QLinearGradient, QFont

class WaveformWidget(QWidget):
    seek_requested = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.waveform_data = None
        self.full_waveform = None
        self.sample_rate = 44100
        self.duration = 0.0
        self.playback_position = 0.0
        self.trim_start = None
        self.trim_end = None
        self.dragging_marker = None

        self.bg_color = QColor(22, 22, 28)
        self.grid_color = QColor(40, 40, 50)
        self.waveform_gradient_start = QColor(40, 180, 250)
        self.waveform_gradient_end = QColor(250, 60, 100)
        self.trim_start_color = QColor(0, 220, 120)
        self.trim_end_color = QColor(255, 60, 80)
        self.cursor_color = QColor(255, 255, 255)
        self.cursor_glow = QColor(120, 200, 255, 120)
        self.setMinimumHeight(180)

    def load_audio(self, file_path):
        try:
            waveform, sr = torchaudio.load(file_path)
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            self.sample_rate = sr
            self.duration = waveform.shape[1] / sr

            downsample_factor = max(1, waveform.shape[1] // 4000)
            self.waveform_data = waveform[0][::downsample_factor].numpy()
            self.full_waveform = waveform.numpy()

            self.trim_start = 0.0
            self.trim_end = self.duration
            self.update()
            return True
        except Exception as e:
            print(f"Error loading audio: {e}")
            return False

    def set_playback_position(self, position_seconds):
        self.playback_position = max(0.0, min(self.duration, position_seconds))
        self.update()

    def get_trim_range(self):
        return (self.trim_start, self.trim_end)

    def mousePressEvent(self, event):
        if self.waveform_data is None:
            return
        x = event.position().x()
        t = self.x_to_time(x)

        x_start = self.time_to_x(self.trim_start)
        x_end = self.time_to_x(self.trim_end)

        if abs(x - x_start) < 16:
            self.dragging_marker = "start"
        elif abs(x - x_end) < 16:
            self.dragging_marker = "end"
        else:
            self.seek_requested.emit(t)

    def mouseMoveEvent(self, event):
        if not self.dragging_marker:
            return
        t = self.x_to_time(event.position().x())
        if self.dragging_marker == "start":
            self.trim_start = max(0.0, min(t, self.trim_end - 0.1))
        elif self.dragging_marker == "end":
            self.trim_end = min(self.duration, max(t, self.trim_start + 0.1))
        self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_marker = None

    def x_to_time(self, x):
        widget_width = self.width() - 80
        return (x - 40) / widget_width * self.duration

    def time_to_x(self, t):
        widget_width = self.width() - 80
        return 40 + (t / self.duration * widget_width)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), self.bg_color)

        grid_steps = 8
        for i in range(grid_steps + 1):
            gx = int(40 + (w - 80) * i / grid_steps)
            p.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
            p.drawLine(gx, 0, gx, h)

        if self.waveform_data is None:
            p.setPen(QColor(200, 200, 200))
            p.setFont(QFont("Arial", 16))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No audio loaded")
            return

        center_y = h // 2
        draw_width = w - 80
        scale = (h // 2) * 0.8

        step = max(1, len(self.waveform_data) // draw_width)

        gradient = QLinearGradient(40, 0, w - 40, 0)
        gradient.setColorAt(0.0, self.waveform_gradient_start)
        gradient.setColorAt(1.0, self.waveform_gradient_end)
        p.setPen(QPen(Qt.GlobalColor.transparent))
        p.setBrush(QBrush(gradient))

        points = []
        for i in range(0, len(self.waveform_data), step):
            x = 40 + (i / len(self.waveform_data)) * draw_width
            y = int(center_y - self.waveform_data[i] * scale)
            points.append(QPoint(int(x), y))
        if points:
            path = QPolygon(points)
            p.setPen(QPen(gradient, 2))
            p.drawPolyline(path)

        for i in range(0, len(self.waveform_data), step):
            x = 40 + (i / len(self.waveform_data)) * draw_width
            y = int(center_y - self.waveform_data[i] * scale)
            amp = abs(self.waveform_data[i])
            color = QColor.fromRgbF(
                0.2 + 0.8 * amp,
                0.2 + 0.2 * (1 - amp),
                0.85 - 0.4 * amp,
                0.55 + 0.45 * amp
            )
            p.setPen(QPen(color, 2))
            p.drawLine(int(x), center_y, int(x), y)

        if self.trim_start is not None and self.trim_end is not None:
            x1, x2 = self.time_to_x(self.trim_start), self.time_to_x(self.trim_end)
            p.fillRect(int(x1), 0, int(x2 - x1), h, QColor(255, 255, 255, 30))

            p.setBrush(QBrush(self.trim_start_color))
            p.setPen(QPen(self.trim_start_color, 2))
            handle_w = 12
            handle_rect = QRectF(x1 - handle_w // 2, center_y - 24, handle_w, 48)
            p.drawRoundedRect(handle_rect, 6, 6)
            p.setPen(QColor(22, 22, 28))
            p.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            p.drawText(handle_rect, Qt.AlignmentFlag.AlignCenter, "S")

            p.setBrush(QBrush(self.trim_end_color))
            p.setPen(QPen(self.trim_end_color, 2))
            handle_rect2 = QRectF(x2 - handle_w // 2, center_y - 24, handle_w, 48)
            p.drawRoundedRect(handle_rect2, 6, 6)
            p.setPen(QColor(22, 22, 28))
            p.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            p.drawText(handle_rect2, Qt.AlignmentFlag.AlignCenter, "E")

        cursor_x = self.time_to_x(self.playback_position)
        glow_width = 8
        p.setPen(QPen(self.cursor_glow, glow_width))
        p.drawLine(int(cursor_x), 0, int(cursor_x), h)
        p.setPen(QPen(self.cursor_color, 2))
        p.drawLine(int(cursor_x), 0, int(cursor_x), h)

class AudioEditorSection(QGroupBox):
    play_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    seek_requested = pyqtSignal(float)

    def __init__(self):
        super().__init__("Audio Editor")
        self.audio_file = None
        self.is_playing = False
        self.waveform = WaveformWidget()
        self.setup_ui()
        self.hide()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.waveform)

        controls_layout = QHBoxLayout()

        self.play_pause_btn = QPushButton("▶️ Play")
        self.play_pause_btn.clicked.connect(self.play_requested.emit)
        controls_layout.addWidget(self.play_pause_btn)

        self.trim_btn = QPushButton("✂️ Trim Preview")
        self.trim_btn.clicked.connect(lambda: self.seek_requested.emit(self.waveform.trim_start or 0.0))
        controls_layout.addWidget(self.trim_btn)

        self.audio_info_label = QLabel("No audio loaded")
        controls_layout.addWidget(self.audio_info_label, 1)
        layout.addLayout(controls_layout)

    def load_audio(self, file_path):
        self.audio_file = file_path
        if self.waveform.load_audio(file_path):
            self.audio_info_label.setText(os.path.basename(file_path))
            self.show()
            return True
        return False

    def update_playback_position(self, pos_sec):
        self.waveform.set_playback_position(pos_sec)

    def set_play_button_state(self, is_playing: bool):
        if is_playing:
            self.play_pause_btn.setText("⏸️ Pause")
        else:
            self.play_pause_btn.setText("▶️ Play")
            
    def get_trim_range(self):
        return self.waveform.get_trim_range()