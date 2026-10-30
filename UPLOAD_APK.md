# Uploading an existing DSH APK for controlled audit

Repository: `u2584604327-a11y/dshe` (**PRIVATE** as checked during setup).

## First asset to upload

Use the already-verified historical v135 baseline, not an unverified patched build.

- Release tag: `dsh-baseline-v135`
- APK filename: `DSH0.4.1-v135-browser-native-device-v1.3.5-fixed-signature.apk`
- SHA-256: `394adfbe85b81ce46c285b1c531ffa307432d777e17af04fe5418272c5cc2e99`
- Package: `com.dsh.android`
- Expected versionCode: `135`
- Expected certificate: `90072b7de43e96999be92d99869ce5e5b7639b5f2449417b99a1790831b60ff8`

This APK is about 147 MB, so **upload it as an attachment to a GitHub Release**, not as a normal tracked repository file.

1. Open `https://github.com/u2584604327-a11y/dshe/releases/new`.
2. Enter the exact tag `dsh-baseline-v135`; select `main` as its target.
3. Use release title `DSH v135 fixed-certificate baseline — private audit only`.
4. Mark the release **Pre-release**. Do not describe it as a new production version.
5. Attach the APK with the exact filename above.
6. Save the release and confirm the asset appears. A new release is stored on GitHub's servers even when the repository is private; anyone granted repository access may be able to download it.
7. Go to `Actions → APK baseline identity audit (no signing) → Run workflow → v135`.
8. Read the actual job results and stop on any hash, version, package or certificate mismatch.

If you instead have the already-signed **v138 P0 test APK**, create a separate
`dsh-p0-v138` pre-release with filename
`DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk`.
Its expected SHA-256 from the build report is
`3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5`.
Do not treat the reported v138 digest as independently verified until the
workflow reports PASS.

## Never upload

- The fixed signing `.p12`, `.jks`, private key, keystore password or backup.
- Real diagnostic bundles, log files, unredacted traces, cookies, account tokens,
  API keys, chat databases or profiles.
- A rebuilt APK before reviewing whether it still contains embedded sensitive
  data and until native/Node security gates are closed.

The release audit only validates identity. It **does not** repair diagnostic
upload, browser state, device settings, UID/session isolation or JavaScript
features. A valid v135/v138 signature is not acceptance for a new v139 build.

## Current state

- GitHub repository and manual verification workflow: initialized.
- Uploaded release APK: **NONE at the time of this note**.
- Original project Gradle/Kotlin host: **NOT PRESENT**.
- APK build: **NOT RUN**.
- Signature of a new APK: **NOT VERIFIED**.
- ART / real device v139: **NOT VERIFIED**.
