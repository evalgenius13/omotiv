import os
import torch
import torchaudio
import numpy as np
import tempfile
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

def get_downloads_folder():
    """Return the user's Downloads folder path."""
    return os.path.join(os.path.expanduser("~"), "Downloads")

class MDXModelWrapper:
    """Wrapper for MDX vocal removal model with CPU-only processing."""
    def __init__(self, model_path, status_callback=None):
        self.model_path = model_path
        self.separator = None
        self.status_callback = status_callback

    def __call__(self, waveform, sample_rate=44100):
        try:
            if self.separator is None:
                if self.status_callback:
                    self.status_callback("Loading MDX vocal removal model (CPU-only)...")
                try:
                    from audio_separator.separator import Separator
                except ImportError as e:
                    raise ImportError("audio-separator package not found. Please install it with: pip install audio-separator") from e

                # Use a user-writable temp directory for outputs
                output_dir = os.path.join(tempfile.gettempdir(), "omotiv_outputs")
                os.makedirs(output_dir, exist_ok=True)
                # Force CPU-only processing by setting environment variables
                os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
                os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
                os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Disable CUDA

                # Only use supported args for Separator
                self.separator = Separator(
                    output_dir=output_dir,
                    output_format="wav"
                )
                self.separator.load_model(self.model_path)

            if self.status_callback:
                self.status_callback("Processing with MDX model (CPU-only)...")

            # Convert waveform to proper format for saving
            if isinstance(waveform, torch.Tensor):
                waveform_tensor = waveform.cpu()  # Force CPU
            else:
                waveform_tensor = torch.from_numpy(waveform).float()

            # Ensure proper dimensions for saving
            if waveform_tensor.dim() == 1:
                waveform_tensor = waveform_tensor.unsqueeze(0)
            elif waveform_tensor.dim() == 3:
                waveform_tensor = waveform_tensor.squeeze(0)

            # Use a temp file for input
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, "input_audio.wav")

            try:
                torchaudio.save(temp_path, waveform_tensor, sample_rate)
                if self.status_callback:
                    self.status_callback("Running MDX separation...")

                output_files = self.separator.separate(temp_path)

                vocals, instrumental = None, None

                if self.status_callback:
                    self.status_callback("Loading separated stems...")

                # Handle different return formats
                if isinstance(output_files, list):
                    for file_path in output_files:
                        if os.path.exists(file_path):
                            filename = os.path.basename(file_path).lower()
                            if 'vocal' in filename or 'voice' in filename:
                                vocals, _ = torchaudio.load(file_path)
                            elif 'instrumental' in filename or 'music' in filename or 'no_vocals' in filename:
                                instrumental, _ = torchaudio.load(file_path)
                            elif vocals is None:
                                vocals, _ = torchaudio.load(file_path)
                            elif instrumental is None:
                                instrumental, _ = torchaudio.load(file_path)
                elif isinstance(output_files, dict):
                    for key, file_path in output_files.items():
                        if os.path.exists(file_path):
                            if 'vocal' in key.lower():
                                vocals, _ = torchaudio.load(file_path)
                            elif 'instrumental' in key.lower():
                                instrumental, _ = torchaudio.load(file_path)

                # If we still don't have both, check the output directory
                if vocals is None or instrumental is None:
                    output_dir = self.separator.output_dir
                    for file in os.listdir(output_dir):
                        if file.endswith('.wav'):
                            file_path = os.path.join(output_dir, file)
                            if 'vocal' in file.lower() and vocals is None:
                                vocals, _ = torchaudio.load(file_path)
                            elif 'instrumental' in file.lower() and instrumental is None:
                                instrumental, _ = torchaudio.load(file_path)

                if vocals is None or instrumental is None:
                    raise ValueError("Could not find both vocal and instrumental stems in output")

                return [vocals, instrumental]

            finally:
                # Always clean up temp files
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

        except Exception as e:
            if self.status_callback:
                self.status_callback(f"MDX processing error: {str(e)}")
            raise

    def cleanup(self):
        if self.separator is not None:
            try:
                if hasattr(self.separator, 'cleanup'):
                    self.separator.cleanup()
            except Exception:
                pass
            self.separator = None

