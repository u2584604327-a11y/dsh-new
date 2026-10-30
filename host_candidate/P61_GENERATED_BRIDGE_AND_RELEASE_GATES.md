# P61 real original DEX generated-bridge inspection and formal APK gate

Baseline P60 Draft PR 44 HEAD 1f7f6867cabeac05e15e989d2c3d7ff1b2522f49, actual signed-v138 CI 41009853774 SUCCESS. The ProcessBuilder(List) argument comes from a DSH application generated-name static invoke-range returning java.util.List. P61 resolves the exact method declaration across classes.dex and classes2.dex, checks access flags, code presence, return / List / array operations and invoke-range encoding. Report categorical counts only. Do not expose original class/method identifiers, script/path/argv/env contents or binaries.

Formal release prerequisites (not satisfied merely by P61):
1. com.dsh.android package with versionCode > 138, exact existing certificate SHA256 90072b7de43e96999be92d99869ce5e5b7639b5f2449417b99a1790831b60ff8.
2. Existing fixed signing PKCS12 file DSH_BROWSER_FIXED_SIGNING_KEY.p12, alias dsh-browser-fixed and separate password are preserved, privately verified in model session. No key rotation and no upload to repository, PR, CI logs, artifacts or release. Use local trusted signing only AFTER acceptance.
3. Original Node script entry and all startup argv/env/cwd, READY signal, process exit, process shutdown, cancellation and reader stream semantics must be proven, then original EngineManager must actually use the authenticated isolated P53 worker rather than only obtaining child ACK.
4. Zero direct host ProcessBuilder fallback for production; diagnostics send requires trusted native per-packet review/redaction/revoke; ordinary file/photos not blocked.
5. Emulator + authorized owner phone tests for original WebView, provider input/send/stream, session continuity, token usage, floating bubble, virtual environment isolation, same-package upgrade with data preserved, rollback gate.
6. Build signed production APK only after all checks PASS. Ephemeral emulator APK is NOT formal. Keep Draft, no merge or release.
