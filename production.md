# Production Readiness — Orx: The Ascension of the Prime Cy-Orx

## Overview
Hybrid Python/C++ pseudo-3D retro-shooter with RPG progression.

## Current Gaps

### 1. Build System
- `setup.py` and `pyproject.toml` exist but no reproducible build environment
- C++ component via `CMakeLists.txt` — no CI build matrix for cross-platform
- **Action**: Add GitHub Actions build matrix (Linux, macOS, Windows), pin all dependencies

### 2. Packaging & Distribution
- No installer or distribution package
- Users must clone repo and run manually
- **Action**: Package with PyInstaller / Nuitka for single-binary distribution, publish on Itch.io

### 3. Asset Management
- No asset versioning or integrity checks
- No fallback if assets are missing
- **Action**: Add asset manifest with SHA256 hashes, bundle with installer

### 4. Save System
- Save file at `.orx_save.json` — no encryption, no corruption recovery
- **Action**: Add atomic writes, checksum validation, optional encryption

### 5. Error Reporting
- No crash logging or telemetry
- `game.log` exists but unstructured
- **Action**: Add structured logging, optional opt-in crash reporting (Sentry)

### 6. Performance
- No frame time profiling or optimization targets
- No graphics settings menu
- **Action**: Add FPS counter (dev), resolution/quality settings, profiler markers

### 7. Cross-Platform
- Linux-only in practice
- Python and CMake suggest multi-platform but untested
- **Action**: Test on Windows (DirectX/Vulkan), macOS (Metal), add platform-specific workarounds

### 8. Game Polish
- No main menu, settings screen, or pause menu
- No audio mixing or volume controls
- **Action**: Implement pause menu, settings persistence, audio slider

### 9. Legal
- No LICENSE file in the repo
- **Action**: Add LICENSE (GPL/MIT/Apache) before public distribution

## Quick Wins
1. Add LICENSE file
2. Set up GitHub Actions build matrix for Linux/macOS/Windows
3. Add atomic save with corruption detection
4. Add pause menu + FPS counter
