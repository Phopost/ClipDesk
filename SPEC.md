# ClipDesk — SPEC & Decisions

Status of this document: reflects the code as built. Items not yet verified are marked **UNVERIFIED**.

## 1. Target & assumptions
- Windows 10/11 x64 (development machine: Windows 10 Home 19045, AMD64).
- Output: MP4 (video) and MP3 (audio). Platforms: YouTube (incl. Shorts), TikTok.
- Only content the user is entitled to download. No DRM / access-restriction bypass.
- No guarantee every clip is downloadable forever: platforms change; the engine (yt-dlp) is a separate process so it can be replaced independently.

## 2. Locked stack
| Part | Choice |
|---|---|
| GUI | PySide6 6.12.0, Qt Widgets (no WebEngine) |
| Download engine | yt-dlp 2026.10.21, external process via QProcess |
| Media | FFmpeg / FFprobe 9.0.2 (gyan.dev full build, GPL) |
| JS runtime | Node.js 24.x passed to yt-dlp (`--js-runtimes`) |
| Storage | SQLite (`~/.clipdesk/clipdesk.db`) |
| Tests | pytest + pytest-qt |

## 3. Architecture rules (enforced in code)
1. GUI never builds download commands; the controller + adapters do.
2. Format choices come only from the source's real format list (`format_selector`).
3. No blocking network/process calls on the GUI thread (QProcess, worker QThread for FFprobe).
4. Every task has `task_id`; every retry has a new `attempt_id`. Controller callbacks compare `attempt_id`, so late events from an old attempt are dropped.
5. Raw tool output never reaches the UI directly: users see `ErrorCode` messages (Thai); raw text is kept in `error_detail` ("ดูรายละเอียด").
6. One task failing never touches other tasks (per-task adapter, work dir, state).

## 4. Task lifecycle
```
QUEUED -> RESOLVING -> DOWNLOADING -> POSTPROCESSING -> VERIFYING -> COMPLETED
any active -> CANCELLING -> CANCELLED        error -> FAILED        retry: FAILED -> QUEUED (new attempt_id)
```
- **RESOLVING re-reads the source** (does not trust format data fetched earlier). If the quality the user chose no longer exists the task fails with `FORMAT_UNAVAILABLE`; quality is never downgraded silently.
- Success is declared only after FFprobe verification passes and the file is published.
- Cancel: state -> CANCELLING immediately, process tree killed (Job Object), our own work dir removed.

## 5. File safety
- Name template `{title} [{media_id}].{ext}`; Thai/Unicode kept; illegal chars, reserved names, trailing dots, `..` handled; length capped keeping the id.
- Never overwrite: duplicates get ` (2)`, ` (3)`; `safe_move` refuses if the destination exists (checked at publish time, so two tasks racing for one name cannot clobber each other).
- Each task has its own work dir; removed on success/cancel, kept on failure for retry.

## 6. Behaviour decisions
- A source that genuinely has no audio track is not failed for missing audio (MP4 verification expects audio only if the source has one).
- "Reduce motion" setting disables the info-card animation.
- Default concurrency 1; max 3.
- No telemetry; history stays local.

## 7. Milestones
| # | Milestone | State |
|---|---|---|
| 0 | Environment + spec | done |
| 1 | Vertical slice (URL → metadata → download → verify) | code done; live run UNVERIFIED here |
| 2 | Quality & file handling | done (unit-tested) |
| 3 | Queue / state / cancel / history | done (unit-tested); cancel tree needs live test |
| 4 | UI polish (thumbnails, sound, theme) | done by other agents; not visually reviewed by me |
| 5 | Robustness + performance report | scripts exist; **no measured report yet** |
| 6 | Packaging / installer | build script exists; clean-machine test UNVERIFIED |

## 8. Known gaps (honest list)
- Live YouTube/TikTok download not confirmed end-to-end in this environment (earlier live test hit the missing JS runtime warning; fix is in the adapter work by another agent and needs a real run).
- Pause/resume not offered (deliberately).
- Minimise-time render throttling not implemented.
- Installer, code signing, upgrade/uninstall tests not done.
- Performance numbers (RAM/CPU of the whole process tree) not yet measured.
