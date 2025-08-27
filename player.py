import sounddevice as sd
import soundfile as sf
import numpy as np
import threading

class AudioPlayer:
    def __init__(self):
        self.stream = None
        self.data = None
        self.samplerate = 44100
        self.position = 0
        self.is_playing = False
        self.output_device = None
        self._lock = threading.Lock()

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