# Iconik Storage Locator

The Iconik Storage Locator is a tool designed to quickly find the physical storage location (S3 URIs, HTTPS URLs, or local paths) of assets in Iconik. It now ships as a local macOS app, a CLI, and a browser tool on GitHub Pages.

## Download Iconik Locator

Get the latest version below. Extract the `.zip` and run the app or executable.

* [**Download macOS App (Apple Silicon / M1/M2/M3)**](https://github.com/MichaelBrandonFalk/iconik-locator/releases/latest/download/Iconik_Locator_App_arm64.zip)
* [**Download CLI for macOS (Apple Silicon / M1/M2/M3)**](https://github.com/MichaelBrandonFalk/iconik-locator/releases/latest/download/iconik_locator_arm64.zip)
* Intel builds are supported by `dev/build.sh` when an x86_64/Rosetta Python is available.

## Browser Version

Use the hosted browser tool here:

* [**Open Iconik Locator Web Tool**](https://michaelbrandonfalk.github.io/iconik-locator/)

The browser version sends requests directly from your browser to Iconik using the App-ID and Auth-Token you enter. Credentials are not committed to this repository.

> **Note:** If you get a security warning on macOS, you may need to go to *System Settings > Privacy & Security* to allow the application to run, or clear the quarantine attribute via terminal: `xattr -d com.apple.quarantine iconik_locator`

## Features

* Paste one Iconik asset link, share link, or asset UUID to get storage details.
* Share links default to listing every represented asset instead of stopping on multi-asset pages.
* Use the macOS UI wrapper without running terminal commands.
* Use the public GitHub Pages browser version when Iconik API access is allowed from your browser.
* **Reverse Lookup**: Paste an `s3://` URI to instantly find its corresponding Iconik Asset URL.
* Get the S3 URI directly in Terminal.
* If the storage URL cannot be converted to `s3://bucket/key`, the tool prints the best fallback URL returned by Iconik.
* For local, Lucid Link, or other non-S3 storage, the tool shows the storage path from Iconik file metadata when available.
* Located URI lines include online/offline status.
* `Output` / `Outputs` include only online storage locations.
* **Interactive Mode**: Rapidly perform multiple lookups in succession seamlessly crossing between Iconik URLs and S3 URIs.
* Dependency-free runtime (Python standard library only).

## Deliverables

After build:

* `dist/iconik_locator_arm64`
* `dist/iconik_locator_arm64.zip`
* `dist/Iconik Locator_arm64.app`
* `dist/Iconik_Locator_App_arm64.zip`
* `dist/iconik_locator_x86_64` and app equivalents when an x86_64/Rosetta Python is available.
* `dist/checksums.txt`

## Quick Single Lookup

Default output is `S3`.

```sh
./dist/iconik_locator_arm64 "https://app.iconik.io/asset/<asset-id>"
```

Terminal output starts with the located URI:

```text
Located URI
[ONLINE] s3://bucket/path/to/file.mov

Output
s3://bucket/path/to/file.mov
```

If Iconik exposes offline or missing replicas, they remain visible in `Located URIs` but are excluded from `Output` / `Outputs`:

```text
Located URIs
[ONLINE] s3://bucket/path/to/file.mov
[OFFLINE] local-storage/example.mov

Output
s3://bucket/path/to/file.mov
```

### Bidirectional Lookup

The Locator can map from S3 back to Iconik seamlessly. Paste an `s3://` URI:

```sh
./dist/iconik_locator_arm64 "s3://bucket/path/to/file.mov"
```

The tool will return the mapped Iconik Assets:

```text
Located Iconik Assets
1

Asset
My Asset Title
00000000-0000-0000-0000-000000000000

Iconik URL
https://app.iconik.io/asset/00000000-0000-0000-0000-000000000000
```

### Options

* `--uri-only`: Print only the URI.
* `--quiet`: Minimal output.
* `--copy`: Copy the first URI to the macOS clipboard.

## Output Formats

```sh
--output S3
--output HTTPS
--output FULL
```

`S3` is the default. `HTTPS` strips presigned query parameters. `FULL` preserves the full presigned URL returned by Iconik.

## Multi-Asset And Multi-Source Behavior

Share links:

* `--multi ALL` (Default)
* `--multi ERROR`
* `--multi FIRST`

Multiple storage locations for the selected file:

* `--multi-files ERROR`
* `--multi-files FIRST`
* `--multi-files ALL` (Default)

## Interactive Mode

For high-speed, successive lookups, run the tool without an input argument to enter **Interactive Mode**:

```sh
./dist/iconik_locator_arm64
```

Simply paste an Iconik link or UUID and press Enter. The tool will display the results and immediately prompt for the next one. Type `help` for instructions or `q` to quit.

## Build

```sh
cd dev
chmod +x build.sh
./build.sh
```

## Project Structure

* `dev/`: Development source code and build scripts.
  * `iconik_locator.py`: Main script.
  * `iconik_locator_gui.py`: macOS desktop UI wrapper.
  * `build.sh`: macOS build script.
* `index.html`: Public GitHub Pages browser tool and documentation/download page.
* `releases/`: Historical and packaged releases.
  * `v5.0.0/`: Legacy version.
  * `v6.0.0/`: Version 6.0.0 source.
* `README.md`: This file.
