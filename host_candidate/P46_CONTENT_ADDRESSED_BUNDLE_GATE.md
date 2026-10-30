# P46 — Two-part, content-addressed synthetic runtime resource bundle in original DSH APK

## Exact source and established gates
- Baseline private signed v138 APK SHA-256 pinned from P35, size 147341486.
- P38 separate Android16 ARM64 exact original Node: stdout/stderr/exit synthetic program PASS, not production EngineManager.
- P39 exact DEX: three ProcessBuilder.start callsites, only EngineManager$start$2 main startup in scope.
- P40/P41: one-call pass-through trampoline and Android35 original DSH MainActivity launch PASS.
- P43: original com.dsh.android embedded nonexported isolated Service and framework UID Messenger verified on Android35 emulator.
- P44: bounded simulated profile in original Android Binder, NOT an Android system virtual machine.
- P45: one synthetic private O_RDONLY FD opened by trusted original host and passed without path; Android35 real Binder test PASS.

## P46 concrete delta
- New pure-Java `P46ResourceBundle`: canonical protocol version p46-1, **exactly two** allowlisted fixture labels in fixed order, maximum 4096 bytes per FD and 8192 bytes total, strict lowercase 64-hex SHA-256 and canonical decimal sizes. No directories or paths are sent over IPC as grant targets; the fixture *labels* are inert metadata only.
- The host opens **two** synthetic, deterministic and public test resources from its fresh emulator private cache with `MODE_READ_ONLY`, unlinks each filename before Binder send, includes only the two ParcelFileDescriptors and the bounded content manifest in an existing one-shot authenticated Messenger request.
- Worker validates framework sender UID, random 256-bit session, P44 profile, P45 one-off resource, manifest structure, a *frozen expected fixture manifest fingerprint*, exact byte sizes and SHA-256 for both FDs. On failure, no successful reply. On success, it reports a fingerprint verified independently by host.
- Static Java8 tests cover malformed manifest version, count, path traversal label, reordered names, leading-zero, negative, overflow, too-large, nul/newline injection, short/long/tampered body and null inputs.
- Actual original DSH APK rebuilt into `classes3.dex`, preserving original assets/native libs/classes2.dex and original permission declarations; disposable cert; on Android35 emulator confirm MainActivity, original isolated UID handshake, P44 and P45, then P46 two-FD results. No APK, source binaries, original user data, logs or disposable keys uploaded after CI.

## Explicit risk limits
- These are **never-executed, synthetic** fixtures (one inert JavaScript comment, one inert JSON document). This is not executing the production DSH Node script and does not prove Node package compatibility, multi-file Node require resolution, dynamic imports, native addons, stdin or RPC protocol parity.
- No real user files or secrets. No UI permission grant for arbitrary files. The *real* production package broker requires separately engineered time-bounded user-approved descriptors, content-addressed immutable snapshots, per-operation revocation, retries, stop propagation, EOF, and capability separation. The fixture permits only two names: no arbitrary manifests.
- No temporary-root exploit, Shizuku or Linux root **in the DSH app**. The GitHub emulator harness invokes `adb root` only to apply per-UID network-denial firewall rules. This test does not prove formal filesystem ACL denial; merely absence of passed paths.
- The Android emulator is x86_64 API35, not the owner's ARM64 API36 real phone. The compiled app contains an **exported diagnostic Activity** and a one-day throwaway signing key: never install it on owner's phone or label as v139.
- This protocol is a prerequisite, not a P37 Process override for original EngineManager. It cannot be marked production-ready until real process startup/READY/shutdown, chat/browser/photos/files, diagnostics per-packet consent and fixed signature are all proved.

P46_ORIGINAL_DSH_TWO_FD_BUNDLE_ANDROID=UNDER_TEST
P46_ACTUAL_ORIGINAL_NODE_ENGINE_EXECUTION=NO
P46_ARBITRARY_USER_FILE_GRANTS=NO
P46_REAL_ANDROID_OS_VM=NO
P46_SIGNED_PRODUCTION_V139_APK=BLOCKED
