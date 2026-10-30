# P59 — original signed-v138 ProcessBuilder constructor exact backward slice

Baseline P58 Draft PR #42 HEAD 4538881acfa73fa2a5a3572ae9189f301986b55f; CI 41003554840 SUCCESS. Original P35 EngineManager$start$2.invokeSuspend code_off 3163260, unique ProcessBuilder.start PC3912 and P54 full immutable engine tree are prerequisites, revalidated through the P58/P57/P56/P54 chain.

P59 targets only the original unique ProcessBuilder constructor. It reports its descriptor category (List / String array / Other), decoded argument register count, and each argument's closest within-basic-block register definition (including move-object chains and immediate invoke/move-result producers) as bounded categorical data. Cross-branch, jump targets, unknown field reads, ctor object contents, invoke-range and out-of-window origins remain UNKNOWN; **no script/argv value or name is revealed and no actual executable entry is claimed**. The secondary READY scan reports bounded within-block nearby string comparison, Latch and StateFlow APIs; syntactic proximity is not predicate causality.

The current scope is not a full CFG/SSA or heap/alias analysis. Constructors may receive a list whose elements are assembled through branches, fields, callbacks and coroutine state; identifying a List allocation alone does NOT prove its contents. Unknown return values remain opaque. Synthetic tests enforce overwrite, branch, field, factory, invoke-range and READY-branch false-positive rules.

Private GitHub Actions may read only the exact signed-v138 source and scripts as passive bytes; must never execute JS/Node/native addons, disassemble and print sensitive strings, publish source artifacts, modify the original phone or signed APK, change P53/no-fallback isolation permissions, merge/release or sign v139. Always destroy the APK and temporary aggregate logs.

P59_SOURCE_ONLY=CI_PENDING
P59_COMPLETE_PROCESS_ARGV_AND_READY=NOT_PROVEN
P59_P53_PRODUCTION_INTEGRATION=NO
P59_FIXED_SIGNED_V139=BLOCKED
