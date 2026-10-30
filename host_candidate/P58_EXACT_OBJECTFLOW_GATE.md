# P58 — exact signed v138 conservative StringBuilder/List/ProcessBuilder and READY object propagation

P57 Draft PR #41, HEAD d7b6207c58b2abd704ada9321d33c9958f601574, CI run 41000788019 **SUCCESS**. P57 measured 9 start-family methods, 1 JS-shaped literal and 2 READY-hint literals, 57 StringBuilder.append calls, 1 ProcessBuilder constructor, 1 start, 4 Latch signals and 8 StateFlow writes. Proximity was NOT dataflow.

P58 evaluates within-method, branch-bounded provenance only. It tracks const-string classes, move-object aliases, new StringBuilder/ArrayList/array, their append/add/store, toString/move-result, and ProcessBuilder constructor/command argument objects. It also records direct READY-hint String comparisons and direct StateFlow argument presence, but cannot prove branch predicates control READY. Unknown calls invalidate tracked object provenance; branches/jump targets clear state, so negatives mean INCONCLUSIVE, not absence of dependency. Live runtime, method aliasing, heap references, coroutine state machine, exception edges, spread arrays, invoke-range argument corner cases and JNI remain NOT_COVERED.

Re-verify the P57/P56/P54 immutable exact-v138 APK SHA and engine tree before scanning. Only synthetic tests and original-signed read-only private CI. Print aggregate categories and counts, never actual strings, paths, source, argv/env, device IDs or secrets. Do not extract original scripts to disk, execute Node or native addons, upload original APK/workflow artifacts, sign any v139 APK, modify original DSH owner device, change sandbox permissions or connect P53. Delete all private inputs/outputs in ephemeral CI. KEEP DRAFT, NO MERGE.

P58_EXACT_ORIGINAL_OBJECT_FLOW=CI_PENDING
P58_COMPLETE_CFG_PROVENANCE=NO
P58_PRODUCTION_COMMAND_AND_READY=NOT_PROVEN
P58_P53_ORIGINAL_RUNTIME_CONNECTION=NO
P58_FIXED_SIGNED_V139=BLOCKED
