# P12: previous DSH-version Library recovery used for real host-button candidate
Date: 2026-10-29. Private repository, source-only feature candidate.

## Historical artifacts inspected (Library, user-provided/generated)

1. `DSH_v137_NATIVE_RECOVERY_RESULTS.zip` — recovered Java **pseudocode** and DEX call graph. **Not** complete original Kotlin, license grant, or buildable Gradle project.
2. `DSH_v137_NATIVE_RECOVERY_FROM_APK_AUDIT.zip` — historical compiled DEX symbols and binary structural recovery. Not buildable Kotlin source.
3. `DSH_v1.3.7_WORK_HANDOFF_SOURCE_ONLY.zip` — browser-tool, browser-pane, Mobile UI and Market JavaScript with browser tests; no original Android host source.
4. `DSH_V139_NATIVE_INTEGRATION_SOURCE_AND_EVIDENCE.zip` — bounded host DEX patch candidate and P1 native components, with explicit lack of original Activity hook.
5. `DSH_APK_BROWSER_LAB_FULL_SOURCE_v1.zip` — **Cloudflare browser lab source** (seven entries including worker.js), not a full APK app.

No private third-party APK or full recovered third-party source was copied to this repo. Only identifiers, test evidence and independent original source written for this feature.

## Exact original host target observed in v137 recovered pseudocode

`LogViewerActivity.bindActions()` attaches:
- `R.id.logExport` (the existing export button) -> `bindActions$lambda$22` -> `exportBundle()`.
- `R.id.logUpload` (the existing upload button) -> `bindActions$lambda$23` -> `upload()`.

The original `exportBundle$lambda$41` / `upload$lambda$49` directly call `DiagnosticBundle.build$default`. They are **not** trustworthy consent gates. The P10 candidate disables all analyzed legacy external direct ZIP-build calls and must remain fail-closed even when a new button handler is installed.

## New P12 original Java adapter (authored separately)

`host_candidate/p12_native/com/dsh/p12/P12LogViewerReviewEntry.java`:
- Expects a **real, exact** `com.dsh.android.LogViewerActivity` instance, invoked only from a trusted native Activity lifecycle after original `bindActions()` has created views.
- Requires a host-supplied exact HTTPS destination in a native allowlist, never a string from Node, WebView, JS bridge or Intent extras.
- Rebinds the existing `logExport` and `logUpload` user click listeners to a **local-only** safe preview chooser.
- Creates/validates native UID-owned **0700** root and child queue, uses no directory chmod on existing, foreign or symlinked paths.
- Delegates final direct-child file descriptor pinning, strict schema projection, review/consent/revoke to the existing P5 `AndroidFdQueue` and `NativeDiagnosticReview` implementation.
- Accepts only directory-entry names matching the controlled `.json` schema. No legacy ZIP, raw log lines, arbitrary file picker or generic Node-file access granted.
- Maintains P5's **send default deny** because original approved network transport is not connected; nothing is uploaded. Empty native queue is a clean in-app disabled-state notice.
- Registers native lifecycle cleanup on stop/destroy; new host code does not remove or modify the original diagnostic files.
- Explicitly **not automatically installed** into the DSH product. A documented native `LogViewerActivity.onResume`/post-bind hook or an independently audited application-level lifecycle broker is still necessary.

## Verification and stop conditions

- Source compile/D8 against real Android API 35 and P5's nine pinned classes: [P12 compile Actions #40827286539](https://github.com/u2584604327-a11y/dshe/actions/runs/40827286539) PASS.
- Temporary P10/P11 + P12 third DEX and separate same-ephemeral-signer Android 35 instrumentation test is checked in `.github/workflows/unsigned-integration-lab.yml`. The **latest full run result** is required before claiming any original-button runtime PASS.
- Android original v138 data, signing identity and user phone are unchanged; test APK and key must be destroyed by CI.
- If legacy buttons are absent/renamed, original LogViewer cannot start, queue permissions fail, P5 dialog rejects input, unintended network egress appears, or ART throws `VerifyError`, report FAIL and do not ship.
- The previous P5 pass via test-only instrumentation did **not** mean the original LogViewer button was wired. P12 test-only calling `attach()` also does **not** mean the original Activity now calls it in its product lifecycle.

## Remaining release blockers

```text
HISTORICAL_SOURCE_REFERENCE=RECOVERED_PSEUDOCODE_ONLY
P12_ANDROID_SOURCE_COMPILES=PASS
P12_HOST_ORIGINAL_LOG_BUTTON_HOOK_AUTOINSTALLED=NO
P12_NATIVE_CONSENT_SEND_TRANSPORT=NO
NODE_GENERIC_SAME_UID_FILE_AND_NETWORK_ACCESS=NOT_ISOLATED
BROWSER_DEVICE_SETTINGS_UI=NOT_WIRED
WEBVIEW_PROFILES_AND_STORAGE_ISOLATION=NOT_VERIFIED
V139_COMPATIBLE_SIGNING_AND_DATA_PRESERVING_UPGRADE=NOT_VERIFIED
PRODUCTION_V139_APK=NOT_BUILT
```

## Actual Android 35 original LogViewer button test — VERIFIED PASS

Official private GitHub Actions: https://github.com/u2584604327-a11y/dshe/actions/runs/40827698165 — **SUCCESS**, completed 2026-10-29.

- Combined ART-safe P1–P10 native DEX, P11 Node summary-only asset and P5+P12 native classes were built together in one **disposable unsigned APK**. The third DEX contains **70 compiled P5+P12 class definitions**, SHA256 `8356fffceb6012c66432b72e1c7d93ce6e67322190e7b5a05e5c11efad2ef925`.
- A new ephemeral APK signing identity was generated inside private Actions; the app and test-only instrumentation package were signed with that same **nonproduction** certificate. Both APKs and keystore were deleted before the run completed.
- Android 35 emulator `adb install`, offline ART compile and MainActivity launch **PASS**. Existing P5 direct native-review Instrumentation **PASS**.
- P12's own separate Instrumentation started the original `com.dsh.android.LogViewerActivity` using the real app process and found both existing view IDs. It then called the P12 adapter from **trusted test instrumentation**, performed clicks on both native Export and Upload buttons and observed no raw export:
  - `P12_ORIGINAL_LOGVIEWER_LAUNCHED=PASS_ANDROID_FIXTURE`
  - `P12_EXISTING_EXPORT_UPLOAD_BUTTONS=BOTH_INTERCEPTED_TEST_CALL`
  - `P12_EMPTY_QUEUE_DEFAULT_DENY=NO_RAW_EXPORT_TRIGGERED`
  - `P12_NATIVE_APPROVED_TRANSPORT=NOT_CONNECTED`
  - `P12_ORIGINAL_ACTIVITY_LIFECYCLE_WIRED=NO_TEST_ONLY_ATTACH`
  - `INSTRUMENTATION_CODE: -1` (successful tests)
- The injected adapter preserves the native-origin-only entry; it does not bridge to model text, web pages or arbitrary files. Existing P10 fail-closed raw ZIP paths remain blocked. This test does **not** prove all other Node/Java generic file paths cannot access logs.

**Crucial next step:** add a trusted automatic hook from original `LogViewerActivity` lifecycle **after its native views are initialized**, without changing or duplicating user conversation and other native functions. Existing original DEX cannot invoke a new `com.dsh.p12` method without an additional method reference; do not fake this by simply packaging `classes3.dex`. A manifest-controlled native initializer or a fully audited DEX+Manifest integration would require separate isolated ART and UI verification. No fixed-signed `versionCode>138` APK is ready, and none should be installed on the real user device.
