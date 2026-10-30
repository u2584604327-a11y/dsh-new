# DSH v139 P2+P6 real baseline preflight — 2026-10-29

## Primary verified run

GitHub Actions run: https://github.com/u2584604327-a11y/dshe/actions/runs/40812133057

Status: **SUCCESS**. This run reads existing signed v138 APK and P6 Release sources, but **never generates a modified APK or installs anything**.

### Verified input identity

- Repo: `u2584604327-a11y/dshe` (private).
- v138 input: `DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk`, SHA256 `3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5`.
- P6 input: `DSH_V139_P6_NODE_CREDENTIAL_LOG_REDACTION_AND_ASSET_STAGING.zip`, SHA256 `3af586c2c83d1aea67d119357672559eb09371c77ef4e06900bb697c06d11fd5`.
- Original v135 and v138 package identity, v2 signature and fixed certificate were previously verified in https://github.com/u2584604327-a11y/dshe/actions/runs/40810972896

### Native bounded DEX static verification

Current private files:
- `host_candidate/patch_deny.py`
- `host_candidate/patch_browser.py`
- `host_candidate/patch_privacy.py`
- `host_candidate/verify_p2_scope.py`

The workflow **replays** four diagnostic-deny methods, two browser getter/open methods and one WebView configuration method from the exact v138 `classes.dex`, entirely in memory.

- Combined target DEX SHA256: `9a7cd89f4a5c86394770febf703a9345a44d8c12c39abec9d494635587d8f221` — PASS.
- 7 targeted original method bodies — scope PASS.
- 52,004 other code method bodies unchanged — PASS.
- Only expected DEX header integrity fields and target instruction ranges changed — PASS.
- Reconstructed instructions, preserved code headers/handlers, DEX SHA-1 and Adler32 — PASS.
- No new DEX references — static scope PASS.
- **New signed DSH APK built: NO**.

This is **not** a run of these bytes under Android ART or a true connection of P5's new Java classes into the existing Android host. Four original upload-entry denials do **not** cover generic native uploads or arbitrary Node diagnostic-sending paths.

### P6 asset preimage compatibility

Current private verifier: `host_candidate/verify_p6_asset_preimages.py`.

The workflow compares these three v138 ZIP entries with the P6 overlay manifest, both by exact SHA256 and byte length:

- `assets/browser-tool.zip` — PASS.
- `assets/browser-pane.zip` — PASS.
- `assets/dsh-fetch-guard.mjs` — PASS.

All three replacement assets match their pinned P6 hashes; nested browser ZIP CRC checks PASS. This proves **static asset replacement compatibility**, not that a running DSH host loads the replacements or fixes the visible UI.

### CI artifact storage

One preceding CI run had `P2/P6` checks PASS but the final artifact upload failed because the GitHub Actions **artifact storage quota was exhausted**. The final successful workflow writes textual hashes and gating status to the job summary instead, with **no artifact upload**, and requires no additional user files.

## Remaining release blockers

| Gate | Status |
| --- | --- |
| Exact baseline inputs | PASS |
| v138 P2 bounded DEX candidate static replay | PASS |
| P6 three-resource overlay preimages | PASS |
| P5 single-use safe sender hooked into real native transport | NOT_IMPLEMENTED |
| Native and Node diagnostic sending fully closed against bypass | NOT_VERIFIED |
| Native user review dialog hooked to existing log UI | NOT_IMPLEMENTED |
| Device settings button attached to original browser title bar | NOT_IMPLEMENTED |
| viewport/DPR/UA real application and readback | NOT_VERIFIED |
| Separate browser profile, cookies and storage verified | NOT_IMPLEMENTED |
| Runtime JS asset migration into full original host | NOT_VERIFIED |
| VersionCode >138 APK build | NO |
| Original-certificate v139 signing | NO |
| Android ART, data-preserving offline install and real phone | NOT_VERIFIED |

**Do not sign, publish or install a new APK based on the static replay alone.** Keep original signing material out of GitHub and the existing phone v138 unchanged. The next required engineering work is *actual native/Node send-path integration* and *Android host UI integration*, which cannot be accomplished by merely appending the existing standalone Java classes to DEX.

## Native diagnostic upload call-graph and egress delta (verified 2026-10-29)

### Read-only original DEX invocation analysis

Source: `host_candidate/audit_native_upload_callgraph.py`

Verified GitHub Actions: https://github.com/u2584604327-a11y/dshe/actions/runs/40813846052

- 4,599 DSH application method implementations scanned.
- 6,149 direct app-to-app invocation pairs identified.
- 56 app-code direct calls to network-related Java APIs. These are **not** 56 confirmed diagnostic upload paths.
- Static audit detects 22 `LogUploader` method definitions and their caller sites.
- Confirmed original upload path: `LogViewerActivity.upload$lambda$49 → LogUploader.upload → upload$lambda$12 → doUpload`.
- Confirmed legacy retry path: `DshApplication.uploadPendingBundles → retryPending → retryPendingLocked → doUpload`.
- `doUpload` invokes `HttpURLConnection.getOutputStream()`; it is a concrete original native send sink.
- `LogCommandBridge` local export and `LogUploader.enqueue` are not by themselves evidence of a network request.

### Real DEX patched sink removal

Source: `host_candidate/verify_diagnostic_egress_sites.py`

Verified GitHub Actions: https://github.com/u2584604327-a11y/dshe/actions/runs/40814002535

- Original v138 exact SHA256: `3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5`.
- P2 in-memory candidate exact `classes.dex` SHA256: `9a7cd89f4a5c86394770febf703a9345a44d8c12c39abec9d494635587d8f221`.
- Original diagnostic-focused classes contained **5** direct HTTP/URL sink instructions (constructor, `openConnection`, `setRequestMethod`, `setDoOutput`, `getOutputStream`).
- P2 candidate contains **0** such direct sink instructions in the same classes: **PASS**.
- Full P2 seven-method byte-range and non-target method invariants: **PASS**, verified separately in the same run.
- P6 static three-file overlay preimages: **PASS**.

**Limitations:** This shows removal of the known native diagnostic uploader HTTP implementation from a validated *uninstalled candidate DEX*. It does not exclude generic native bridge, reflection, JNI, additional HTTP libraries, Node outgoing requests, or other executable/network transports. It does not implement P5's approved transport and native review UI. The candidate DEX was never written into a signed APK and was not executed on Android ART.

