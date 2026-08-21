# Iconik Storage Locator v7.0.0

Adds a local macOS UI wrapper and a public GitHub Pages browser version while keeping the original CLI behavior intact.

## Artifacts

After running `dev/build.sh`, copy these files into this release folder and upload the zip files to the GitHub release:

* `Iconik_Locator_App_arm64.zip`
* `iconik_locator_arm64.zip`
* `checksums.txt`

Intel artifacts are produced by the same build script when an x86_64/Rosetta Python is available.

## Changes

* Added `dev/iconik_locator_gui.py` for a Tkinter desktop app.
* Updated `dev/build.sh` to build both the CLI and GUI app for Apple Silicon and Intel macOS.
* Added `index.html` for the GitHub Pages browser tool and download documentation.
* Updated links to point to `MichaelBrandonFalk/iconik-locator`.
