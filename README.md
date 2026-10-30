# DSH Android — private APK baseline audit workspace

This private repository is a controlled APK audit workspace, **not a completed
Android source tree**. The installed phone remains on signed v138.

## What belongs here

Use **GitHub Releases** for the original APK baseline (it exceeds the ordinary
100 MB Git object limit). Do **not** commit the APK to Git history. Release
assets are accessible to people who have repository access.

| Release tag | Expected filename | Expected SHA-256 |
| --- | --- | --- |
| `dsh-baseline-v135` | `DSH0.4.1-v135-browser-native-device-v1.3.5-fixed-signature.apk` | `394adfbe85b81ce46c285b1c531ffa307432d777e17af04fe5418272c5cc2e99` |
| `dsh-p0-v138` | `DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk` | `3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5` |

The v138 hash originates from the user's P0 build receipt and is **not independently verified here**.

## Audit workflow

Run [`APK baseline audit`](../../actions/workflows/apk-baseline-audit.yml)
manually after adding a matching asset under its Release tag. This verifies
SHA-256, package identity, APK v2 signature, signing certificate fingerprint
and versionCode. It **never signs or modifies** the original APK and **never
uploads the APK as a workflow artifact**.

Expected certificate SHA-256:
`90072b7de43e96999be92d99869ce5e5b7639b5f2449417b99a1790831b60ff8`

The original APK may contain embedded credentials and proprietary application
code. Keep it in this private repo only if you are comfortable with GitHub
hosting it. The original signing P12/JKS and password must stay on a trusted
local machine; **do not put them in Git history, Releases, Actions Secrets, or
Artifacts at this stage**.

## Release blockers

A valid certificate does not prove that v139 fixes the original WebView
or diagnostic-upload issues. Before any new installation, verify the native
and Node diagnostic-send gate, user review, ART loading, session isolation,
data preservation and fixed-signature overlay update. **No v139 APK is
currently approved for release.**
