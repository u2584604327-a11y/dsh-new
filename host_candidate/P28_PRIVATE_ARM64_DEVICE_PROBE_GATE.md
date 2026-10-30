# P28 private exact-original v138 Node ARM64 device probe

## Explicit authorization and storage scope
The repository is confirmed PRIVATE by authenticated GitHub API.
The user explicitly approved making the APK containing original Node
available as a private GitHub Actions artifact to install on their own phone.
This is not authorization for any public release, external device-farm
provider, or Cloudflare/production deployment.

Private ZIP artifact retention: 7 days (subject to repository settings).
It contains an APK, a SHA256SUMS.txt file and a short private readme.
The disposable GitHub runner deletes original signed v138 input, derived
runtime files and its ephemeral signing key after upload or failure.

## Strict app boundaries
- Entirely separate package com.dsh.p28.nodeprobe, never com.dsh.android.
- Ephemeral test signing key, never original DSH signing credentials.
- Android 14+ / API34, arm64-v8a only.
- No manifest uses-permission entries; specifically no INTERNET or storage.
- User must click Start within the locally installed P28 UI.
- IsolatedService, non-exported, Android Binder sender UID authentication.
- Only exact original sha256 Node executable with fixed --version argument.
- All ten original shared ELF byte SHA256 identities checked before running.
- Six versioned SONAME libraries from P25 pinned alias preload mapping.
- No arbitrary JS, shell, URL, plugins, file attachments or diagnosis upload.
- Results are displayed locally with user-initiated Copy-to-clipboard.
- Node child UID is not independently measured; no false child-UID claim.
- Node network/file sandbox tests and entire DSH functional integration
  remain NOT TESTED even if Node --version succeeds.

## Build gates
- Download only exact SHA-pinned v138 release asset in ephemeral CI.
- Reuse P21 original input ELF closure and P25 original library alias stager,
  preserving all 11 original AArch64 ELF bytes, including sqlite missing SONAME.
- Embed signed APK asset JSON pin record for every original ELF alias.
- No extra native libraries; all 11 native ZIP entries stored and 16K aligned.
- Enforce unique package name and manifest has no Android permissions.
- Sign with fresh 30-day temporary PKCS12 cert, verify via apksigner, zipalign.
- Never use/upload original DSH signing key.
- Upload ONLY private Actions artifact, never GitHub Releases or PR attachments.
- No real physical ARM64 test has been run by CI; final boot remains pending
  until user explicitly runs the test app and shares local results.

## Reporting
P28_PRIVATE_REPO_VERIFIED=YES
P28_EXACT_V138_ELF_APK_BUILD=CI_PENDING
P28_PRIVATE_SIGNED_TEST_ARTIFACT=CI_PENDING
P28_REAL_DEVICE_ARM64_NODE_VERSION=NOT_TESTED
P28_REAL_NODE_NETWORK_AND_PRIVATE_FS_ISOLATION=NOT_TESTED
P28_DSH_V139_RELEASE=BLOCKED
