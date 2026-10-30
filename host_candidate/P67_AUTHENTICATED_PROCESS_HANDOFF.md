# P67 — actual P53-to-P37 host process handoff candidate

Baseline P66 Draft #50 SHA 537939fc083d719d0521dbec7aa45b782bf5d4af signed-v138 passive CI 41020752517 SUCCESS. P66 resolved the original 13-instruction loop and its two add sites; actual full Node argv and original EngineManager READY predicate remain unproven.

This phase introduces a production-minded, source-only Java 8 host lifecycle coordinator linking two **previously implemented** primitives:
- P53StartOrder (HELLO0 → CHILD_STARTED1 → STDOUT/ERR/EXIT, strict sequence).
- P37RemoteProcess (authenticated UID/session, bounded streams, terminal transport/stop controls).

The coordinator **must not construct or expose** the Process facade on HELLO; it only allocates it after authenticated CHILD_STARTED. Each frame checks framework Binder sender UID and host-generated session. Invalid seq/UID/session, too-large stream, duplicate start, and binder death irreversibly fail closed. A genuine exit without original READY is a valid early-exit condition. Neither stdout nor CHILD_STARTED is a READY proof. There is intentionally no ready setter or READY promotion until verified original DSH EngineManager reader/parser semantics are integrated. Host frame caller must use actual framework Message.sendingUid, never untrusted Bundle fields.

This source candidate DOES NOT implement Android Binder binding, original DSH EngineManager trampoline, sandbox Node execution or full READY/exit. It leaves P47 original fail-closed launch untouched. JVM tests only and no signing key or original APK usage in this CI. No production v139 APK, installation or merging. Future work: implement the authenticated Android Binder adapter from original EngineManager to this coordinator, with verified original launch, no host fallback, and controlled data plane; run emulator and owner-device regression.
