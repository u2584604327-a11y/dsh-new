# P49 — place exact SHA-pinned ORIGINAL ARM64 Node in original DSH APK (OFFLINE ONLY)

This work continues P48 (original package confirmed Android35 in-package isolated child + actual P37 Process proxy and P47 no-host-fallback). It does not replace the existing DSH code or claim a finished virtual machine.

## What was implemented
- Only in private PR-scoped GitHub CI, obtain the exact original signed v138 DSH APK, check 147341486 byte size and known full SHA256.
- Reuse P21 source-pinned extraction, P25 dependency-graph aliasing and P28 immutable lock creation. This extracts **the actual original ARM64 Node ELF** (SHA256 a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6) plus the original ten shared-library ELF files, no substitutions/recompilation.
- Append only the eleven approved ELF files to lib/arm64-v8a/ and one SHA lock to assets/p49-original-node-lock.json in the *actual original package* previously rebuilt with P47 and P48 native host/isolated Service scaffolding.
- APK zipalign -P 16; signed with a **disposable incompatible one-day certificate** solely to verify installer v2/v3 signatures.
- Verify each ELF ZIP entry is STORED (uncompressed), exactly 16KiB aligned and SHA-matched to original payload/lock; confirm original APK assets/native library bytes, permissions and classes2 DEX remain untouched, extra asset/native members exactly allowlisted. Retain P47 no-host-fallback target DEX.
- Absolutely no output ZIP/APK/native library files are uploaded or released; cleanup all temporary copies.

## Important release blockers
This is an OFFLINE static build. It is **not executed** on an ARM64 device here; an Android35 x86_64 emulator cannot validate a pure ARM64 native library image, and adding arm64-only libs can make that emulator refuse APK installation. No claim of ARM64 runtime support is made here.
- Production exact command/environment/cwd and script resource bundle for original Node require independent read-only inventory and explicit broker construction. The 11 ELF files alone are NOT an actual working engine.
- Android app's original native library extraction and loader namespace/path behaviour not proved for the new package arrangement. The old native app DSH child launch is intentionally blocked by P47, and isolated worker does not yet invoke this Node executable.
- The original Node ELF was built with Termux runpath; P25 had explicit libsqlite3 no-SONAME exception. Cannot claim runtime compatibility based on SHA alone.
- No actual original EngineManager Kotlin coroutine -> P37 proxy handoff; no READY/latch integration, network port/loopback, Shizuku, stop/restart, real chats, WebView, photos, or files parity.
- Do not use test-only exported probe Activity or throwaway certificate on the owner's actual existing DSH installation; fixed signing and data migration remain unverified.

P49_REAL_ORIGINAL_DSH_APK_CONTAINS_EXACT_ARM64_NODE=UNDER_TEST_STATIC
P49_REAL_ORIGINAL_ARM64_NODE_EXECUTED=NO
P49_ORIGINAL_ENGINE_MANAGER_ISOLATED=NO
P49_PRODUCTION_FIXED_SIGNED_V139_APK=BLOCKED
