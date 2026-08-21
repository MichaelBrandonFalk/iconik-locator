# Iconik Storage Locator v7.0.5

This release focuses on the local UI workflow and makes the downloadable app artifact versioned.

## Changes

* Default output is reset to `S3` for this version.
* The local app saves App-ID/Auth-Token and settings locally when the save option is enabled.
* Added a `Copy S3 Only` action for single and bulk results.
* Added a local `Bulk Lookup` tab for pasted rows, CSV upload, and XLSX upload. Spreadsheet files must use the header `iconik_url`.
* Added local bulk export as CSV or XLSX.
* Added browser bulk lookup from pasted rows or CSV upload. Browser export is CSV.
* Browser network failures now explain when Iconik/browser CORS is likely blocking the hosted page.
* The macOS app download is now versioned as `Iconik_Locator_App_v7_0_5_arm64.zip`.

## Browser Note

The browser version sends requests directly from the hosted GitHub Pages page to Iconik. If Iconik blocks that request with CORS, the browser version can fail even when credentials are valid. Use the local macOS app for reliable lookups and Excel/XLSX bulk work.

## Artifacts

* `Iconik_Locator_App_v7_0_5_arm64.zip`
* `iconik_locator_arm64.zip`
* `checksums.txt`