- KNOWN_NATIVE_DIAGNOSTIC_HTTP_SINK_REMOVED_IN_CANDIDATE: **PASS**
- ALL_NATIVE_NODE_EGRESS_CLOSED: **NOT_VERIFIED**
- NATIVE_APPROVAL_UI_CONNECTED: **NO**
- DSH_V139_APK_BUILT: **NO**
- ART_AND_REAL_PHONE: **NOT_VERIFIED**
- PHONE_V138_CHANGED: **NO**

Do not upload signing material to GitHub or install/debug the current v138 online with sensitive data. The required next implementation is a controlled Android host path that routes all diagnostic send requests through the native per-bundle review and fail-closed transport, with isolated ART and offline device verification before signing.

## P5 Android native compilation + P2/P5/P6/P7 unsigned fusion (2026-10-29)

### Android-native compilation

PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40814642663

- All nine P5 Java sources from the **pinned** P6-embedded P5 archive compiled against Android API 35 using Java 8 language compatibility.
- D8 compiled them for Android minimum API 26.
- **63 P5 class definitions** in the resultant component DEX, including compiler-generated nested classes.
- No native Activity was wired into the installed original app and no ART execution happened.

### Fusion into one temporary UNSIGNED APK structure

P2+P5+P6 PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40814995654

P2+P5+P6+P7 PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40815688204

The private workflow dynamically downloads the exact v138 signed APK and exact P6 ZIP, replays the seven bounded P2 changes, compiles the nine P5 sources into `classes3.dex`, replaces three P6 assets and adds P7's narrowed `assets/logs-tool.zip` asset.

For the final P2+P5+P6+P7 **ephemeral unsigned** experiment:

- SHA-256 of bounded main DEX: `9a7cd89f4a5c86394770febf703a9345a44d8c12c39abec9d494635587d8f221`.
- SHA-256 of P5 additional DEX: `552d593f42596a624b36374243f48aec10ffec6a9006eaa1b4974bc84ffab56b`.
- P5 definitions added: **63**, and class descriptor collision with original two DEX files: **none**.
- P7 logs-tool replacement SHA-256: `71c92b1ec4facad6d443d3277e72303684751dc9f5ce44481db6aeb582082d58`.
- Original file entries verified byte-for-byte unchanged: **965**.
- Temporary unsigned, pre-zipalign APK SHA-256: `5643d1364d61bd447a3776f01edcb30982a0f288ea8719b126932726c91afdd5`.
- Temporary unsigned APK size before alignment: **147,382,039 bytes**.
- Android `aapt`, `zipalign`, ZIP CRC and DEX entry structural checks: PASS.
- APK original signature intentionally **invalidated** by repacking and the job requires `apksigner verify` to reject the result.
- The temporary APK was deleted on the GitHub Runner; no APK file was uploaded to Actions Artifacts or GitHub Releases.
- `versionCode` stays **138**, because this is a lab structure, not an approved v139 installation candidate.

### P7 Node diagnostic export AI-output containment

PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40815619962

Source: `host_candidate/patch_logs_export_output.py`.
Synthetic native mailbox regression: `host_candidate/test_logs_export.mjs`.

The original `logs` tool's `action:"export"` returned an absolute `bundlePath` and told the model it could send that ZIP. P7 still allows the native host to generate a local bundle, but exposes only a bounded success/failure, optional bounded byte count, and a requirement for native review. It drops the original mailbox's path, message, nested `details` and any synthetic sensitive canaries from **the model-facing result**. Other `summary` behavior was exercised and preserved. P7 is only in the **unsigned lab**; installed v138 is unchanged.

**Critical limitation:** the native mailbox itself can still contain a path. Node shares the application's UID and may access the private files directly; generic file transport or shell tools may bypass a model-output-only restriction. Neither P7 nor P5 adds a strong Node filesystem capability boundary. A reliable total diagnostic egress policy requires an isolated process/UID or a native-controlled private queue inaccessible to generic tools and enforcement at every diagnostic-capable transport. A separate user-approved sharing UI must be connected to the host to permit safe intentional sends. Do not assume unchanged ordinary attachments are blocked.

### Release blockers and next engineering requirements

- HOST_NATIVE_DIALOG_CONNECTED: **NO**.
- P5_TRUSTED_SINGLE_USE_TRANSPORT_CONNECTED: **NO**.
- LEGACY_NATIVE_AND_NODE_DIAGNOSTIC_EGRESS_TOTAL_GATE: **NOT_VERIFIED**.
- GENERIC_NODE_FILE_ACCESS_ISOLATION: **NOT_IMPLEMENTED**.
- STORAGE_AND_COOKIES_ISOLATION: **NOT_VERIFIED**.
- ART_RUNTIME_LOADING_TEST: **NOT_RUN**.
- VERSIONCODE_139_SIGNED_WITH_FIXED_CERT: **NO**.
- DATA_PRESERVING_DEVICE_INSTALL: **NOT_TESTED**.

**Do not sign, publish or install the ephemeral assembly.** It is not a ready APK, and no original fixed signing private key should be uploaded to GitHub. Continue with real native host invocation and Node process capability boundaries, not only more standalone JVM tests.

## P8 native mailbox path containment and disposable Android test (2026-10-29)

### Verified P8 native DEX modification

Source: `host_candidate/patch_native_export_reply.py`. Real v138+P2 in-memory replay: https://github.com/u2584604327-a11y/dshe/actions/runs/40817557005

The original `LogCommandBridge.doExport(Lorg/json/JSONObject;)V` (code offset 3,287,332) invokes `File.getAbsolutePath()` and writes `bundlePath` into its JSON reply. This was verified independently in https://github.com/u2584604327-a11y/dshe/actions/runs/40817381857.

P8 replaces four exact bytecode instructions at absolute DEX byte offsets **3,287,476–3,287,494**, 18 bytes total, with nine NOP code units. It preserves the original `DiagnosticBundle.build` call and bundle-size `JSONObject.put` operation. All other code method bodies remain identical and no new DEX refs were added. The full original v138 ZIP was kept intact; no signed update has been published.

- P2 combined DEX SHA256: `9a7cd89f4a5c86394770febf703a9345a44d8c12c39abec9d494635587d8f221`
- P2+P8 combined DEX SHA256: `d7a984597930c7599732d3d5c87df61d15c80bc4a1a942f0fd4d6db7dc2355b3`
- `NATIVE_EXPORT_REPLY_BUNDLE_PATH_REMOVED=PASS_STATIC`
- `ORIGINAL_DIAGNOSTIC_FILE_CREATION=UNCHANGED`
- `P7_NODE_AI_VISIBLE_PATH_REDACTED=PASS_SYNTHETIC`
- `NODE_SAME_UID_FILESYSTEM_ACCESS=UNRESOLVED`
- `P8_ART=NOT_VERIFIED`

