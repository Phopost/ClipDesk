# AGENTS.md — ClipDesk Development & Release Directives

<!-- MANDATORY AI AGENT INSTRUCTIONS FOR CLIPDESK -->

## 1. Project Overview & Architecture
- **Language/Framework:** Python 3.13, PySide6 (Qt for Python).
- **Core Engine:** `app/core/` (Multi-fragment download engine, controller, state).
- **UI & Themes:** `app/ui/` (Sky-Blue Wave Glass UI, custom QPainter widgets in `wave_widgets.py`).
- **Packaging:** PyInstaller onedir (`packaging/build_windows.py`), C# WinForms stub installer (`packaging/build_installer.py`).
- **Vendor Tools:** `vendor/windows-x64/` (`yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`).

## 2. Mandatory Workflow on EVERY Update or Task Completion
Whenever modifying code, UI, or assets in this repository, you **MUST ALWAYS** execute the following steps in sequence:

1. **Verify Tests:**
   ```bash
   python -m pytest -q
   ```
   All unit and integration tests must pass before proceeding.

2. **Rebuild Application & Installer (if runtime/UI/assets changed):**
   ```bash
   python packaging/build_windows.py --skip-test
   python packaging/build_installer.py
   ```
   Ensures `dist/ClipDesk/ClipDesk.exe` and `~/Desktop/ClipDesk-Setup.exe` are kept in sync.

3. **Update Version & Changelog:**
   - Update `app/version.py` if bumping version.
   - Summarize exact changes made.

4. **Publish to GitHub (`Phopost/ClipDesk`):**
   ```bash
   python tools/publish_to_github.py --version <VERSION> --message "<COMMIT_MESSAGE>" --notes "<RELEASE_NOTES>"
   ```
   This automatically pushes code to `main` branch and uploads the new `ClipDesk-Setup.exe` asset to GitHub Releases.

5. **Report to User:**
   - Clearly announce to the user:
     1. Current version (e.g. `v1.0.0`)
     2. Exact list of what was updated / changed
     3. Link to the GitHub repository commit and release download.
