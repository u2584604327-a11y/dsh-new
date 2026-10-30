# DSH P17 — Virtualization and restricted-capability broker design

Date 2026-10-29. This source-only prototype is **NOT** an installable DSH v139 update and is **NOT** a virtual Android or iOS device.

## External architecture comparison

- Android `android:isolatedProcess=true`: Android OS assigns a separate isolated UID with no app privileges. Good for untrusted workers and verified by disposable P15 Android 35 test. Official: https://developer.android.com/guide/topics/manifest/service-element
- Google gVisor: a userspace application kernel with a controlled filesystem gofer; valuable architectural inspiration for separating untrusted compute and trusted resource mediation. It is not a drop-in Android APK library. Official: https://gvisor.dev/docs/
- Android Work Profile and Shelter: isolates whole app instances and data under managed user/profile boundaries; user setup, device policy, limits and additional UX requirements differ from an in-app worker. See https://f-droid.org/en/packages/net.typeblog.shelter/
- Android AVF/Microdroid: genuine guest OS, but its Android framework APIs depend on restricted `MANAGE_VIRTUAL_MACHINE` / system API access on documented versions. Do not assume a third-party installable DSH app can freely launch hardware-protected guests. Source: https://android.googlesource.com/platform/packages/modules/Virtualization/+/HEAD/libs/framework-virtualization/README.md
- Android WebView `setDataDirectorySuffix`: storage partition for different processes, **not** a new UID nor a new rendering engine. Source: https://developer.android.com/reference/android/webkit/WebView#setDataDirectorySuffix(java.lang.String)

## New isolated-workload proof components

- `host_candidate/p17_capability/src/com/dsh/p17/P17CapabilityGate.java`: strictly scoped native-only grant ledger.
  - 256-bit unpredictable random grant identifier, 30-second maximum lifetime.
  - Uses monotonic elapsed time; 16 outstanding grants maximum.
  - Grants are bound to a verified isolated UID, not a user-agent, device preset or untrusted parameter.
  - Exactly one permitted action: `METADATA_COUNT`, a synthetic bounded counter; no raw files, URLs, generic network, shell, camera, clipboard, device control, diagnostics or credentials.
  - Grants are burned on both successful and incorrect-scope/UID requests; replay, revoke, expiry and process death deny.
  - The ledger is stored solely in the trusted host process. The isolated worker cannot mint its own grant.
- `host_candidate/p17_capability/android/`: separate **disposable zero-permission test APK**, containing a real isolated worker and a trusted Android Activity.
  - IPC via Android Messenger. Host verifies framework-authenticated `Message.sendingUid` and `Process.isIsolatedUid` on API 34+, never trusts a claimed UID in Bundle or JSON.
  - A synthetic test-only screen touch is required before minting one scope-limited grant. Preapproval request, one use, replay and raw-file scope are tested.
  - No actual input file, user secrets, network, shell or diagnostics are exposed to the worker.
  - A fixed grant is never auto-approved on app launch.

## Test evidence

- P15 standalone isolated UID/private canary denial: https://github.com/u2584604327-a11y/dshe/actions/runs/40834677353 **PASS**.
- P17 Java unit tests: https://github.com/u2584604327-a11y/dshe/actions/runs/40835974704, check individual job status. **Java unit job passed**, after correcting grant burn on a wrong scope. Keep the earlier failed security regression as evidence.
- P17 actual Android35 Messenger sender UID and touch test is in the same run, and MUST be **completed successfully** before reporting P17_ANDROID_BINDER=PASS. Do not infer emulator PASS from build/unit results.

## Staged migration into DSH

1. Inventory the exact **Node native runtime, shell, browser, plugin, child-process and file/network** invocation graph in the SHA-pinned v138 APK. Enumerate Android service entry and JNI references; do not silently rename existing processes.
2. Move real model-facing untrusted execution into isolated UID. It cannot simply open original internal Node binary, data directory or signing/API-key paths, due to different UID. Choose an explicit immutable, read-only payload source and offline start sequence, with bounded CPU/memory and no file/network permissions. Preserve functional original services until safe replace-in-place coverage is proven.
3. Add a genuinely trusted same-UID host Binder service which receives IPC from the actual isolated worker, validates **kernel-reported calling UID and active worker instance**, time-limited grant, request schema, per-scope rate and size, current UI user authorization, and revocation. Deny by default.
4. Trusted host should keep user API keys; any network requests go through explicit destination/auth policy. Do not simply proxy arbitrary URLs/headers/paths from the worker; do not expose unrestricted loopback HTTP.
5. Native file selection should use Android picker-granted single files, pinned FD and immutable content revalidation, not arbitrary path traversal. Keep explicit ordinary image/file sends working while P10/P11 raw diagnostic gates remain closed.
6. Account/device metadata and JS/browser device profile must be clearly marked **simulated** unless measured on an approved test website. Do not claim fake platform values modify real GPU/TLS/IP, device attestation or Android UID.
7. In a **new** disposable integrated DSH APK, verify UID split, `app/files` and user credentials inaccessible from real Node, all shell/network bypass blocked, explicit grant/revoke, service crash/restart and WebView storage isolation. Then original Activity, browser, conversations, API streaming, attachments, privacy and data persistence regression.
8. Only after full functional and isolation gates pass may original-certificate `versionCode > 138` signing and data-preserving update be considered. Original v70 signer is different from v138 test signer.

## Hard blockers

```text
P15_ANDROID_ISOLATED_UID_AND_PRIVATE_CANARY=PASS_STANDALONE_ONLY
P17_ONE_SHOT_NATIVE_GATE=PASS_JAVA_UNIT
P17_ANDROID_BINDER_AND_UI_TOUCH=CHECK_GITHUB_CI
P17_DSH_ACTUAL_NODE_MIGRATED=NO
P17_DSH_OS_VM_OR_MICRODROID=NO
P17_VIRTUAL_IPHONE_WINDOWS_HARDWARE=NO
P17_PER_ORIGIN_WEBVIEW_PROFILE_ISOLATION=NOT_VERIFIED
P17_ONE_SHOT_DIAGNOSTIC_TRANSPORT=NOT_CONNECTED
P17_ORIGINAL_FIXED_SIGNED_V139_APK=NOT_BUILT
P17_REAL_PHONE_DATA_RETENTION=NOT_TESTED
RELEASE=BLOCKED
```
