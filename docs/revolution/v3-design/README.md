# CityNexus Revolution V3 | Original 10-screen design reference

> STATUS: assets verified from user-uploaded archives on 2026-10-20; **the original binary PNG/JPEG/HTML set is not in this directory until the local import succeeds**. Do not treat the appearance of this README as the successful binary upload.

## Verified source archives

- **Complete source**: CityNexus_Revolution_V3_UI_Design_and_Flow.zip
  - SHA-256: af084281d7b3f05cee235650c57e9708a759da21f2a7316ddbc62571681c4543
  - 7,242,967 bytes; 41 valid entries: 10 PNG (860 x 1864), 10 standalone HTML pages, index.html, one full interaction specification Markdown, 2 text references, 17 JPG assets.
- **PNG-only source**: CityNexus_Revolution_V3_10_Independent_UI_PNG.zip
  - SHA-256: ee6f1d92ca81a3b6d5b6a010756bddc7bd3e7c83e4ab7e298374fe5164983093
  - 5,138,397 bytes; 10 PNG + README + SHA256 manifest. All 12 shared files are byte-for-byte identical to the complete source, so **import the complete ZIP once**.
- Both ZIP archives pass CRC verification. The embedded SHA256 manifest matches all 10 PNG files.

## Import into this product branch (Codex on the Windows developer machine)

Read and execute the checked-in **IMPORT_FROM_LOCAL.ps1** script. It locates the complete ZIP in common user Downloads/Desktop locations, or accepts an explicit ArchivePath. It rejects the wrong archive hash, checks the ZIP layout and each PNG manifest digest, imports all 41 originals to this directory, and optionally commits/pushes only those design files to the existing product branch.

    powershell -NoProfile -ExecutionPolicy Bypass -File .\docs\revolution\v3-design\IMPORT_FROM_LOCAL.ps1 -CommitAndPush

If auto-discovery does not find the complete ZIP, use:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\docs\revolution\v3-design\IMPORT_FROM_LOCAL.ps1 -ArchivePath "C:\path\to\CityNexus_Revolution_V3_UI_Design_and_Flow.zip" -CommitAndPush

Do **not** mistake the fact that a user uploaded the ZIP to a ChatGPT conversation for its presence on Codex's local Windows disk. If the archive is absent, report that concrete blocker and do not manufacture or regenerate the original screenshots.

## Intended committed directory

- index.html: locally browsable catalogue.
- 01_探索首页.png through 10_多人决策.png: ten original independent PNG screens.
- Matching 01–10 HTML files: linked layout and navigation prototypes.
- assets/*.jpg: 17 illustrative photographic assets.
- CityNexus_V3_交互与实现规格.md: original authored product flow and UI requirements.
- README_先看这里.txt, MANIFEST_SHA256.txt: original archive provenance and checksums.

All pictures, map routes, fares, hotel availability, reviews and Guardian incidents in this reference are **illustrative fixtures**, not live verified events or booking receipts. HTML prototypes have browser-side concept interactions, not a real Agent backend. The real product must preserve live provider provenance and existing member-bound plan authority.

## Implementation coordination

- Central delivery issue: https://github.com/Canshu-King/CityNexus/issues/42
- Codex product branch/PR: https://github.com/Canshu-King/CityNexus/pull/23
- Qoder capability/PR: https://github.com/Canshu-King/CityNexus/pull/35
- Baseline behavior contract: ../REVOLUTION_V3_AGENT_NATIVE_UI_IMPLEMENTATION_20261020.md

**Binary asset import is completed only when the 41 actual files appear at this path in the GitHub branch and the imported PNG SHA-256 values match the manifest.**