class AudioProcessor(QObject):
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(str)

    def __init__(self, model_manager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.cancelled = False
        self._current_mdx_model = None

    def cancel(self):
        self.cancelled = True
        if self._current_mdx_model:
            try:
                self._current_mdx_model.cleanup()
            except Exception:
                pass

    @pyqtSlot(str, str, list)
    def run(self, input_path, output_path, instruments_to_remove, progress_callback=None, status_callback=None, cancelled=None):
        def emit_status(msg):
            if status_callback:
                status_callback(msg)
            else:
                self.status_updated.emit(msg)

        def emit_progress(val):
            if progress_callback:
                progress_callback(val)
            else:
                self.progress_updated.emit(val)

        def is_cancelled():
            if cancelled:
                return cancelled()
            else:
                return self.cancelled

        try:
            self.cancelled = False
            emit_status("Loading audio file...")
            waveform, sr = torchaudio.load(input_path)

            instrument = instruments_to_remove[0].lower() if instruments_to_remove else "vocals"

            # --- MDX Vocal Removal (CPU-only) ---
            if instrument == "vocals":
                emit_status("Starting vocal removal with MDX...")
                emit_progress(20)
                try:
                    model_name = "UVR-MDX-NET-Inst_HQ_1.onnx"  # Fixed to match your working model
                    emit_status(f"Loading MDX model: {model_name}")
                    mdx_model = MDXModelWrapper(model_name, emit_status)
                    self._current_mdx_model = mdx_model
                    emit_progress(40)
                    
                    if is_cancelled():
                        mdx_model.cleanup()
                        return None
                        
                    sources = mdx_model(waveform, sr)
                    emit_progress(70)
                    
                    if is_cancelled():
                        emit_status("Processing cancelled.")
                        mdx_model.cleanup()
                        return None
                        
                    if len(sources) >= 2:
                        instrumental = sources[1]
                    else:
                        raise ValueError("Expected 2 sources from MDX model")
                    
                    mdx_model.cleanup()
                    
                    emit_status("Saving instrumental stem...")
                    emit_progress(90)
                    
                    downloads_dir = get_downloads_folder()
                    base_filename = os.path.basename(input_path)
                    base, ext = os.path.splitext(base_filename)
                    if not ext:
                        ext = ".wav"
                    out_path = os.path.join(downloads_dir, f"{base}_instrumental{ext}")
                    
                    if not isinstance(instrumental, torch.Tensor):
                        instrumental = torch.from_numpy(instrumental).float()
                    if instrumental.dim() == 1:
                        instrumental = instrumental.unsqueeze(0)
                    elif instrumental.dim() == 3:
                        instrumental = instrumental.squeeze(0)
                        
                    torchaudio.save(out_path, instrumental, sr)
                    emit_progress(100)
                    emit_status(f"Processing complete. Saved to {out_path}")
                    self.processing_finished.emit(out_path)
                    return out_path
                    
                except Exception as e:
                    emit_status(f"MDX processing failed: {str(e)}")
                    emit_status("Falling back to Demucs...")
                    # Fall through to Demucs section

            # --- Demucs Separation ---
            from demucs.apply import apply_model
            model_name = "htdemucs_ft"
            emit_status(f"Loading Demucs model: {model_name}")
            emit_progress(20)
            
            try:
                model = self.model_manager.load_model_safely(model_name, emit_status)
                model = model.to(self.model_manager.device)
            except Exception as e:
                emit_status(f"Demucs model loading failed: {str(e)}")
                self.processing_finished.emit("")
                return None

            if is_cancelled():
                emit_status("Processing cancelled before start.")
                return None

            emit_status("Running Demucs separation...")
            emit_progress(50)

            try:
                with torch.inference_mode():
                    if waveform.dim() == 2:
                        waveform = waveform.unsqueeze(0)
                    sources = apply_model(
                        model,
                        waveform,
                        device=self.model_manager.device,
                        shifts=1,
                        overlap=0.25,
                        split=True,
                    )[0]

                    if is_cancelled():
                        emit_status("Processing cancelled mid-way.")
                        return None

                emit_status("Saving stems...")
                emit_progress(80)

                base_filename = os.path.basename(input_path)
                base, ext = os.path.splitext(base_filename)
                if not ext:
                    ext = ".wav"
                downloads_dir = get_downloads_folder()
                saved_paths = []
                
                for i, name in enumerate(model.sources):
                    if is_cancelled():
                        emit_status("Saving cancelled.")
                        return None
                    if name.lower() == instrument:
                        continue  # Skip the requested instrument
                    stem_path = os.path.join(downloads_dir, f"{base}_{name}{ext}")
                    torchaudio.save(stem_path, sources[i].cpu(), sr)
                    saved_paths.append(stem_path)

                emit_progress(100)
                if saved_paths:
                    emit_status(f"Processing complete. Saved: {', '.join(saved_paths)}")
                    # Return first saved path for consistency with MDX
                    self.processing_finished.emit(saved_paths[0])
                    return saved_paths[0]
                else:
                    emit_status("No stems were saved.")
                    self.processing_finished.emit("")
                    return None

            except Exception as e:
                emit_status(f"Demucs processing failed: {str(e)}")
                self.processing_finished.emit("")
                return None

        except Exception as e:
            emit_status(f"Error: {str(e)}")
            self.processing_finished.emit("")
            return None