### Disposable Android ART test — evidence boundary

A separate private Actions workflow builds the P2–P8 *lab only*, with a fresh non-original ephemeral signing key generated inside the runner, no GitHub artifact upload or GitHub Release, and a new offline emulator.

- The P2–P7 iteration at https://github.com/u2584604327-a11y/dshe/actions/runs/40817134153 **installed successfully** on Android 35, but the test's implicit `MAIN/LAUNCHER` intent did not resolve. No app-start or ART execution PASS was claimed. The signing key and APK were deleted.
- The follow-up P2–P8 iteration at https://github.com/u2584604327-a11y/dshe/actions/runs/40817726760 adds offline `cmd package compile -m speed -f`, then checks a manifest-derived explicit Activity or `com.dsh.android.MainActivity` and monitors fatal errors. Its actual Actions result must be consulted independently before recording an ART PASS.
- Android lab certificates **differ from** the original fixed signer, so this cannot upgrade the installed personal v138 app and must never be distributed as a real APK.

### Native browser IllegalAccessError constraint

Verified read-only two-DEX audit: https://github.com/u2584604327-a11y/dshe/actions/runs/40816918553. The original `AiBrowserView.currentWebView()` is `private final` (`0x12`) and has 18 `invoke-direct` calls, none directly from `BrowserBridge` in either original DEX. Blindly changing it to public would require modifying the call instruction types and is **not an authorized bounded fix**. No such potentially unsafe flags were changed.

**Still blocked:** actual P5 native UI-to-legacy Activity wiring, default-closed one-shot transport integration, Node privilege/UID filesystem bypass, storage isolation, original-certificate v139 signing, and data-preserving real-phone upgrade. Never mark the temporary lab APK ready to install.

## ART-safe replacement: Android 35 emulator launch PASS (2026-10-29)

The **old** original P2 `patch_deny.py` is **ART_FAIL** (illegal `fill-array-data-payload` spans an existing try boundary); do not reuse it for a real APK. The replacement `host_candidate/patch_deny_art_safe.py` removes the pseudo-payload entirely, using existing original DEX strings and ordinary NOPs, preserving the pre-existing code headers/try table. Static gate: https://github.com/u2584604327-a11y/dshe/actions/runs/40818265220

### New independently pinned DEX sequence

- ART-safe native deny P1 DEX SHA256: `8565675b7da207e858f1c3dd69896ce5a68015a24605157a4a11b259218119b6`
- Browser getter patch P2 SHA256: `e392e65bf7592ddd9531af81459e678d1462423abed526d5eeddac248ab158a4`
- WebView settings patch P3 SHA256: `8682204473860802b17b18ab487fa72380eb076d37495d2de4abb76abad0df6b`
- Native P8 `bundlePath` suppression SHA256: `086d0e431515d9f5072109e96a94cbbe7f37c578f1cc68722bcd787881d1acb3`
- P5 D8 extension SHA256: `552d593f42596a624b36374243f48aec10ffec6a9006eaa1b4974bc84ffab56b`

### Genuine disposable Android ART and launch

Full P1–P8 fusion, test-sign/install, offline ART compilation and app launch: **PASS** at https://github.com/u2584604327-a11y/dshe/actions/runs/40818441206

- SHA256 of ephemeral unsigned pre-alignment fusion: `6c492f80df83f77dfc34f9deb64ad0825a5f490e6cf8c72ddd80a7fea87887f7`.
- 965 untouched APK file entries verified byte-for-byte, P5 63 compiled classes inserted as `classes3.dex`.
- GitHub runner generated a new ephemeral self-signed keystore, **not** the original production certificate. Test APK and keystore were deleted after emulator testing, never published.
- On a clean Android 35 emulator, APK install was **PASS**; offline `cmd package compile -m speed -f com.dsh.android` was **PASS**.
- Explicit MainActivity launch succeeded, DSH process remained alive across the observation window; prior `VerifyError` was not detected. `DISPOSABLE_ANDROID_EMULATOR_LAUNCH=PASS`.
- This proves a **limited startup ART gate**, not every P5 class or feature. No user data from a real device was present.
- P5 new classes were compiled and packaged but original Activity is still **not wired** to `NativeDiagnosticReview`; no trusted native one-shot send has been enabled.
- The P7/P8 path redaction does **not** create a separate Node UID or block generic same-UID reads. This remains a hard security blocker.

### Current trustworthy gates

```text
EXACT_V138_INPUT_SHA=PASS
OLD_P2_ART=FAIL_DO_NOT_SHIP
NEW_ART_SAFE_DENY_STATIC=PASS
NEW_P1_TO_P8_FUSED_APK_STRUCTURE=PASS
DISPOSABLE_ANDROID35_OFFLINE_ART_COMPILE=PASS
DISPOSABLE_ANDROID35_MAINACTIVITY_LAUNCH=PASS
P5_NEW_CLASSES_EXECUTED=NOT_VERIFIED
TRUSTED_NATIVE_REVIEW_WIRED=NO
ALL_NODE_AND_NATIVE_DIAGNOSTIC_EGRESS_CLOSED=NOT_VERIFIED
APP_BROWSER_DEVICE_SETTINGS_UI_WIRED=NO
WEBVIEW_STORAGE_ISOLATION=NOT_VERIFIED
PRODUCTION_V139_VERSIONCODE_GREATER_THAN_138=NO
SIGNED_WITH_ORIGINAL_FIXED_CERTIFICATE=NO
USER_PHONE_UPDATE_AND_DATA_RETENTION=NOT_TESTED
```

**Important:** No full DSH v139 release has been built or authorized. Do not share the throwaway emulator-signed APK as an installation candidate; do not ask the user to uninstall their installed v138.

## P9 native legacy export fail-closed — Android emulator PASS (2026-10-29)

