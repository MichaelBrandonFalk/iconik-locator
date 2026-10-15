# Iconik Storage Locator v7.0.11

Native desktop downloads are now available for Windows and Linux Mint, alongside Mac.

* Windows 10/11, Intel/AMD 64-bit: extract the ZIP and run `Iconik Locator 7.0.11.exe`. Keep the `_internal` folder beside it.
* Linux Mint 21/22, Intel/AMD 64-bit: open the DEB in Package Installer, install it, then launch Iconik Locator from the application menu. A portable TAR.GZ is also available.
* Mac, Apple Silicon: extract the ZIP and open `Iconik Locator 7.0.11_arm64.app`.

Python and GUI libraries are included in the downloads. All app names and archives include the version. The existing icon, single lookup, bulk lookup, spreadsheet export, and S3 copy features are included.

Credentials use Windows Credential Manager, Linux Secret Service, or macOS Keychain. On Mint, unlock the login keyring in Passwords and Keys if needed. Unavailable credential storage shows a warning without blocking a successful lookup or writing the token to settings files.

## Validation

37 automated tests passed on the Windows and Ubuntu 22.04 builders. Both native packages passed GUI startup and button-layout checks on Single Lookup and Bulk Lookup at two window sizes. Linux was built and tested on Ubuntu 22.04, the Mint 21 base; it targets Mint 21/22 but has not been manually exercised on a Mint desktop. No live Iconik credentials were used during CI checks.

Build evidence: https://github.com/MichaelBrandonFalk/iconik-locator/actions/runs/38787876191

## Downloads

* `Iconik_Locator_App_v7_0_11_windows_x86_64.zip`
* `Iconik_Locator_App_v7_0_11_linux_amd64.deb`
* `Iconik_Locator_App_v7_0_11_linux_x86_64.tar.gz`
* `Iconik_Locator_App_v7_0_11_arm64.zip`
* `checksums.txt`
