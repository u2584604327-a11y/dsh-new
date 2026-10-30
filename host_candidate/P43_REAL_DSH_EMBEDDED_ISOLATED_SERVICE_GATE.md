# P43 — real original DSH APK + embedded isolated Android Service (private transient experiment)

P42 confirmed original DSH v138 has a custom Application class, two existing services (no isolatedProcess service), targetSdk28, INTERNET and cleartext permitted, Node startup needs builder environment, directory and merged stderr. P41 established original launcher and P40 trampoline boot parity on an emulator.

P43 injects a **nonexported isolatedProcess Service** and a **test-only adb-started Activity** into a private exact-source original DSH APK. It also adds these two tiny Java classes exclusively to a new classes3.dex, preserving original classes2.dex, assets and native libraries. P40 remains a pass-through and Node still executes in the host when actually started. The test Activity requests no capabilities; its only operation is a host-generated random 256-bit session echoed over Android Messenger while the host validates real framework Message.sendingUid and Process.isIsolatedUid.

The custom original Application onCreate runs in the separate isolated process unless exempted. Test may fail here: report the failure and do not claim isolation success. This test is designed to prove actual service creation inside original app before attempting original Node startup integration.

The test APK retains the original package name `com.dsh.android` but uses an **incompatible one-day disposable signer** and contains an exported diagnostic Activity. It is only for fresh GitHub Actions emulator, must NEVER be given to the owner or deployed as v139. Original release key, owner device, tokens and data are untouched.

**No original production process isolation**, no filesystem/runtime broker, no main EngineManager P37 handoff, no production chat/browser/files parity, no ARM64 original Node in x86 emulator. These remain hard release gates.

P43_ORIGINAL_PKG_NONEXPORTED_ISOLATED_SERVICE=UNDER_TEST
P43_REAL_ORIGINAL_NODE_ENGINE_WIRING=NO
P43_OWNER_DEVICE_SIGNED_V139=BLOCKED
