# P47: Exact original EngineManager main-start fail-closed integration gate

## Motivation
P46 **PASS** proved that real original `com.dsh.android` APK can transfer two content-addressed, synthetic and never-executed O_RDONLY resources over an authenticated isolated Binder Service inside a disposable Android35 emulator. It did NOT migrate the production Node engine. P40's one-call `P40ProcessBridge.start(ProcessBuilder)` still called the host `ProcessBuilder.start()`, which would be an unsafe silent fallback if used as an isolation implementation.

## This PR
In a **throwaway exact-original v138 app copy only**, condition `P47_NO_HOST_FALLBACK=1` rewrites only P40 bridge invocation from original `ProcessBuilder.start()` to `P47LaunchGate.startOrDeny(ProcessBuilder)`. The latter currently always raises an explicit IOException because no production isolated supervisor exists. It never executes a shell, child process, executable script, or writes user data. No secret command/env values are output; only bounded counts may be inspected. The actual original `EngineManager$start$2` DEX callsite remains the exact P40 static trampoline, while `EngineManager.probeBoot` and `runDumpConfig` preserve original ProcessBuilder calls.

Validation:
- JVM canary invokes a synthetic ProcessBuilder and verifies no file is created.
- Actual signed-original SHA256 (P35), main DEX bridge rewrite, **reassembled/signed disposable APK classes.dex**, and a distinct gate class in `classes3.dex` are inspected; exact method calls and absence of host spawn verified.
- Fresh Android 35 emulator opens original `MainActivity`, invokes **the actual main DEX bridge reflectively** through the test-only Activity, verifies expected denial and no spawned canary, then verifies P43–P46 Binder/UID/profile/FD tests continue to pass.
- Strict unchanged original assets/libs/classes2.dex/Manifest permissions, ephemeral one-day signer and cleanup. Original user device or data not modified. No artifact released or PR merged.

## Deliberate consequence and hard boundary
**This candidate is not usable DSH**: attempting to start production Node would now be rejected because no isolated supervisor exists. This fail-closed behavior is a narrow security test, not a release candidate. P47 does not establish that the real EngineManager coroutine was exercised by the test Activity, nor that every alternative launch path is disabled; P39 found two independent ProcessBuilder.start uses (probeBoot and runDumpConfig) which are kept unchanged. If those launch executable code in production, that needs separate authorization and auditing. It also does not prove file system ACL denial, actual Node script transfer, shell availability in Worker, direct TCP, stdin, READY/latch, start/stop/restart, users' chat/browser/attachments or signing parity.

### Next implementation
Only a real original-package host supervisor connected to a correctly authenticated isolated Worker returning a P37 Process facade and a minimal verified production script/resource bundle may replace the deny branch. No silent host ProcessBuilder fallback, root exploits, global permissions or broad host-private file access.

P47_ORIGINAL_MAIN_ENGINE_HOST_FALLBACK=DENIED_IN_TEST
P47_REAL_PRODUCTION_NODE_READY=NO
P47_USER_FACING_V139_APK=BLOCKED
