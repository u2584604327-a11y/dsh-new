# P60 — original v138 ProcessBuilder(List) return-value producer

Based only on P59 Draft PR #43 HEAD 11c48ca02dc3401a47814e9b9ada4d4056e68951, verified GitHub Actions run 41005118755 SUCCESS. P59 showed one exact ProcessBuilder(List) constructor with receiver + List parameter; last same-block definition for List is an opaque move-result from an invoke.

P60 performs **targeted local backward def-use** to identify the immediate invoke that produced the List. It outputs only closed, finite categories for owner namespace, method category, JVM return descriptor shape, opcode, decoded registers, formal parameter count and each input's bounded local def-use category. Raw original owner/class/method identifiers, literal script values, paths, argv, environment variables or secrets are never emitted. Branch, field, alias, unknown call, invoke-range and cross-method boundaries remain UNKNOWN; an invoke producing a java.util.List does not prove its contents or actual executable startup argv. Descriptors are shapes only, not runtime observations. A single source witness must not be promoted into an unqualified proof of original entry or READY.

Private source-only GitHub Actions verifies exact signed-v138 APK sha256 and P54 immutable engine archive; re-runs full P59→P54 provenance and tests, then prints categorical report only. Always clean exact original APK and temporary logs. Do not start Node, JS or .node addons; do not modify P53/host process/permissions, original DSH device, fixed signature, create APK, release or merge. Keep Draft.

P60_PRODUCER_CATEGORY=CI_PENDING
P60_FULL_LIST_CONTENTS_AND_ARGV=NOT_PROVEN
P60_READY_PROTOCOL=NOT_PROVEN
P60_SIGNED_V139=BLOCKED
