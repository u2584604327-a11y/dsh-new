# P54 — Exact original production engine: complete TAR SHA-256 and native addon metadata (READ ONLY)

## Purpose and evidence
P53 confirmed the exact signed v138 DSH `assets/engine.bin` is a GZIP wrapper around a TAR with 30,411 entries (including 9 `.node` native addons). P50/P51 owner ARM64 original SHA-pinned Node in isolated UID passed synthetic UID/BOOT/READY/EXIT, and P53 authenticated CHILD_STARTED after real ProcessBuilder.start in an Android35 emulator. **Neither has executed the production engine.**

P54 analyzes the immutable exact original v138 source **without executing or extracting any JS**. Every one of the 30,411 TAR entries is subject to strict path length/canonicalization, duplicate normalized name, link/special file denial, bounded member sizes, bounded declared total sizes and maximum member count. Every regular-file byte is streamed through SHA-256; a stable aggregate tree SHA-256 binds normalized path bytes, file kind, byte count and full file SHA-256. The aggregate root is opaque: original member paths, individual file checksums and code are never logged or published. GZIP/TAR are read only in memory, and no JS is written to a staging directory.

All nine native `.node` extensions are hashed. Each ELF is inspected **read-only** with `readelf -d` through a transient Linux anonymous memfd (no executable launch and no durable addon file). CI reports only CPU architecture distribution and `DT_NEEDED` sonames; those are dependency metadata, not proof that Android's native loader can load them. Unexpected ELF metadata or unsupported archive shapes fail closed.

Adversarial synthetic TAR tests cover canonical path traversal, control chars, duplicate normalized paths, symlink/hardlink/device entries, source tampering, ordering, and deterministic tree hashing. One private GitHub Actions job downloads the exact SHA-pinned original v138 APK from the already-established private release, performs the pure synthetic tests and exact original archive audit, then deletes its temporary original APK and summary in an always-run cleanup. There are **no uploads, generated APKs, release/signature changes, user device changes, or changes to app privileges**.

## Important limits
- SHA-256 inventory is static evidence; it is not the production file distribution/broker implementation and contains no approved resource-loading capability.
- TAR members' paths do NOT give isolated child access to original host-private dirs. Implementing a real read-only module graph will require a separately scoped, immutable, content-addressed Node JS module source and native-addon loader design compatible with app package/SELinux restrictions.
- Original DSH production script entry point, cwd, env, dependency graph and READY protocol are not proved by this audit.
- The previously successful P53 CHILD_STARTED is not production READY. P47 original EngineManager main Node launch still denies unsafe host fallback. Full DSH chat/browser/file and fixed signing remain blocked.
- If the original archive has aliases, unexpected links, noncanonical paths, binary errors or bad native addon metadata, STOP with status; do not silently normalize, skip or rewrite real files.

P54_EXACT_ORIGINAL_ENGINE_TAR_TREE=UNDER_CI
P54_ANDROID_NATIVE_ADDON_RUNTIME_LOADING=NOT_TESTED
P54_PRODUCTION_IMMUTABLE_MODULE_BROKER=NOT_IMPLEMENTED
P54_ORIGINAL_ENGINEMANAGER=NOT_CONNECTED
P54_FIXED_SIGNED_V139=BLOCKED
