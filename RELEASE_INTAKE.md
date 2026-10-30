# Verified DSH private intake — 2026-10-29

**No additional upload is currently needed.** Three pre-existing GitHub Release assets were checked through GitHub Actions using exact SHA-256, the Android package identity, fixed certificate and offline P5/P6 regression.

## Confirmed Release assets

| Item | Actual release tag | Exact asset name | SHA-256 |
| --- | --- | --- | --- |
| v135 original APK | `dsh-baseline-v135dsh-baseline-v135` | `DSH0.4.1-v135-browser-native-device-v1.3.5-fixed-signature.1.apk` | `394adfbe85b81ce46c285b1c531ffa307432d777e17af04fe5418272c5cc2e99` |
| v138 signed P0 APK | `dsh-baseline-v135dsh-baseline-v135` | `DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk` | `3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5` |
| P6 source/asset staging | `dsh-source-v139-p6` | `DSH_V139_P6_NODE_CREDENTIAL_LOG_REDACTION_AND_ASSET_STAGING.zip` | `3af586c2c83d1aea67d119357672559eb09371c77ef4e06900bb697c06d11fd5` |

The APK tag is unintentionally duplicated and the original v135 filename has the suffix `.1`. The intake CI accounts for these **actual existing names**. Do not rename/delete or re-upload in an attempt to fix them; they are already hash-verified.

## Verified official Actions run

**PASS:** https://github.com/u2584604327-a11y/dshe/actions/runs/40810972896

- v135 APK identity, versionCode 135, APK v2 signer certificate: PASS.
- v138 APK identity, versionCode 138, APK v2 signer certificate: PASS.
- P6 Node/browser regression, P5 JVM synthetic tests, Android D8 class conversion: PASS.
- Fixed signing certificate SHA-256: `90072b7de43e96999be92d99869ce5e5b7639b5f2449417b99a1790831b60ff8`.

## Strict outstanding gates

This CI verified only the **historical signed APKs** and **source-only P5/P6 modules**. It did **not** generate a v139 APK. It did not prove that Node and native legacy diagnostics are completely gated, that the device settings UI exists in the installed APK, or that there is process/UID storage isolation.

- HOST_INTEGRATED: NOT_VERIFIED.
- NATIVE_AND_NODE_EGRESS_CLOSED: NOT_VERIFIED.
- DEVICE_UI_INTEGRATED: NOT_VERIFIED.
- STORAGE_ISOLATION: NOT_VERIFIED.
- V139_APK_BUILT: NO.
- V139_FIXED_SIGNATURE: NOT_VERIFIED.
- ART_AND_REAL_DEVICE: NOT_VERIFIED.

Signing secrets, JKS/P12, passwords, API keys and user diagnostic archives must **never** be uploaded. Installed phone v138 remains unchanged. Do not uninstall, downgrade or clear private app data.

## Subsequent work

Review and integrate the already-developed P2 bounded DEX patches, P5 native UI and total diagnostic-send gate, P6 JS overlay, and independent runtime privacy verification in a controlled Android host or sandbox. No new installation or sensitive network tests until required security gates pass.