- Independently verified SHA-pinned static P9 native patch: https://github.com/u2584604327-a11y/dshe/actions/runs/40819381448
- Full P1–P9 ephemeral unsigned fusion + temporary nonproduction signature + fresh offline Android 35 emulator test **SUCCESS**: https://github.com/u2584604327-a11y/dshe/actions/runs/40819495503
- Candidate primary `classes.dex` SHA256: `db1d61fdae52f55b569cc92bc82afbc82c31f305295ef4a2fd3a431177038d29`
- P9 changes exactly **8 bytes** in `LogCommandBridge.doExport`, replacing the original `DiagnosticBundle.build$default` call and move-result with `const/4 v3,#0` and NOPs. The following existing `if-eqz v3` error path is preserved; no new raw diagnostic archive should be created through this old export path. **Runtime export button behavior has not been UI-tested.**
- Other **52,010** method code bodies remain byte identical relative to P8.
- All 965 other original APK entries remain byte-identical in final fusion, P5 D8's 63 class definitions remain separately bundled in `classes3.dex`, and the P6/P7 assets remain pinned.
- Offline ART package compilation = **PASS**, emulator APK install = **PASS**, explicit `MainActivity` launch and process survival = **PASS**; no known startup VerifyError.
- No fixed signer, no release, no user's real app data touched. Temporary APK and temporary keystore were removed by the Runner, versionCode still **138**.
- **Functional tradeoff:** the old full diagnostic ZIP export has been intentionally disabled while native trusted per-bundle approval is unavailable. Existing logs/ZIPs are not deleted. Ordinary file/image send method bodies were not modified by P9.
- **Remaining same-UID risk:** Node can still read pre-existing diagnostic files and may ask for raw `logs.read`/`logs.crashes` content; P9 does not introduce OS process/UID isolation or comprehensively gate generic Node tools.
- **Release hard blockers:** No trusted host UI hook to P5 `NativeDiagnosticReview`; `ApprovedDiagnosticSendGate` still has no bound transport; no full native/Node diagnostic egress enforcement; no Android WebView storage profile separation; no real-phone data-preserving update; no original-certificate versionCode>138 APK.

```text
P9_STATIC_DEFAULT_DENY_RAW_ZIP=PASS
P9_ANDROID35_EMULATOR_INSTALL=PASS
P9_ANDROID35_OFFLINE_ART_COMPILE=PASS
P9_ANDROID35_MAINACTIVITY_LAUNCH=PASS
P9_DIAGNOSTIC_EXPORT_BUTTON_RUNTIME_TEST=NOT_RUN
P5_TRUSTED_REVIEW_WIRED=NO
GENERIC_NODE_SAME_UID_EXFILTRATION_BLOCKED=NO
PRODUCTION_V139_APK=NOT_BUILT
USER_PHONE_V138=UNCHANGED
```

Do NOT publish or sign the ephemeral candidate. Avoid asserting total privacy gate closure based only on P9 disablement.

## P10 all original external direct ZIP builder calls denied — emulator PASS (2026-10-29)

Verified by four independent pieces of private Actions evidence:

1. Original direct native bundle constructor reachability audit: https://github.com/u2584604327-a11y/dshe/actions/runs/40819987540
2. Exact return/branch context analysis for `LogViewerActivity.exportBundle$lambda$41` and `LogUploader.collectCrashScenes`: https://github.com/u2584604327-a11y/dshe/actions/runs/40820114161
3. P10 exact v138 → ART-safe P1 → browser/privacy → P8/P9 → P10 direct callsite and method scope regression: https://github.com/u2584604327-a11y/dshe/actions/runs/40820289771 (**SUCCESS**)
4. P1–P10 temporary unsigned APK + ephemeral throwaway signer + fresh offline Android 35 simulator: https://github.com/u2584604327-a11y/dshe/actions/runs/40820408827 (**SUCCESS**)

### Native changes and proof boundary

- Original `DiagnosticBundle.build$default` direct DEX callers were identified in `LogCommandBridge.doExport`, `LogViewerActivity.exportBundle$lambda$41`, `LogViewerActivity.upload$lambda$49` and `LogUploader.collectCrashScenes`. Three more calls were within `DiagnosticBundle`'s own implementation. These are a **static inventory of direct calls**, not reflection/JNI/Node reachability.
- The first two existing sends had already been denied by ART-safe P1, P9. P10 now replaces two more external builder callsites, **8 bytes each** (existing register set to null + NOP), with the original failure/result branches preserved.
- `ALL_DIRECT_EXTERNAL_DIAGNOSTIC_BUILD_DEFAULT_CALLS=ZERO_STATIC` in the candidate original primary DEX.
- Full P10 candidate primary DEX SHA256: `cfe19482edcd4bea7c1b476bb90da5b956759c98a2bb101ee9dd459be4a15474`.
- P5 native additional DEX remains 63 class definitions. P6/P7 resources retain their pinned preimages.
- Both original ZIP-building methods (`LogViewerActivity` manual export, uploader crash scene collection) are deliberately **unavailable** pending native trusted review. Local log browsing, summary, and ordinary attachment send instruction bodies were not rewritten by these patches. Runtime manual export UX remains untested.
- Android 35 fresh emulator install: **PASS**; offline ART package compile: **PASS**; explicit MainActivity launch and process survival: **PASS**. This is a limited launch check, not native P5 dialog or full feature validation.
- All generated APKs were **temporary emulator-signed**, versionCode remains **138**, and were deleted from Runner after use. No original signing key used, no GitHub APK release created, and user's existing phone v138 is unchanged.

### Release blockers and mandatory next work

- `P5_TrustedNativeReview` still **not invoked** from `LogViewerActivity` lifecycle / user gesture, and `ApprovedDiagnosticSendGate` transport is intentionally unbound. Actual one-package native preview and one-shot dispatch are **not implemented in original host**.
- Existing ZIPs and raw logs remain readable by Node with the same UID; Node generic shell/file/network tooling has not been isolated. Blocking ZIP creation through original known DEX direct callers is **not** a comprehensive Node exfiltration prevention layer.
- No full Android/Kotlin Gradle host project is present in this repository; binary-level DEX patches alone do not provide a safe way to wire new P5 Activity methods or guarantee all network sinks.
- Browser device settings UI is not hooked to the original activity; same-app WebView cookie/storage profile separation remains unverified.
- No original-certificate signed `versionCode > 138` release, no data-preserving user phone update, and no ART proof of every P5 class under UI flows.

```text
P10_ALL_ORIGINAL_DIRECT_EXTERNAL_ZIP_BUILD_CALLS=ZERO_STATIC
P10_EXACT_DEX_AND_METHOD_SCOPE=PASS
P10_ANDROID35_INSTALL=PASS
P10_ANDROID35_ART_COMPILE=PASS
P10_ANDROID35_MAINACTIVITY_LAUNCH=PASS
P10_NATIVE_MANUAL_EXPORT_USER_FLOW=NOT_VERIFIED
P5_NATIVE_CONSENT_UI_WIRED=NO
P5_EXCLUSIVE_APPROVED_SEND_TRANSPORT_WIRED=NO
GENERIC_NODE_UID_FILE_EXFILTRATION_CLOSED=NO
REAL_PHONE_DATA_PRESERVATION=NOT_TESTED
FIXED_CERT_SIGNED_V139_APK=NOT_BUILT
```

