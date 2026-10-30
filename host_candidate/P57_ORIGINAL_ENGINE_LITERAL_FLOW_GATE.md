# P57 - Original EngineManager literal-to-register and READY-proximity gate

P56 Draft PR #40 HEAD 5198a2c43263fc03e60503e09cd0ceff51234230 and GitHub Actions run 40999886565 SUCCESS establish original signed v138 and immutable engine tree, 5 APK JS assets, 24 ZIP assets, 9 original start-family methods. P56 observed one JS-shaped literal and two READY-hint literals in the start family, zero exact asset literal matches. EngineManager$start$2.invokeSuspend ProcessBuilder.start PC3912 and code_off3163260 are pinned.

P57 adds the **real signed APK read-only** local DEX register-copy trace for those string classes. It tracks const-string, move-object register copies and direct invoke registers, kills register provenance on overwrites, jumps, branch boundaries, and switch/return, categorizes ProcessBuilder constructor/command/start, List add, String comparisons, CountDownLatch, StateFlow calls, and separately emits same-method PC distance buckets. No string value, filename, argv, environment, regex, JS body, hardware identifier, user data or path is emitted. Synthetic regressions test positive copy flow and negative register-overwrite/branch barriers.

P57 is explicitly NOT whole-program taint analysis. Kotlin suspend state machine branches, indirect calls, object/list aliasing, register targets not decoded by androguard, use after exception edges and ZIP/script expansion remain unresolved. Do not infer actual script name, argv, READY condition, or chat service operation from static proximity or local register matches.

Only one ephemeral private GitHub Actions job runs this code against the exact SHA-pinned v138 release after P56's full source hash audit. Original APK and logs are deleted after job; no artifact upload, script execution, real device modification, fixed signing, merging, production fallback or sandbox bypass. P53 Process proxy not connected to original EngineManager. v139 BLOCKED.

P57_STATIC_LOCAL_REGISTER_TRACE=CI_PENDING
P57_DETERMINISTIC_JS_LAUNCH_AND_READY=NOT_PROVEN
P57_FIXED_SIGNED_V139=BLOCKED
