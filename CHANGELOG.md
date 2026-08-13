# Changelog

All notable changes are documented here. This project follows semantic
versioning; release dates use ISO 8601.

## Unreleased

## 1.4.0 - 2026-08-12

### Added

- A backend startup and reconnection screen with progress, elapsed time,
  failure details, and retry controls.
- Clearly separated AI result cards that open the verified full source record.
- Frontend, backend, translation, version, Rust, and clean-clone CI checks.
- A fully resolved Python runtime lock file used by setup, CI, and sidecar builds.

### Changed

- Search, chat, history restore, note autosave, import, and project switching
  now isolate stale asynchronous work instead of applying it to a new context.
- Gemini integration now uses the supported `google-genai` SDK.
- Desktop startup owns and monitors one backend process and can restart it after
  a crash.
- Documentation, package metadata, and the in-app About panel consistently use
  AGPL-3.0-only.

### Fixed

- Search placeholder ordering and empty-project isolation.
- Project-name path traversal, unsafe shared-library deletion races, concurrent
  upload collisions, silent CSV imports, and MOBI/AZW3 source-name mismatches.
- Settings persistence errors, note autosave races, and cross-platform data-path
  migration.

## 1.3.3

See the repository tag for the original 1.3.3 release state.
