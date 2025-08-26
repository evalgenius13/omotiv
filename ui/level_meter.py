from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QLinearGradient, QBrush
import math
import time

class LevelMeter(QWidget):
    def __init__(self, channels=2, parent=None):
        super().__init__(parent)
        self.channels = channels
        self.displayed_levels = [0.0 for _ in range(channels)]
        self.target_levels = [0.0 for _ in range(channels)]
        self.peak_levels = [0.0 for _ in range(channels)]
        self.peak_times = [0.0 for _ in range(channels)]
        self.setMinimumHeight(50)
        self.setMinimumWidth(180)
        self.attack = 0.2
        self.release = 0.92
        self.peak_hold_ms = 700
        self.peak_threshold = 0.97

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def update_levels(self, levels):
        now = time.time() * 1000
        for i in range(self.channels):
            lvl = min(max(levels[i], 0.0), 1.0)
            self.target_levels[i] = lvl
            if lvl > self.peak_levels[i]:
                self.peak_levels[i] = lvl
                self.peak_times[i] = now
        self.update()

    def animate(self):
        now = time.time() * 1000
        for i in range(self.channels):
            if self.target_levels[i] > self.displayed_levels[i]:
                smoothing = self.attack
            else:
                smoothing = self.release
            self.displayed_levels[i] = (
                self.displayed_levels[i] * smoothing +
                self.target_levels[i] * (1 - smoothing)
            )
            if now - self.peak_times[i] > self.peak_hold_ms:
                self.peak_levels[i] *= 0.96
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        W = self.width()
        H = self.height()
        gap = 8
        bar_height = (H - (self.channels + 1) * gap) // self.channels
        bar_width_max = W - 60

        for i in range(self.channels):
            lvl = self.displayed_levels[i]
            peak = self.peak_levels[i]
            bar_width = int(bar_width_max * lvl)
            peak_x = int(bar_width_max * peak)
            y = gap + i * (bar_height + gap)
            x = 40

            gradient = QLinearGradient(x, y, x + bar_width, y + bar_height)
            if lvl >= self.peak_threshold:
                gradient.setColorAt(0.0, QColor(255, 0, 0))
                gradient.setColorAt(1.0, QColor(255, 180, 100))
            elif lvl > 0.7:
                gradient.setColorAt(0.0, QColor(255, 220, 0))
                gradient.setColorAt(1.0, QColor(220, 220, 50))
            else:
                gradient.setColorAt(0.0, QColor(60, 220, 100))
                gradient.setColorAt(1.0, QColor(180, 255, 180))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(x, y, bar_width, bar_height)

            painter.setPen(QColor(255, 140, 0))
            painter.drawLine(x + peak_x, y, x + peak_x, y + bar_height)

            db_val = 20 * (math.log10(lvl) if lvl > 0.0001 else -2)
            painter.setFont(QFont("Arial", 9))
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(0, y, 36, bar_height, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{db_val:.1f} dB")

        peak_x = int(bar_width_max * 0.707)
        painter.setPen(QColor(180, 180, 180))
        painter.drawLine(40 + peak_x, 0, 40 + peak_x, H)