**Do not ship the test-signed APK or expose a v139 installation link.** It does not include the production signer or complete host and egress integration.

## P11 summary-only Node tool + P5 Android UI runtime gate (2026-10-29)

### P11: source + Node execution PASS, production still unchanged

- P11 private GitHub Actions: https://github.com/u2584604327-a11y/dshe/actions/runs/40822332733 — **SUCCESS**.
- Source: `host_candidate/patch_logs_metadata_only.py`, using exact SHA-pinned original v138 `assets/logs-tool.zip` plus P7 export-output redaction.
- New P11 ZIP SHA256: `29bcf54bb00ea989516b8bc7bdeb6bbd68f9a11a85082273399eb3597cdd76a0`.
- The AI `logs` plugin now denies `read`, `crashes` and `export` before dispatching any mailbox command, regardless of attempted arguments. `summary` projects only bounded integer counters and fixed explanatory strings; it discards native arbitrary `message`, `headline`, `lastExit`, `logText`, `sceneText`, `bundlePath` and nested `details`. Synthetic canary leak test PASS.
- The native log viewer, on-disk data, existing ZIP files and other Node/shell generic file tools are **not** protected by this specific plugin-only restriction. The Node process still shares application UID; **total native/Node diagnostic egress closed = NO**.
- P11 resource has been added to the ephemeral P1–P10 assembler, with exact pinned hash. This is **not an installed user update**.

### P5 actual Android UI smoke: newly discovered runtime boundary

- Same-ephemeral-signer Android instrumentation source: `host_candidate/test-only/com/dsh/p1/smoketest/DshInstrumentation.java`; the instrumentation package is never shipped or published.
- Original disposable Android 35 App and instrumentation APK build/installation worked in https://github.com/u2584604327-a11y/dshe/actions/runs/40821972738, but `NativeDiagnosticReview` UI was **not displayed**: the P5 `AndroidFdQueue` constructor raised `IOException`. Thus previous P5 Java compile and package success must **not** be called native UI runtime PASS.
- A subsequent bounded diagnostic https://github.com/u2584604327-a11y/dshe/actions/runs/40822506334 showed `FAIL_PHASE=NATIVE_PINNED_QUEUE`, `FAIL_REASON=SYNTHETIC_QUEUE_PERMISSIONS`. Its strict mode requirement rejects group/other-writable roots. Do **not** loosen the ownership/permissions checks.
- The instrumentation fixture now creates an explicitly native-owned mode `0700` private queue root under a disposable subdirectory; no app-shared filesDir mode is changed and no old logs are removed. The retest is https://github.com/u2584604327-a11y/dshe/actions/runs/40822933877, and remains **NOT_VERIFIED** until its actual result.
- This P5 UI test is intentionally invoked by a test harness from MainActivity, **not** by the original LogViewerActivity button. Even success cannot establish host UI wiring or one-shot transport integration.

```text
P11_NODE_LOG_MODEL_BOUNDARY=PASS_SYNTHETIC_REAL_PLUGIN
P11_FULL_APP_EGRESS=NOT_VERIFIED
P5_NATIVE_UI_ANDROID=NOT_VERIFIED_PENDING_0700_QUEUE_RETEST
P5_ORIGINAL_LOGVIEWER_HOOK=NO
P5_ONE_SHOT_SEND_CONNECTED=NO
ORIGINAL_CERT_V139_APK=NO
PHONE_V138_UNCHANGED=YES
```

## P11 + P5 trusted-native-dialog Android35 runtime proof — PASS (2026-10-29)

Authoritative private GitHub Actions: https://github.com/u2584604327-a11y/dshe/actions/runs/40823908102 — **SUCCESS**

This run used the exact SHA-pinned original v138 APK, the ART-safe P1–P10 main DEX, all original P5 Android classes compiled into `classes3.dex`, the P6 assets, and the P11 safe summary-only `assets/logs-tool.zip` replacement (SHA256 `29bcf54bb00ea989516b8bc7bdeb6bbd68f9a11a85082273399eb3597cdd76a0`). Both the main package and the instrumentation test package were signed with the **same disposable nonproduction key** inside an isolated runner. No original signing certificate/key was used.

### Concrete Android 35 results

- `ANDROID_ART_OFFLINE_PACKAGE_COMPILE=PASS`.
- `DISPOSABLE_ANDROID_EMULATOR_LAUNCH=PASS`.
- P5 `AndroidFdQueue` constructor **and descriptor-pinned read of exact synthetic `dsh-safe-diagnostic-v1` fixture = PASS**.
- P5 `NativeDiagnosticReview` **real Android `AlertDialog` shown with the fail-closed sending notice = PASS**. To avoid a false negative from a non-visible Accessibility tree, test-only instrumentation checks the actual `AlertDialog.isShowing()` and known fixed notice text on the UI thread. This bypasses **only the test's visibility detector**, not any app privacy/permission check.
- Malformed schema fixture triggered `NativeDiagnosticReview`'s native `DENIED/preview/UNSUPPORTED_OR_CHANGED_FILE` audit callback = PASS.
- `P5_NETWORK_SEND=NOT_CONNECTED`; no HTTP request, no real diagnostic bundle or user app data used.
- `LEGACY_HOST_BUTTON_WIRED=NO` is still a hard blocker: P5 UI was invoked directly by **temporary test instrumentation**, not by `LogViewerActivity`. No user-accessible P5 UI feature has been added to the installed app.
- Test used a dedicated app-owned mode **0700** private queue root. Earlier test attempt against the ordinary `filesDir` failed the intentionally strict P5 group/other-writable directory ownership gate; security checks were **not relaxed**.
- P11 `summary` numeric-only Node policy had independently passed a synthetic canary reply test in https://github.com/u2584604327-a11y/dshe/actions/runs/40822332733. This runtime run proves P11's resource was structurally incorporated in the lab APK; it does **not** prove all generic same-UID Node exfiltration has been stopped.
- The temporary app/test APKs and the ephemeral key were deleted by the CI runner. APK `versionCode` remains **138** for lab testing; user phone unchanged.

### Latest verified status

