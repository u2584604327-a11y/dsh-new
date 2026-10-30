# P56: Exact original EngineManager startup / READY structural slice

Verified baseline: P55 Draft PR #39 HEAD 49590a7f32b4004bf3f3dd1f8b81ff307e264dcd, CI run 40996832566 SUCCESS. P35 verified v138 original EngineManager startup ProcessBuilder.start at code_off 3163260 and PC 3912, followed by Process assignment, reader thread, CountDownLatch and StateFlow.

P56 reads the original exact signed v138 APK and P54 immutable engine tree in private CI; it never executes original scripts, child processes, or native addons. It inspects EngineManager$start$2.invokeSuspend and nested start callback methods, counts categorized ProcessBuilder command/env/cwd/start, process streams, regex hints, latch and StateFlow APIs, and compares only constant string equality to APK asset names. No original path, string, regex, argv, environment, source content or output is logged. Synthetic tests reject original spawn/lifecycle offset drift and candidate source mismatches. All original APK input and transient logs are removed by the CI runner; no artifacts or release.

Important limitation: finding an asset string in the original DEX is not proof that it is actually the executed JS. Even a literal equal-name match does not prove argv/provenance, READY condition or the script dependency closure. Dynamic startup command construction and coroutine branch conditions remain unresolved. Original P53 Process facade must not replace the EngineManager process until command, cwd, env, JS script, READY, stdin/stdout/exit lifecycle and restricted broker requirements are validated by separate tests. No unrestricted filesystem/network grants, host fallback, device mutation, fixed-signing or production release.

P56_ORIGINAL_LIVE_NODE_READY=NOT_PROVEN
P56_P53_PRODUCTION_ENGINE_WIRING=NO
P56_FIXED_SIGNED_V139=BLOCKED
