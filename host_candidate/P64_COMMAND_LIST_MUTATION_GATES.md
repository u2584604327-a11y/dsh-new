# P64 exact ListBuilder mutation site and argv element audit

Source: exact original signed-v138 P63 Draft PR #47, final head 7cf680da627f771a6437b6fcbbbfc18456e72bfd; actual GitHub Actions 41015985318 SUCCESS. The verified 43-instruction DSH internal command List method calls Kotlin standard library createListBuilder() then build(List). Its only return-object has same-basic-block producer build. The build input origin is UNKNOWN_CONTROL_BOUNDARY.

P64 focuses on actual List/Collection/ListBuilder add, addAll, set, remove and clear in this exact method, counts mutators and categorizes their argument source without exposing any original bytes, string literal, argv, path, user data or original DSH method name. An add call or JS-shaped literal does NOT prove the dynamic launch argv or its order; unknown branches, aliases and invoke-range remain unknown. No real script, Node, native addon or phone activity.

Formal APK release is still conditioned on real production argv/env/cwd + engine script import closure, readiness and shutdown, P53 isolation using the true EngineManager with no host fallback, trusted diagnostic approval, original WebView/provider regressions, Android same-package upgrade and data preservation. Fixed signing key/alias/cert are already privately verified, but no signing or GitHub upload is allowed before these gates.
