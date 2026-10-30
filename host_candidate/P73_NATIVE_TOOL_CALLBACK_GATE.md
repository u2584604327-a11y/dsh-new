# P73 real Android WebView browser tool callback probe

P70 shared command/reply mailbox race was fixed and CI verified. P71 added exactly-once tool result contract and Android CookieManager+localStorage persistence proof. P72 identified a real v138 private AiBrowserView.currentWebView accessor and an exact visibility patch for test APK. This phase exercises the Android layer missing from pure JVM tests: a genuine WebView evaluateJavascript operation has to produce a callback and complete the matching P71ToolReplyOnce exactly once; a silent callback times out with UNKNOWN outcome.

Only synthetic local non-network page and side-by-side ephemeral-signed com.dsh.p51.isolatedprobe package are allowed. Five sequential steps check reading page text, scroll capability, locating comment text area, entering a synthetic draft, and making sure the Publish button was NOT clicked. Model must not claim a comment was submitted. No real Bilibili account, webpage, login or user cookies are accessed.

This is still not the original AiBrowserView browser executor nor native tool_result/model continuation. Original app browser bridge, mailbox response writer, Bilibili dynamic controls, fixed-signed v139 and actual EngineManager/Node script remain pending. CI must report the separate statuses instead of assuming passing synthetic probes solve the user's phone.
