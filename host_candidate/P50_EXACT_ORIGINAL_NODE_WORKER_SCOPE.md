# P50 — exact original ARM64 Node launch code inside original DSH isolated Worker

## What this actually delivers
P48's Android35 emulator verified an original com.dsh.android APK with non-exported isolatedProcess Service launching a real fixed /system/bin/id -u child whose UID matched the kernel/framework-derived Binder UID, with genuine P37 Java Process stdout/stderr/EOF/waitFor/exit. P49 offline packaging verified original v138 Node ELF SHA256 a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6 and all ten original dependency ELF copied into an experimental original APK without altering original assets/libs/secondary DEX.

P50 combines those same primitives into the original application's actual Service: P50OriginalNodeFixedChild is compiled into the additional classes3.dex. It can run only on real Android 34+ with arm64-v8a, as an isolated UID. It checks non-grant of INTERNET in that process, resolves all original ELF only through the application's installed nativeLibraryDir, canonical-parent controls and SHA256 of each of 11 ELF (plus P49 exact original SHA lock), and constructs a totally fixed environment and fixed original Node --no-warnings --eval synthetic UID/BOOT/READY stdout and fixed stderr test. It never accepts a caller executable, shell command, arbitrary script, user file, directory, network URL, token or startup environment. It streams bounded frames over the existing authenticated Binder session to the P37 Process proxy; proxy checks framework sendingUid, sequence, session, exact UID witness / READY, stderr, exit and EOF. Wrong type, hash, ABI, API, path, permissions, framing, timeout or Binder failure is terminal and never falls back to main-host ProcessBuilder.

The trusted original test-only P43 ProbeActivity automatically chooses P50 only if running ARM64 and the P49 node lock actually exists, otherwise chooses P48 fixed system id witness. The P47 original EngineManager primary bridge still deliberately refuses all host launches, so this is not production EngineManager integration.

## Verification: two distinct CI jobs, neither claiming ARM64 runtime PASS
(1) Private P50 staging: exact v138 147341486-byte source SHA pin, P21/P25/P28/P49 exact original ELF and 16KiB native ZIP alignment, original assets/libs/classes2 preserved, P50 Android class compiled into actual original classes3.dex, ephemeral signer and no binary uploads.
(2) Private Android35 x86_64 emulator: compiled original DSH package **without ARM64 libraries**, verifies original MainActivity, P43–P46 Binder/UID/resource gates, P47 main DEX no fallback, P48 actual isolated system child/P37 proxy; and requires an explicit P50 skip signal so no false claim of Node ARM64 run on x86_64. The original final ARM64-stage APK cannot safely be tested in this x86 emulator by pretending its ELF is x86.

## Release BLOCKERS
- Still NO real original-package ARM64 runtime proof (requires suitably isolated ARM64 device with a non-overwriting test installation strategy; cannot install same-package test cert over existing signed DSH).
- Even if P50 fixed Node synthetic test passes on ARM64, it is NOT DSH production startup. Actual original EngineManager Kotlin coroutine does not yet receive this proxy, and original JS boot scripts, working directory, native library extraction, networking and protocol routing, READY socket and restart semantics are still unknown.
- Only a fixed synthetic test script is authorized. No root/kernel exploit or Shizuku. No general arbitrary tool or filesystem grants, no local permissions bypass, no device fingerprint spoofing, no full Android VM. Test-only exported P43 Activity must be removed from any owner release.
- No original real chat, browser, photo/file flows or protocol compatibility acceptance, and no fixed-signature proof. The ephemeral cert cannot update the owner's existing original DSH app.

P50_EXACT_ORIGINAL_NODE_WORKER_CODE_IN_ORIGINAL_APK=UNDER_CI
P50_REAL_ARM64_ORIGINAL_APP_NODE_RUNTIME=NOT_PROVEN
P50_PRODUCTION_ENGINEMANAGER_P37_PROXY=NOT_WIRED
P50_HOST_FALLBACK=DENIED_BY_P47
P50_OWNER_ORIGINAL_APP_AND_DATA=UNCHANGED
P50_FIXED_SIGNED_V139_APK=BLOCKED
