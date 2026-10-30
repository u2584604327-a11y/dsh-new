# P55 — Startup candidate and native addon import dependency clues (private, read-only)

## Input
P54 verified exact signed-original v138 DSH `assets/engine.bin` is a GZIP/TAR with 30,411 members, 262,498,938 bytes of regular members and full-tree SHA256 `b2c7e52890351c4d1a3200c67ccb9be6154389a20da0b0b590d16676ce47b1e1`. The 9 `.node` native-addon entries are 1 ELF AArch64 Linux glibc, 1 ELF x86-64 Linux glibc, 2 macOS Mach-O and 5 Windows PE binaries, none automatically proven Android-compatible.

## P55 substantive implementation
- Re-run the full P54 signed-original APK SHA and opaque complete-tree digest gate; stop on byte drift.
- Stream the actual original TAR a second time and parse only bounded UTF-8 JavaScript (`.js/.mjs/.cjs`) and bounded `package.json` bytes **in memory**. No original member extracted to disk, committed, uploaded or printed. Skip oversized source with an explicit count.
- Collect aggregate-only static literal `require/import/from` syntax (heuristic lower bound), relative path resolution hints, native addon direct literal references, package entry fields (`main`, `module`, `exports`, `bin`) at archive root, `scripts.start` presence, optional dependencies, dynamic require/import hints and platform branching patterns. No module paths, script content, raw argv/env, user data, credentials or JavaScript stdout ever printed.
- Reject invalid/replayed or path-traversal member names, duplicate package JSON fields, unexpected large source or excessive imports. Limit scanning, line lengths, literal count, package count and total bytes. Synthetic-only regression asserts normal relative package imports and optional dependency, duplicate canonical archive entries, malicious traversal and duplicate package JSON fields.
- One private GitHub Actions job downloads only the exact signed original-v138 APK from the pre-existing private Release, runs synthetic tests and the static scanner, reports counts and absolute limits, and destroys all original APK and report bytes on cleanup. No binary artifacts, changes to installed DSH or fixed signing.

## What this does NOT establish
**Literal import scanning cannot prove the production engine's complete dependency graph or that a Windows/macOS/Linux native binary is actually imported on Android.** Dynamic require, runtime `process.platform`, package exports/conditional resolution, bundlers, URL/file loading, `dlopen` and Node's native module loader require separate runtime-equivalent tracing or deterministic source-level reconstruction. Counting `package.json` entries does not prove original EngineManager's actual command/working directory or server READY contract.

Android Bionic is not a general Linux glibc module loader. Do not attempt to dlopen 9 cross-platform addon binaries, lift SELinux/isolated UID restrictions, or expose general host-private filesystem access to make the app start. P47 host fallback remains blocked; original EngineManager `Process` assignment, read latch and StateFlow not yet wired to P53. Full chat/browser/files, persistent owner state, original certificate and formal v139 remain BLOCKED.

P55_EXACT_IMMUTABLE_ENGINE_SOURCE=UNDER_CI
P55_NATIVE_ADDON_ACTUAL_ANDROID_IMPORT_SET=UNVERIFIED
P55_COMPLETE_PRODUCTION_MODULE_GRAPH=NOT_PROVEN
P55_ORIGINAL_ENGINEMANAGER_PROCESS_PROXY=NOT_WIRED
P55_FIXED_SIGNED_V139=BLOCKED
