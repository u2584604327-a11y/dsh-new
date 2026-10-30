# P98 — Original AgentLoop session execution and Android host handoff gate

**Scope:** exact SHA-pinned original signed DSH v138 engine in private CI, using original Cordis services. **NEEDLE R5 integration explicitly deferred**. No modification of original APK, account credentials, OmniGate native owner, browser sessions or installed mobile data.

## Evidence established

1. The real original `AgentLoop` requires `agents`, `sessions`, `llm`, `tools`, `systemPrompt`, `sessionProjections`. On CI Node 22, all six genuine original first-party services boot, `agentLoop.create` is callable and `Promise.withResolvers` exists. Node 20 previously failed on that feature. This **does not establish the embedded Android Node version**.
2. `p98_original_agent_session_once.mjs` invokes real original `AgentLoop.create('p98_nonexistent_fixture_agent_no_model')` in a network-denied isolated temporary runtime. The returned instance owns `session`, `inbox`, `dispatch`; the original `SessionStore.get(id)` finds the created session. `P98_ORIGINAL_SESSION_ACTUAL_SESSION_CREATED_AND_STORED=PASS`; denied outbound attempt count zero. No user prompt or actual model was run.
3. Real `ReactLoopAgent` prototype exposes `send(message,target,wakeup)`, `followup(input)`, `steer`, `cancel`, `turn` and `step`; original `Session` exposes `append(type,data)` and `commit(event,entry)`. This is a contract observation only.
4. A separate synthetic `handle.send(input,'followup',false)` probe **does not pass** on an intentionally minimal original session. Error is `TypeError: Cannot read properties of undefined (reading 'length')` at `ReactLoopInbox.mutate → splice → ReactLoopAgent.send`. It proves this isolated fixture lacks a required inbox mutation precondition, **not** an Android production defect. This probe must be explicitly `BLOCKED_ORIGINAL_INBOX_MUTATION_PRECONDITION`; never fabricate or seed guessed inbox internals to declare success, and never claim the message was committed.
5. Earlier original module tests remain valid only within their scope: pi-ai text and tool streaming, actual original `ToolRuntime.execute` once, actual Cordis `tools/result` once, and a manually arranged two-round pi-ai continuation to a local synthetic SSE server. They **do not prove automatic AgentLoop continuation**.
6. `p98_original_node_capabilities.mjs` is a no-I/O executable probe returning the *runtime it is actually run inside*: Node version, platform/arch and required JavaScript features. CI shows a Linux Node 22 runner, not the Android phone. It has not been executed in the installed original Android EngineManager/Node process.

## Authoritative next implementation boundary

Reuse original DSH, not an extra chat engine:

`Original SessionController.prompt → validated original session + fully initialized projections/inbox → Original AgentLoop.send/turn → ToolRuntime → trusted Android Browser Broker → original tools/result → AgentLoop-owned continuation → original Cordis session projection → existing DSH chat UI stream`.

**Before making this live:**

- Obtain the real writable source of the installed Android `EngineManager` / original host integration; the candidate tests and APK binary alone do not provide a verified editable production callsite. Do not patch an APK blindly or distribute a resigning replacement.
- Through an existing trusted host diagnostic, execute the read-only P98 Node capability checker **inside the installed DSH Node process**. Assert Node supports `Promise.withResolvers` and the actual required features. Runner results are not enough.
- Use the real `SessionController.prompt(request,signal)` entry and original session-command/projection setup. Correlate accepted user turn, session ID, and output projection. Find the required inbox projection through the original service initialization path, not an invented `current()` array. Make one no-side-effect synthetic user turn; require a committed original session event.
- Register an approved read-only browser tool through the **original** `ToolRuntime`, backed by the trusted Android Binder broker and UI approval gate. No broad sandbox network, no raw Node host paths, no direct isolated UID socket to OmniGate 8787. Guarantee call ID/session ID correlation, one execution and one typed result. No publication, login or file writes.
- Require observable actual `AgentLoop` continuation after `tools/result` (not explicit second `pi-ai.streamSimple` authored in test). Verify same session's original UI receives incremental streamed assistant output, including WebView hidden/open/restart without losing trusted auth state.
- On owner mismatch 409, unknown result, revoked auth, missing live session, incorrect Node version, lost reply projection, or active user model generation, fail closed. Do not restart a generating model, auto-retry actions, reroute owner or claim success from HTTP 200/SSE DONE.

## Release and model policy

PR #80 remains Draft. No installed/signed APK, no merge, no production browser controls, no Bilibili comment publishing, and no R5 connector may be declared ready from these isolated CI checks. NEEDLE R5 remains disabled until its separate independent inference/holdout/safety evaluation after the DSH native loop is connected.

## Required evidence for lifting the stop

Actual device Node major/features; trusted original EngineManager process ownership; original SessionController accepted user turn and projection ID; original `ToolRuntime` execution call ID; Binder read-only result / explicit approval status; original `tools/result` once; original AgentLoop own follow-up request once; original DSH chat incremental paint timestamps; hidden-browser lifecycle/session persistence; 409 and isolation failures still denied. Never include API secrets, page contents, user conversations, Cookies or auth tokens in public artifacts.
