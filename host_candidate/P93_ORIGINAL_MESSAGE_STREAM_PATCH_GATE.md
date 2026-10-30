# P93 original-chat message state and UI frame patch boundary

The user selected DSH as the single message entry; OmniGate 8787 remains the provider. This phase supplies **immutable per-turn revisioned message snapshots** to a callback intended for the existing DSH chat store; no Activity or synthetic replacement TextView is created.

- `P93TurnMessageState`: keeps reasoning as a phase, tool-call events as metadata, assistant body as content, explicit [DONE] as COMPLETE, and early EOF as TRUNCATED without erasing previously rendered text. Rejects data after terminal and enforces bounded text.
- `P93MainThreadPatchDispatcher`: receives immutable turn snapshots from network threads and posts to Android main looper; first text and terminal states immediately scheduled, subsequent frames coalesced within 48 ms; stale generations and stale revisions rejected; does NOT call setContentView.
- JVM test verifies first content before complete, reasoning/tool separation, monotonic revisions, preserved partial content on truncated transport, content limits.
- Compile against Android SDK is a **source check**, not a real on-phone UI paint proof.

Production blockers: the exact original `MainActivity` model network/SSE owner still needs to be patched with P87/P89 and this message state; the correct original message store identity and lifecycle must be derived from pinned DEX/JS source, not guessed. Tools must be dispatched by original authorized plugin broker and results returned to same model turn. P89 Android emulator hit SDK ZIP install infrastructure failures; that does not verify real UI. DSH phone logs contained fake SENT from empty composer; P90/P92 remain source-only and have not fixed phone. Never claim real APK release, create original login state or shut down thinking/generation.