```text
P10_ORIGINAL_DIRECT_ZIP_CALLS=ZERO_STATIC
P11_NODE_LOGS_TOOL_SUMMARY_ONLY=PASS_NODE_CANARY_TEST
P11_ANDROID_APK_RESOURCE_FUSED=PASS
P5_NATIVE_FD_PINNED_QUEUE_READ=PASS_ANDROID35_FIXTURE
P5_NATIVE_DIALOG_SHOWN=PASS_ANDROID35_INSTRUMENTATION
P5_UNSUPPORTED_REPORT_DENIED=PASS_ANDROID35_INSTRUMENTATION
P5_LEGACY_ACTIVITY_USER_BUTTON_CONNECTED=NO
P5_APPROVED_ONE_SHOT_TRANSPORT_CONNECTED=NO
ALL_NODE_GENERIC_FS_NETWORK_EGRESS_BLOCKED=NO
APP_WEBVIEW_STORAGE_ISOLATION=NOT_VERIFIED
FIXED_CERTIFICATE_VERSIONCODE_139_APK=NOT_BUILT
ART_REAL_USER_DEVICE=NOT_VERIFIED
PHONE_V138_UNCHANGED=YES
```

**Release decision remains BLOCKED_HOST_INTEGRATION.** The next implementation is a real host Activity lifecycle and user-gesture hook to P5 UI, plus native and generic Node egress control. Source-only components and test-only instrumentation are not that hook.

## P12 previous versions reuse and real legacy buttons on Android35 (2026-10-29)

A search of the user's persistent Library located historic DSH releases, the v137 native decompilation/callgraph, v1.3.7 JS source, and older host patch evidence. The recovered `LogViewerActivity` methods identify the real native `logExport` / `logUpload` buttons. These recovered Java sources are **not an original Gradle project**.

New P12 Java adapter `host_candidate/p12_native/com/dsh/p12/P12LogViewerReviewEntry.java` is independent code that rebinds **both native original button click handlers** to P5 local-only structured review. It is guarded by exact Activity class, fixed native destination allowlist, strict 0700 private queue mode, P5 descriptor-pinned reader and fail-closed no-sender semantics. No raw log export is enabled. P10 remains in the original DEX and P11 remains the summary-only tool.

P12 Java source and pinned nine P5 sources Android javac+D8: **PASS**, https://github.com/u2584604327-a11y/dshe/actions/runs/40827286539.

**Real Android 35 ephemeral simulator test: PASS**, https://github.com/u2584604327-a11y/dshe/actions/runs/40827698165:
- Fully assembled experimental APK includes 70 compiled P5+P12 class definitions in `classes3.dex`.
- `P12_ORIGINAL_LOGVIEWER_LAUNCHED=PASS_ANDROID_FIXTURE`.
- `P12_EXISTING_EXPORT_UPLOAD_BUTTONS=BOTH_INTERCEPTED_TEST_CALL`.
- `P12_EMPTY_QUEUE_DEFAULT_DENY=NO_RAW_EXPORT_TRIGGERED`.
- `P5_NATIVE_UI_REAL_ACTIVITY=PASS_INSTRUMENTATION`.
- `P5_FD_PINNED_READER=PASS_ANDROID_FIXTURE`.
- Android install, offline ART package compile, MainActivity launch = PASS.
- Temporary test-signed APK, test-only instrumentation and signer deleted by runner; no production signing/phone install.

**Do not inflate this proof:** P12's original LogViewer click handler was installed by **test instrumentation**, not by the unmodified original app lifecycle. Real user's app will NOT invoke P12 automatically until a native lifecycle/manifest bridge is implemented. Approved one-shot sending is deliberately unconnected and same-UID Node generic filesystem/network bypass is still not blocked. No v139 release may be published.

```text
P12_REUSED_OLD_DECOMPILED_METHOD_MAPPING=YES
P12_NATIVE_JAVA_COMPILES=PASS
P12_REAL_ORIGINAL_LOGVIEWER_BUTTONS=PASS_TEST_ONLY_INSTRUMENTATION
P12_ORIGINAL_ACTIVITY_LIFECYCLE_HOOK_IN_PRODUCTION=NO
P12_NETWORK_SEND=DISABLED
P12_ANDROID35_EMULATOR=PASS_LIMITED
NODE_TOTAL_EGRESS_CLOSED=NO
ORIGINAL_CERT_VERSIONCODE_GT_138_APK=NOT_BUILT
```

See `host_candidate/P12_LIBRARY_RECOVERY_INTEGRATION_NOTES.md` for historical source provenance, exact constraints and next step.

## P13 AndroidX Startup production-style auto hook — Android 35 PASS (2026-10-29)

**Authoritative real Android 35 isolated test:** https://github.com/u2584604327-a11y/dshe/actions/runs/40830669436 — **SUCCESS**.

The previous P12 proof needed test instrumentation to manually call `P12LogViewerReviewEntry.attach()`. P13 eliminates that missing hookup in the actual fused **test candidate app** without rewriting old host DEX method references:

- Original v138 includes a nonexported `androidx.startup.InitializationProvider`, containing three existing startup `meta-data` entries. The exact preimage `AndroidManifest.xml` SHA256 is `fa9e134048fc416e267106600af7bdf28ca1f9dd46e4cf055f1e6a87b69d5987`.
- `host_candidate/p13_manifest_inject.py` appends a single `meta-data android:name="com.dsh.p12.P13NativeReviewInitializer" android:value="androidx.startup"` child under that **existing provider**, without adding a provider, changing permissions, exports, app package/UID or versionCode. It preserves all original attributes and sibling chunks while appending one UTF-16 string-pool entry.
- Exact resulting binary Manifest SHA256: `39a825e40aff02cef83944ef40de61e310a4c6912d3a352169637ee72a9a0b5f`, string pool count 95→96, bytes 10,144→10,328. Full test archive matches the pinned hash.
- `P13NativeReviewInitializer` implements the existing AndroidX Startup `Initializer`; it uses Android `Application.ActivityLifecycleCallbacks` to attach P12 after the real `LogViewerActivity` has resumed and its views exist. It accepts **no** Node, web, model or Intent-provided capabilities.
- The AndroidX interface class is a compile-time test-only stub under `p13_compile_stub`; class `androidx.startup.Initializer` is **not packaged** in the new DEX, avoiding conflict with original app classes. P5/P12/P13 classes compiled under Android SDK35 and D8 API26.
- Diagnostic sender remains unbound. A fixed `.invalid` destination is used **only** to support local preview validation; no real HTTPS upload is possible. Known P10 raw-ZIP builder paths and P11 AI raw-log mailbox routes stay default denied.

**Actual real-activity instrumentation, without manual attach:**

```text
P13_ANDROIDX_STARTUP_METADATA=PASS_REAL_APPLICATION
P13_LOGVIEWER_AUTOMATIC_HOOK=PASS_NO_MANUAL_ATTACH
P13_REAL_EXPORT_UPLOAD_BUTTONS=REBOUND_TO_LOCAL_REVIEW
P13_LEGACY_RAW_ZIP_SEND=P10_DEFAULT_DENY_PRESERVED
P13_APPROVED_NETWORK_SEND=NOT_CONNECTED
P13_GENERIC_NODE_SAME_UID_EGRESS=NOT_BLOCKED
P13_REAL_PHONE_UPGRADE=NOT_TESTED
INSTRUMENTATION_CODE=-1
```

