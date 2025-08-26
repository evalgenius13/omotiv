import os
import torch
import torchaudio
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from demucs.apply import apply_model

def get_downloads_folder():
    return os.path.join(os.path.expanduser("~"), "Downloads")

class AudioProcessor(QObject):
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(str)

    def __init__(self, model_manager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    @pyqtSlot(str, str, list)
    def run(self, input_path, output_path, instruments_to_remove):
        try:
            self.cancelled = False
            self.status_updated.emit("Loading audio file...")
            waveform, sr = torchaudio.load(input_path)

            model_name = "htdemucs_ft"
            self.status_updated.emit(f"Loading model: {model_name}")
            self.progress_updated.emit(20)

            model = self.model_manager.load_model_safely(
                model_name, self.status_updated.emit
            )
            model = model.to(self.model_manager.device)

            if self.cancelled:
                self.status_updated.emit("Processing cancelled before start.")
                return

            self.status_updated.emit("Running separation...")
            self.progress_updated.emit(50)

            with torch.inference_mode():
                sources = apply_model(
                    model,
                    waveform.unsqueeze(0),
                    device=self.model_manager.device,
                    shifts=1,
                    overlap=0.25,
                    split=True,
                )[0]

                if self.cancelled:
                    self.status_updated.emit("Processing cancelled mid-way.")
                    return

            self.status_updated.emit("Combining stems (muting selected instrument)...")
            self.progress_updated.emit(80)

            # Mute the selected instrument by skipping its stem
            mute_indices = [i for i, name in enumerate(model.sources) if name in instruments_to_remove]
            backing = None
            for i, stem in enumerate(sources):
                if i in mute_indices:
                    continue
                backing = stem if backing is None else backing + stem

            # Normalize
            backing = backing / max(backing.abs().max().item(), 1)

            # --- FIXED OUTPUT FILENAME LOGIC ---
            # Compose output filename as: filename-no_{instrument}-omotiv.ext
            removed = '-'.join(instruments_to_remove)
            base_filename = os.path.basename(input_path)
            base, ext = os.path.splitext(base_filename)
            if not ext:
                ext = ".wav"
            downloads_dir = get_downloads_folder()
            output_file = os.path.join(
                downloads_dir,
                f"{base}-no_{removed}-omotiv{ext}"
            )
            torchaudio.save(output_file, backing.cpu(), sr)

            self.progress_updated.emit(100)
            self.status_updated.emit("Processing complete.")
            self.processing_finished.emit(output_file)

        except Exception as e:
            self.status_updated.emit(f"Error: {str(e)}")