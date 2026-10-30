# Original DSH v70 APK: offline lineage reference (2026-10-29)

## Source and handling

User supplied `DSH0.4.1-v70.apk`, SHA256 `d12735f679bdac29bd4f3c17425c738e0340aeae376f71eb675ad28cb878a430`, 147,052,182 bytes. This is a **third-party compiled APK**, not the Android Studio/Gradle project. Inspected offline against the previously provided v135 package `DSH0.4.1-v135-browser-native-device-v1.3.5-fixed-signature.apk`, SHA256 `394adfbe85b81ce46c285b1c531ffa307432d777e17af04fe5418272c5cc2e99`, 147,351,542 bytes.

The raw v70 APK **has not been committed or uploaded** to GitHub; this report contains only extracted structural metadata, hashes and DEX method identifiers.

## Reproducible comparison findings

- Both APKs have 970 same-named ZIP entries. 967 entries were compared by **actual SHA256 of uncompressed bytes**, and are identical. Exactly three differ: `AndroidManifest.xml`, `classes.dex`, `assets/browser-tool.zip`.
- Binary AXML attribute `android:versionCode`: **70 → 135**. Manifest XML otherwise byte-for-byte equal. This was verified against the binary AXML string pool; just one byte in the typed integer value differs.
- `classes.dex` length is identical at **9,735,984 bytes**. Only **156 bytes** differ, including **24 DEX checksum/header bytes**. The actual changed code regions are limited to these existing method code items:
  1. `Lcom/dsh/android/browser/AiBrowserView;->loadUrl(Ljava/lang/String;)V` (code_off 3,429,912)
  2. `Lcom/dsh/android/browser/BrowserBridge;->opEval(Ljava/lang/String;)Lorg/json/JSONObject;` (code_off 3,455,192)
  3. `Lcom/dsh/android/browser/BrowserBridge;->opEval$lambda$20(Ljava/lang/String;Lcom/dsh/android/browser/AiBrowserView;Lkotlin/jvm/functions/Function1;)Lkotlin/Unit;` (code_off 3,452,304)
- `assets/browser-tool.zip` changed from 10,107 bytes to 313,703 bytes.
- `classes2.dex`, `assets/logs-tool.zip`, `assets/browser-pane.zip`, and `assets/dsh-fetch-guard.mjs` retain exact content SHA256.

## Signing identity: critical update-safety constraint

APK Signature Scheme **v2** signed certificate extracted directly from the APK Signing Block:

- v70: SHA256 `ef6afe33330839ed6d6739fb4d4bb84d358fd7bec8c1116c97309f92d9d3f385`, subject `CN=DSH Android,O=DSH,C=CN`.
- v135: SHA256 `90072b7de43e96999be92d99869ce5e5b7639b5f2449417b99a1790831b60ff8`, subject `O=Local Test Build,CN=DSH Browser Mod Test`.

**Different signing certificates.** Standard Android in-place upgrades do not accept unrelated signer changes. There is no evidence of a compatible signing rotation lineage. Do not advise uninstalling the original v70 app or claim that a test-signed v139 will update it without data loss. Determine which signer the user's *currently installed* DSH actually uses, before any final upgrade plan. Cert subject is not proof of ownership.

## Direct engineering implications

1. v70 is a valuable **behavioral comparison / original-code reference** for the browser. Examine exactly the three changed methods above to diagnose v135+ browser `loadUrl` and `opEval` regressions, including the reported `IllegalAccessError`; no unsupported claim that these differences caused the bug until Android runtime reproduces it.
2. The base of an in-place update to the already modified v138 must remain its exact SHA-pinned APK and signer. **Do not switch the production update signing identity to v70's original certificate** without possessing its legitimate signing private key and proof of app ownership/rights.
3. This v70 APK does **not** provide the missing Gradle build files, native host source code, Node sandbox or signing private key. It does not by itself remove P5 real user-button / one-shot approved send wiring, same-UID Node filesystem/network egress, ART feature validation or data-preserving update blockers.
4. Continue implementation with connected GitHub tools and controlled GitHub Actions; ChatGPT Work usage credits are **not technically required** for those tools. No production signing or APK publish until authorized release gates pass.
5. This is a third-party application: respect applicable licenses and redistribution rights; keep original binary and sensitive app data private.

Status: `V70_V135_BINARY_COMPARISON=PASS`; `ORIGINAL_GRADLE_PROJECT_AVAILABLE=NO`; `V70_V135_CERT_COMPATIBILITY=NO`; `OFFICIAL_V139_RELEASE=BLOCKED_HOST_AND_SIGNING`.