Original app install, offline ART package compilation and MainActivity launch also succeeded. P5 direct UI and P12 test-only button instrumentation retained their previous PASS. No test APK or transient keystore was published; the runner destroyed them. User's existing installed DSH and data remain untouched.

### Honest gate distinctions

- **P13_AUTO_HOOK=PASS_ANDROID35_EPHEMERAL_LAB**: This is now a real manifest-driven integration *in the candidate APK*, not merely a manually wired test.
- **P13_USER_DATA_AND_SIGNATURE=UNVERIFIED**: The candidate still uses v138 versionCode and an unrelated disposable key; it is not a replacement install for the user's real v138.
- **P13_NATIVE_APPROVED_ONE_SHOT_SEND=NO**: UI is preview-only, default denied, no new network capability. A future authorized product implementation must bind a strictly exclusive native transport after revalidating approved bytes and destination.
- **P13_NODE_UID_ISOLATION=NO**: Same-UID general Node/file/shell/network tools can bypass the scoped P11 logs-tool policy; P13 does not solve that.
- **P13_BROWSER_UI_AND_STORAGE_PROFILE=NOT_VERIFIED**: Existing browser/device tools still require separate production path acceptance.

```text
RELEASE_V139=BLOCKED_SAFE_TRANSPORT_NODE_SANDBOX_FIXED_SIGNATURE_REAL_PHONE
P13_NATIVE_AUTOHOOK=PASS_ANDROID35
P13_APPROVED_SEND=NO
ALL_GENERIC_NODE_EGRESS=NOT_CLOSED
PRODUCTION_SIGNED_APK=NO
```

### Independent cold-process P13 regression (no manual attach before test)

The second real Android35 gate https://github.com/u2584604327-a11y/dshe/actions/runs/40831479000 completed with **SUCCESS** after changing the instrumentation order to first:
1. Install exact ephemeral lab APK and test APK.
2. Call `adb shell am force-stop com.dsh.android`, terminating the app process.
3. Run **P13AutoHookInstrumentation first**, with no prior P5/P12 tests in that process and **no call to `P12.attach()`**.
4. Start the original `com.dsh.android.LogViewerActivity`, confirm AndroidX manifest metadata and independently detect the two button content descriptions set by P12, then click them.
5. Only after P13 passes, execute the separately scoped P5 and P12 regression fixtures.

Verified cold-process evidence:
```text
P13_ANDROIDX_STARTUP_METADATA=PASS_REAL_APPLICATION
P13_LOGVIEWER_AUTOMATIC_HOOK=PASS_NO_MANUAL_ATTACH
P13_REAL_EXPORT_UPLOAD_BUTTONS=REBOUND_TO_LOCAL_REVIEW
P13_LEGACY_RAW_ZIP_SEND=P10_DEFAULT_DENY_PRESERVED
P13_APPROVED_NETWORK_SEND=NOT_CONNECTED
P13_GENERIC_NODE_SAME_UID_EGRESS=NOT_BLOCKED
INSTRUMENTATION_CODE=-1
```

Subsequent P5 review and P12 manual-attach tests also PASS, without weakening P13's already-verified early ordering. The P5 direct test's historical `LEGACY_HOST_BUTTON_WIRED=NO` is **a test-local label**, not an accurate description of the P13-integrated lab app: P13 separately proves the real manifest-driven hook. Fix misleading labels before shipping any standalone audit summary.

**Decision:** Lock `P13_COLD_BOOT_AUTOHOOK=PASS_ANDROID35_DISPOSABLE`. Do not extend this PASS to a user phone, original signing certificate, native approved one-shot network send, full Node UID isolation, browser profile separation or production APK. The run creates and deletes only disposable signed test artifacts, with no release.

## P14 Token UI, P15 isolated UID probe, P16 device-mode audit — verified 2026-10-29

1. P14 source/Node token 3-state regression PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40833692739. Browser asset SHA256 be8201f11c7a12478d0552efaf129becde6d104ef2da203c2433b3dfc397a69f. Official provider nonzero values preserved; otherwise clearly estimated or unavailable, not fabricated exact usage.
2. P14 SHA-pinned browser resource fused into actual P13/P5 disposable Android 35 APK, ART/install/main startup/P13 original host autohook regression PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40833854898. The actual on-device Token popup with live LAN provider remains UNVERIFIED. No server-side provider usage invented.
3. P15 original signed v138 APK structural inspection PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40834057507. 2 manifest Service entries, 0 isolatedProcess services, Node and Shell tools shipped. Strict main DSH Node isolation is NOT VERIFIED.
4. P15 separate minimal Android isolatedProcess service and IPC test on Android 35 emulator PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40834677353. Distinct OS UID verified; service denied access to host-owned private synthetic file; manifest isolated flag present; no permissions requested. This proves an independently built isolated service can work on Android35. **Original DSH Node/Browser not migrated to it**, so do not label DSH as strict VM.
5. P16 real P6 browser device profile source consistency PASS after correcting overly strict integer-only CSS viewport test: https://github.com/u2584604327-a11y/dshe/actions/runs/40834952248. Source has declared User-Agent/viewport/DPR and auto-native restore; actual physical device/OS, WebView engine, TLS/IP, attestation and per-profile isolated storage were not changed or validated.

```text
P14_TOKEN_MODEL_DISPLAY_3_STATE=PASS_SOURCE
P14_ANDROID_CANDIDATE_ASSET_FUSED=PASS_EMULATOR
P14_LIVE_LAN_API_ACTUAL_USAGE=NOT_VERIFIED
P15_ORIGINAL_DSH_SERVICES_ISOLATED=0
P15_REAL_ISOLATED_SERVICE_UID_PROTOTYPE=PASS_ANDROID35
P15_REAL_ISOLATED_SERVICE_PRIVATE_FILE_DENY=PASS_ANDROID35
P15_DSH_NODE_ACTUALLY_MIGRATED_TO_ISOLATED_UID=NO
P15_ALL_GENERAL_NODE_FILE_SHELL_NETWORK_EGRESS_CLOSED=NO
P16_DEVICE_PROFILE_SCHEMA=PASS_SOURCE
P16_SITE_VISIBLE_DEVICE_CONSISTENCY=NOT_VERIFIED
P16_REAL_IOS_OR_WINDOWS_DEVICE_IDENTITY=NOT_POSSIBLE_FROM_ANDROID_WEBVIEW
P13_ORIGINAL_LOGVIEWER_COLD_BOOT_AUTOHOOK=PASS_ANDROID35
PRODUCTION_FIXED_SIGNED_V139=NOT_BUILT
REAL_USER_DEVICE=UNCHANGED
FINAL_RELEASE_GATE=BLOCKED_STRICT_ISOLATION_AND_APPROVED_SEND_AND_SIGNATURE
```

