# P47 — Actual original DSH EngineManager bridge fails closed without isolated Node supervisor

P46 private CI verified (run 40974074838): real original `com.dsh.android` disposable Android35 emulator APK, nonexported isolated Binder, host-selected simulated profile, P45 one O_RDONLY FD, P46 two hash-bound synthetic FDs. These are NOT production Node scripts.

## P47 source change in ORIGINAL main DEX
1. Read exact signed v138 original only in private CI; verify hash and size.
2. Apply proven P40 patch of only `EngineManager$start$2.invokeSuspend` ProcessBuilder.start to `P40ProcessBridge.start`.
3. **Only for P47 test candidate**, alter `P40ProcessBridge.start(ProcessBuilder): Process` so it invokes `P47LaunchGate.startOrDeny(ProcessBuilder): Process` in third DEX. It MUST NOT call `ProcessBuilder.start()`, shell, reflection or any host fallback. The Java P47 launch method currently throws a checked IOException with an explicit supervisor-unavailable error; no supervisor is yet implemented.
4. Verify actual rebuilt DEX: primary coroutine calls P40 once, P40 calls P47 once, P47 has no direct ProcessBuilder.start, and the original unrelated EngineManager.probeBoot and runDumpConfig call sites remain original.
5. The original DSH test-only in-package probe Activity invokes the exact P40 bridge reflectively with a *synthetic* ProcessBuilder that would create a canary if incorrectly launched. It must throw the expected checked exception with the canary absent. Then verify P43/P44/P45/P46 actual isolated Binder resource tests. Static Java tests separately reject empty and overlong argv and verify no host process.
6. Preserve original MainActivity startup, original assets/libs/classes2 DEX/Manifest/permissions, and disposable Android35 CI-only signing. The test is deliberately nonfunctional for production Node: it denies the main launch. Never install it over the owner DSH app.

## Security boundary and release
This is a necessary no-fallback boundary, NOT implementation of an isolated Node launcher, not a VM, not production file broker. A Future real DSH must capture approved builder command, cwd, sanitized environment, original bootstrap and dependency graph, enforce no arbitrary shell or env secrets, bind an authenticated isolated Worker, return P37RemoteProcess, propagate true readiness/EOF/stop, and provide user-approved host-side network APIs; P31 showed isolated Node network EACCES. The P47 original Activity test checks bridge denial, **not** full original coroutine behavior or user-visible chat/browser parity.

The original DSH MainActivity may or may not tolerate a denied engine start; any crash is an honest P47 regression gate, not permission to fallback. GitHub emulator harness uses adb-root only for its firewall, not in DSH app. No user data, original fixed signing key, public Release, or installed DSH APK is touched.

P47_MAIN_DEX_NO_HOST_FALLBACK=UNDER_TEST
P47_ORIGINAL_ENGINE_PRODUCTION_NODE_ISOLATED=NO
P47_V139_FINAL_APK=BLOCKED
