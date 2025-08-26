# Omotiv v1.0 - Core Features Roadmap

## 1. Audio Input
- [ ] Load audio files (WAV/MP3/FLAC)
    - File dialog for selection
    - Supported format detection
- [ ] Loopback recording (capture from any audio source)
    - Integrate system loopback (sounddevice/PyAudio)
    - UI for start/stop recording

## 2. Backing Track Creation
- [ ] Remove vocals, bass, drums, or other instruments
    - Demucs stem separation
    - UI: radio buttons/checkboxes for instrument selection
- [ ] Get instant clean backing track
    - Merge stems minus selected instrument(s)
    - Preview in app

## 3. Recording
- [ ] Full song recording over backing track
    - Playback + simultaneous recording
    - Save output to temp/defined folder
- [ ] Section recording with trim bars (punch-in style)
    - UI: trim/punch-in bars on waveform
    - Record only selected section
- [ ] Save your takes
    - Save each take with timestamp/name
    - UI: list of takes, option to play/delete

## 4. Export
- [ ] Export your recordings
    - Export selected takes to disk
    - Format selector (WAV/MP3)
- [ ] Export backing tracks
    - Save processed backing track to disk
- [ ] WAV/MP3 formats
    - Conversion/routing via torchaudio/soundfile or pydub

---

## Suggested Order of Implementation

1. **Audio Input**
   - File loading first, then loopback recording.
2. **Backing Track Creation**
   - Instrument removal, then instant preview/merge.
3. **Recording**
   - Full song recording, then punch-in/section recording.
4. **Export**
   - Export recordings and backing tracks, format selection.

---

## Notes

- Remove all non-core features from UI and codebase before starting v1.0 development.
- Keep UI minimal/clean for MVP.
- Ensure error handling and user feedback for each task.
- Test on multiple OS (Windows/Mac/Linux) for audio I/O compatibility.

---

**Ready to start?**  
Let me know if you want an actionable checklist in GitHub issues, or a file-by-file codebase cleanup plan!