"""
Recording Booth UI for Omotiv v1.0
Provides a clean interface for recording with separate volume controls.
No FX area included in this release.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Callable
import os

from audio.utils import AudioMixer, AudioTrack, AudioExporter, create_test_audio_data


class VolumeControl(ttk.Frame):
    """A reusable volume control widget."""
    
    def __init__(self, parent, label: str, initial_value: float = 1.0, callback: Optional[Callable] = None):
        super().__init__(parent)
        self.callback = callback
        
        # Label
        self.label = ttk.Label(self, text=label)
        self.label.pack(side=tk.TOP, padx=5, pady=2)
        
        # Volume slider
        self.volume_var = tk.DoubleVar(value=initial_value)
        self.slider = ttk.Scale(
            self, 
            from_=0.0, 
            to=1.0, 
            orient=tk.VERTICAL,
            variable=self.volume_var,
            command=self._on_volume_change
        )
        self.slider.pack(side=tk.TOP, padx=5, pady=5, fill=tk.Y, expand=True)
        
        # Value display
        self.value_label = ttk.Label(self, text=f"{initial_value:.2f}")
        self.value_label.pack(side=tk.TOP, padx=5, pady=2)
    
    def _on_volume_change(self, value):
        """Handle volume change."""
        volume = float(value)
        self.value_label.config(text=f"{volume:.2f}")
        if self.callback:
            self.callback(volume)
    
    def get_volume(self) -> float:
        """Get current volume value."""
        return self.volume_var.get()
    
    def set_volume(self, volume: float):
        """Set volume value."""
        self.volume_var.set(volume)


class RecordingBooth:
    """Main Recording Booth interface."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Omotiv v1.0 - Recording Booth")
        self.root.geometry("800x600")
        
        # Audio components
        self.mixer = AudioMixer()
        self.current_track: Optional[AudioTrack] = None
        self.input_volume = 1.0
        self.is_recording = False
        
        self._setup_ui()
        self._create_sample_tracks()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="Recording Booth", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Control panels
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.BOTH, expand=True)
        
        # Volume controls section
        volume_frame = ttk.LabelFrame(controls_frame, text="Volume Controls", padding=10)
        volume_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Input volume control
        self.input_volume_control = VolumeControl(
            volume_frame, 
            "Input Volume",
            initial_value=self.input_volume,
            callback=self._on_input_volume_change
        )
        self.input_volume_control.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Track volume control
        self.track_volume_control = VolumeControl(
            volume_frame,
            "Track Volume", 
            initial_value=1.0,
            callback=self._on_track_volume_change
        )
        self.track_volume_control.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Master volume control
        self.master_volume_control = VolumeControl(
            volume_frame,
            "Master Volume",
            initial_value=self.mixer.master_volume,
            callback=self._on_master_volume_change
        )
        self.master_volume_control.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Recording and playback section
        recording_frame = ttk.LabelFrame(controls_frame, text="Recording & Playback", padding=10)
        recording_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Recording controls
        record_controls = ttk.Frame(recording_frame)
        record_controls.pack(fill=tk.X, pady=(0, 10))
        
        self.record_button = ttk.Button(
            record_controls, 
            text="● Record", 
            command=self._toggle_recording
        )
        self.record_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(
            record_controls,
            text="■ Stop",
            command=self._stop_recording
        )
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.play_button = ttk.Button(
            record_controls,
            text="▶ Play Mix",
            command=self._play_mix
        )
        self.play_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Track list
        track_list_frame = ttk.Frame(recording_frame)
        track_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        ttk.Label(track_list_frame, text="Tracks:").pack(anchor=tk.W)
        
        # Track listbox
        self.track_listbox = tk.Listbox(track_list_frame, height=8)
        self.track_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.track_listbox.bind('<<ListboxSelect>>', self._on_track_select)
        
        # Track controls
        track_controls = ttk.Frame(recording_frame)
        track_controls.pack(fill=tk.X)
        
        ttk.Button(
            track_controls,
            text="Add Track",
            command=self._add_track
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            track_controls,
            text="Remove Track", 
            command=self._remove_track
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Export section
        export_frame = ttk.LabelFrame(controls_frame, text="Export", padding=10)
        export_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(
            export_frame,
            text="Export Mix",
            command=self._export_mix
        ).pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            export_frame,
            text="Export Stems",
            command=self._export_stems
        ).pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            export_frame,
            text="Export After Recording",
            command=self._export_after_recording
        ).pack(fill=tk.X, pady=(0, 5))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        self._update_track_list()
    
    def _create_sample_tracks(self):
        """Create some sample tracks for demonstration."""
        # Create sample tracks with test audio data
        track1 = AudioTrack("Bass", create_test_audio_data(4410, 110))  # 0.1 seconds at 110Hz
        track2 = AudioTrack("Melody", create_test_audio_data(4410, 440))  # 0.1 seconds at 440Hz
        
        self.mixer.add_track(track1)
        self.mixer.add_track(track2)
    
    def _update_track_list(self):
        """Update the track list display."""
        self.track_listbox.delete(0, tk.END)
        for i, track in enumerate(self.mixer.tracks):
            volume_info = f" (Vol: {track.volume:.2f})" if track.volume != 1.0 else ""
            mute_info = " [MUTED]" if track.muted else ""
            self.track_listbox.insert(tk.END, f"{track.name}{volume_info}{mute_info}")
    
    def _on_track_select(self, event):
        """Handle track selection."""
        selection = self.track_listbox.curselection()
        if selection:
            track_index = selection[0]
            if 0 <= track_index < len(self.mixer.tracks):
                self.current_track = self.mixer.tracks[track_index]
                self.track_volume_control.set_volume(self.current_track.volume)
                self.status_var.set(f"Selected: {self.current_track.name}")
    
    def _on_input_volume_change(self, volume: float):
        """Handle input volume change."""
        self.input_volume = volume
        self.status_var.set(f"Input volume: {volume:.2f}")
    
    def _on_track_volume_change(self, volume: float):
        """Handle track volume change."""
        if self.current_track:
            self.current_track.set_volume(volume)
            self._update_track_list()
            self.status_var.set(f"Track volume: {volume:.2f}")
    
    def _on_master_volume_change(self, volume: float):
        """Handle master volume change."""
        self.mixer.set_master_volume(volume)
        self.status_var.set(f"Master volume: {volume:.2f}")
    
    def _toggle_recording(self):
        """Toggle recording state."""
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()
    
    def _start_recording(self):
        """Start recording."""
        self.is_recording = True
        self.record_button.config(text="● Recording...", state="disabled")
        self.status_var.set("Recording... (simulated)")
        
        # Simulate recording by creating a new track with test data
        # In a real app, this would capture actual audio input
        self.root.after(2000, self._finish_recording)  # Auto-stop after 2 seconds for demo
    
    def _finish_recording(self):
        """Finish recording and add the recorded track."""
        if self.is_recording:
            # Create a new track with recorded data (simulated)
            recorded_data = create_test_audio_data(8820, 220)  # 0.2 seconds at 220Hz
            # Apply input volume to the recorded data
            recorded_data = [sample * self.input_volume for sample in recorded_data]
            
            new_track = AudioTrack(f"Recording {len(self.mixer.tracks) + 1}", recorded_data)
            self.mixer.add_track(new_track)
            
            self._stop_recording()
            self._update_track_list()
            self.status_var.set("Recording complete")
    
    def _stop_recording(self):
        """Stop recording."""
        self.is_recording = False
        self.record_button.config(text="● Record", state="normal")
        if not hasattr(self, '_recording_finished'):
            self.status_var.set("Recording stopped")
    
    def _play_mix(self):
        """Play the mixed audio."""
        mixed_audio = self.mixer.mix_tracks()
        if mixed_audio:
            self.status_var.set(f"Playing mix ({len(mixed_audio)} samples)...")
            # In a real app, this would actually play the audio
            self.root.after(1000, lambda: self.status_var.set("Playback complete"))
        else:
            self.status_var.set("No audio to play")
    
    def _add_track(self):
        """Add a new track."""
        track_name = f"Track {len(self.mixer.tracks) + 1}"
        new_track = AudioTrack(track_name, create_test_audio_data(2205, 330))  # 0.05 seconds
        self.mixer.add_track(new_track)
        self._update_track_list()
        self.status_var.set(f"Added {track_name}")
    
    def _remove_track(self):
        """Remove the selected track."""
        if self.current_track and self.current_track in self.mixer.tracks:
            track_name = self.current_track.name
            self.mixer.remove_track(self.current_track)
            self.current_track = None
            self._update_track_list()
            self.status_var.set(f"Removed {track_name}")
        else:
            messagebox.showwarning("No Selection", "Please select a track to remove.")
    
    def _export_mix(self):
        """Export the mixed audio."""
        filename = filedialog.asksaveasfilename(
            title="Export Mix",
            defaultextension=".wav",
            filetypes=[("Wave files", "*.wav"), ("All files", "*.*")]
        )
        if filename:
            mixed_audio = self.mixer.mix_tracks()
            if AudioExporter.export_wav(mixed_audio, filename):
                self.status_var.set(f"Mix exported to {filename}.txt")
                messagebox.showinfo("Export Complete", f"Mix exported successfully to {filename}.txt")
            else:
                messagebox.showerror("Export Error", "Failed to export mix")
    
    def _export_stems(self):
        """Export individual tracks as stems."""
        directory = filedialog.askdirectory(title="Select Export Directory")
        if directory:
            base_filename = os.path.join(directory, "omotiv_stems")
            if AudioExporter.export_stems(self.mixer, base_filename):
                self.status_var.set("Stems exported successfully")
                messagebox.showinfo("Export Complete", f"Stems exported to {directory}")
            else:
                messagebox.showerror("Export Error", "Failed to export stems")
    
    def _export_after_recording(self):
        """Export options available after recording/overdubbing."""
        if not self.mixer.tracks:
            messagebox.showwarning("No Tracks", "No tracks available to export.")
            return
        
        # Show export options dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Export After Recording")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Export Options:", font=("Arial", 12, "bold")).pack(pady=10)
        
        ttk.Button(
            dialog,
            text="Export Final Mix",
            command=lambda: [self._export_mix(), dialog.destroy()]
        ).pack(pady=5, fill=tk.X, padx=20)
        
        ttk.Button(
            dialog,
            text="Export Individual Tracks",
            command=lambda: [self._export_stems(), dialog.destroy()]
        ).pack(pady=5, fill=tk.X, padx=20)
        
        ttk.Button(
            dialog,
            text="Cancel",
            command=dialog.destroy
        ).pack(pady=10)


def create_recording_booth():
    """Create and run the recording booth application."""
    root = tk.Tk()
    app = RecordingBooth(root)
    return root, app


if __name__ == "__main__":
    root, app = create_recording_booth()
    root.mainloop()