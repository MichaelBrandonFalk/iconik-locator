# Iconik Storage Locator v7.0.3

Improves failed lookup messages.

## Changes

* Browser tool no longer shows only `Failed to fetch` for network-level failures.
* Credential failures now explain when Iconik rejected the App-ID/Auth-Token.
* Permission failures now explain that the token may not have asset/file lookup access.
* Missing or inaccessible assets now explain that the URL may be wrong or the API user may not have access.
* Desktop app uses the same friendlier error wording for common lookup failures.

## Artifacts

* `Iconik_Locator_App_arm64.zip`
* `iconik_locator_arm64.zip`
* `checksums.txt`

Intel artifacts are produced by the same build script when an x86_64/Rosetta Python is available.
