# P40 exact v138 EngineManager trampoline — read-only baseline, ephemeral unsigned rebuild

P39 observed three separate original ProcessBuilder.start sites:
- Target: EngineManager$start$2.invokeSuspend at main classes.dex code_off 3163260, PC 3912.
- Excluded: EngineManager.probeBoot PC 310 (code_off 3176996).
- Excluded: EngineManager.runDumpConfig PC 472 (code_off 3176192).

This phase tests real original bytecode patch feasibility without running new Node privileges. It only rewrites the EXACT main engine-launch invoke to a static method in main classes.dex which immediately calls the original ProcessBuilder.start() with the same builder reference. Process handle, stdout reader, CountDownLatch and Ready setter remain unmodified at source level. The two other EngineManager ProcessBuilder sites are preserved.

## Evidence gates
- Exact private signed v138 APK hash and byte size, P35 six original postspawn lifecycle callsites.
- Decode smali without resource decode; target and two excluded entry methods must exist.
- Exactly one original invoke virtual in target with one register. Only that line rewritten, preserving register operands.
- Add P40ProcessBridge.start(ProcessBuilder) : Process as a legacy direct pass-through.
- Rebuild into an **unsigned** CI-only APK; confirm resulting main DEX contains exactly one target static bridge invocation, the bridge calls original ProcessBuilder.start and two excluded locations still call original builder.
- Destroy all original and derived bytes in always(); no artifact, release, upload, original signing or phone installation.

## What this does NOT accomplish
- Node remains launched in the original host if code actually ran. This is a **compatible interception point experiment, not isolation**.
- No protected Binder worker integration, no process supervisor, no original node environment cloning, no Shizuku/Termux startup changes, no production data/credentials.
- No ART / v138 clean-room launch or full chat/browser/media/files regression. Original v139 remains BLOCKED.
- A valid binary rewrite does NOT prove original app functionality or safety. Never use it to install over user's signed v138.