Full scope and failure distinctions are in host_candidate/P14_P16_SECURITY_AND_DEVICE_MODE_STATUS.md. Build/test APKs were temporarily signed and deleted in isolated Actions; no original app keys, account tokens, private APKs or diagnostic data were released.

## P17 authenticated Android IPC and P18 privileged tool deny (2026-10-29)

- Reviewed Android official `isolatedProcess`, Shelter Work Profile, Google gVisor's Gofer architecture and Android AVF/Microdroid system API restrictions; see [P17 architecture](host_candidate/P17_SANDBOX_ARCHITECTURE_AND_MIGRATION_GATES.md). These architectures are **not equivalent**. AVF is not unrestricted for a normal APK and Android WebView UA spoofing is not a real iOS/Windows VM.
- P17 native one-shot `METADATA_COUNT` capability ledger uses 256-bit cryptographic tokens, monotonic expiry <=30 seconds, Android UID binding, single consumption, revoke-all on service death, deny replay, reject arbitrary filesystem and network scopes. Wrong UID or scope burns the grant.
- P17 Java unit and real Android 35 **Messenger.sendingUid** authenticated UI gesture test: https://github.com/u2584604327-a11y/dshe/actions/runs/40836348358 **SUCCESS**, both jobs. A disposable distinct isolated UID worker is actually involved in the Binder IPC, the test uses a real simulated touch on the test-only approval button, and pre-approval, one shot, replay and raw file denial paths were asserted. This is a standalone test APK, NOT the original DSH Node engine.
- Inspecting exact SHA-pinned signed v138 assets surfaced **critical model-facing privilege escape**: `shell` registered a path to UID 2000 through adbd; `root` registered UID 0 through `su` when available. Original plugin comments explicitly admit sandbox bypass for these paths.
- P18 source-only `assets/shell-tool.zip` and `assets/root-tool.zip` JS patches disable tool registration before any runner/ADB/su call and add direct-execute denial. P18 original nested ZIP preimages and untouched package metadata checked; Node runtime registration test https://github.com/u2584604327-a11y/dshe/actions/runs/40836893499 **SUCCESS**. Patched SHA256: shell `51dac0e5c82a38e03318535b6d0d1ac9fe52d2b020ba508efc82af0947df1187`, root `8f54d9871357a79df0acb997169becc03282eb64f3e191ff0cdba4bf7492b7f1`.
- P18 resources integrated into experimental P13/P14 Android fusion. Actual Android35 ART/startup and native UI regression is https://github.com/u2584604327-a11y/dshe/actions/runs/40837022330. **Do not claim P18 Android PASS before that run completes successfully.**
- **Explicit feature tradeoff:** original AI `shell` and `root` model tools are disabled in the experimental candidate until native broker capability integration. This is intentional temporary feature reduction in strict mode; user must be told. Original installed v138 is unchanged.
- **Critical unresolved bypass:** ordinary app-UID `bash`, Node `child_process` and other same-UID filesystem/network/localhost/ADB helpers remain; P18 alone is not a full VM/Node sandbox. No real DSH Node/payload migration to isolated UID, WebView per-profile storage isolation, user data upgrade or original-certificate v139 release.

```text
P17_AUTHENTICATED_BINDER_IPC_AND_UI_GESTURE=PASS_ANDROID35_STANDALONE
P17_ONE_SHOT_REPLAY_REVOCATION_SCOPE=PASS
P17_ORIGINAL_DSH_NODE_ISOLATED_UID=NOT_IMPLEMENTED
P18_UID2000_SHELL_PLUGIN=DISABLED_CANDIDATE
P18_UID0_ROOT_PLUGIN=DISABLED_CANDIDATE
P18_NODE_TOOL_TEST=PASS
P18_COMBINED_ANDROID35_ART_UI=CHECK_REAL_ACTIONS
P18_GENERAL_BASH_CHILD_PROCESS_FILES_NETWORK=NOT_CLOSED
P18_ORDINARY_USER_ATTACHMENTS=SOURCE_UNCHANGED_RUNTIME_NOT_VERIFIED
FIXED_CERTIFICATE_SIGNED_V139_APK=NOT_BUILT
PRODUCTION_RELEASE=BLOCKED_STRICT_ISOLATION_NATIVE_SEND_SIGNING
```

### P18 combined Android 35 final result

Private CI https://github.com/u2584604327-a11y/dshe/actions/runs/40837022330 completed **SUCCESS** (2026-10-29). Exact two modified plugin archives are present in ephemeral P1–P14 candidate; Android 35 installation, ART package compilation, MainActivity startup, P13 cold-process LogViewer automatic hook, P5 safe preview, P12 regression all passed. The trusted P17 Binder one-shot broker **also** passed independently at https://github.com/u2584604327-a11y/dshe/actions/runs/40836348358; it is NOT yet hosted by DSH or wired to Node.

```text
P17_ISOLATED_WORKER_AND_AUTHENTICATED_MESSENGER_UID=PASS_STANDALONE
P17_EXPLICIT_UI_ONESHOT_GRANT_AND_REPLAY_DENIAL=PASS_STANDALONE
P18_SOURCE_NODE_TOOL_SHELL_ROOT_REGISTRATION_DENIED=PASS
P18_COMBINED_ANDROID35_APK_ART_STARTUP=PASS
P18_P13_AUTOMATIC_HOST_UI_REGRESSION=PASS
P18_ACTUAL_AI_SESSION_TOOL_LIST_VERIFIED=NOT_RUN
P18_NODE_BUILTIN_BASH_CHILD_PROCESS_GENERIC_FS_NETWORK_ISOLATED=NO
REAL_NODE_MIGRATED_TO_ISOLATED_UID=NO
FORMAL_V139_RELEASE=BLOCKED
```

These scope distinctions are mandatory; source-only tool registration deny plus APK startup is not a whole-app sandbox. Full details at `host_candidate/P17_SANDBOX_ARCHITECTURE_AND_MIGRATION_GATES.md` and `host_candidate/P18_PRIVILEGED_TOOL_FAILCLOSE_STATUS.md`.
