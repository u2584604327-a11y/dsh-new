# P45 original DSH host-to-isolated-worker read-only file descriptor bridge

**Project focus:** continue P43/P44 real original Android APK integration. This is a concrete prerequisite for production Node's brokered scripts, not another virtual device UI. No root is used.

## Existing evidence
- P31: isolated Node worker + child UID observed on owner ARM64 Android16; private host canary returned ENOENT (nonvisibility, not ACL proof). TCP to loopback and TEST-NET denied EACCES.
- P38: exact original signed-v138 ARM64 Node synthetic stdout/stderr and Process proxy exit observed PASS on owner's separate APK.
- P39: three original ProcessBuilder.start sites; only EngineManager main coroutine is in scope.
- P40/P41: original DSH main coroutine one-call pass-through trampoline rebuilt; emulator MainActivity launch PASS.
- P43: original DSH com.dsh.android added a truly isolated, nonexported Android Service, host verified isolated sender UID and one-shot Messenger handshake in emulator.
- P44: original DSH host passed a bounded synthetic virtual device descriptor over that authenticated Binder channel and verified its fingerprint, NOT a real system VM.

## P45 specific behaviour and invariants
- The trusted original DSH test Activity creates EXACTLY one small synthetic test file inside its own app-private emulator cache; writes deterministic public test bytes.
- It opens that file O_RDONLY (Android ParcelFileDescriptor.MODE_READ_ONLY), unlinks the name and sends only the already-open descriptor plus 64-byte maximum over a single authenticated Binder Messenger request. **Neither path nor actual content is sent as Binder strings.**
- The isolated nonexported Service validates real Message.sendingUid and a host-generated 256-bit session, parses the strict P44 virtual profile, then reads from this one descriptor with a 64-byte hard cap.
- It accepts only exact public synthetic test bytes and returns SHA256 and length. The host independently compares SHA256, size and explicit no-path/no-root flags before logging PASS.
- This explicitly does not grant the worker access to host-private directories, arbitrary files, network, clipboard, camera or system identity; no file paths are supplied to the worker. It does not establish general Android filesystem ACL behaviour.
- The Android emulator end-to-end must PASS for original DSH MainActivity, Binder isolated UID, P44 profile and P45 descriptor contract. The exact signed v138 original assets, native libraries, secondary DEX, Manifest permissions and SDK must pass P43 source integrity and package signing gates.
- The CI-only test APK uses a separate one-day throwaway key and exported probe Activity, is destroyed after test, and MUST NOT be used as the owner's signed DSH app.

## Safe reference context
Temporary-root projects such as GhostLock/DirtyFrag use firmware-and-kernel-specific privilege escalation to UID 0 for one boot. This is an inappropriate dependency for a normal DSH app and risky for device security; no exploits, root daemons, kernel modules, system partition changes, or reboots are authorized. Android platform isolatedProcess and Binder resource leasing are used instead. PRoot root-mapping is not kernel virtualization or root. Shizuku's adb-shell mode is not equivalent to UID 0.

## Remaining blocker for a real release
This is a one-off synthetic payload. Production runtime still requires a **separate** user-approved, content-addressed broker for bounded script/resource packages; revocable/expiring handles, no time-of-check/time-of-use directory races, per-packet consent for diagnostics, Node command/environment compatibility, stdin/stdout/stop/restart, background lifecycle, and the original EngineManager P37 Process proxy actual handoff. Browser/WebView, chat, files/photos and the fixed signing key have not been production tested.

P45_REAL_ORIGINAL_APK_HOST_TO_ISOLATED_FD=UNDER_TEST
P45_PRODUCTION_NODE_RUNTIME_FILES=BLOCKED
P45_ANDROID_OS_VIRTUAL_MACHINE=NO
P45_ORIGINAL_DSH_V139_SIGNED_APK=BLOCKED
