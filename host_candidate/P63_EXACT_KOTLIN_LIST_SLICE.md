# P63 command List Kotlin factory and return-value slice

Exact pinned signed-v138 baseline is P62 Draft #46 HEAD 238b738cfef7f4066f4eb1717b7cc38dae58327e; CI 41012856132 SUCCESS. P62 proved the original ProcessBuilder(List) source passes through a generated 3-instruction wrapper into an actual 43-instruction DSH instance method containing exactly 2 Kotlin collection calls, 5 literal sites, 3 branches and 1 return-object.

P63 reports safe public Kotlin collection symbol names and API categories, known-safe method descriptor shapes, original call form, number of decoded operands, bounded local argument provenance, jump-target counts and return-value local def-use. If invoke-range, mismatched registers, branch, source window or opaque call appears, mark unknown and do not convert string proximity into real argv, executable entry, READY condition or dataflow proof. Class and method names, literal texts, file paths, argv/env, source and keys are never emitted.

This source-only CI downloads only exact SHA-pinned original v138 from private release, runs P62/P61/P60/P54 structural chain, executes synthetic assertions, then purges original bytes. Original script, Node engine and native .node addons are never executed.

Release gates remain: full original Node argv/env/cwd and READY/exit/lifecycle, genuine P53 process isolation plus no host fallback, diagnostic per-send approval, actual Android emulator and owner-device upgrade and regression, com.dsh.android versionCode > 138 and same verified fixed signing fingerprint. No new signed v139 APK or GitHub release until satisfied.
