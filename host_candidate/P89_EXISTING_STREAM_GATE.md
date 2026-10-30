# P89 existing-response SSE incremental delivery gate

Base: P88 exact original DSH source-locked SSE/UI owner audit; preserves P87 incremental UTF-8, CRLF, [DONE] decoder and Android TextView probe.

Added:
- `P89ExistingStreamPump.consume(InputStream, Observer)` takes **an already-open, existing stream=true response body**, reads incremental bytes on the existing network reader thread; does not create a request, take over a port, close the caller's stream, retry, or impose a long-thinking content timeout.
- Decoder remains P87, so a Chinese UTF-8 character split across byte reads remains intact; missing [DONE] is fail-closed and earlier text is retained by the existing UI view.
- `P89ToolCallAssembler` reconstructs bounded OpenAI `tool_calls[index]` with ID, fragmented name and arguments. It only exposes assembled calls after explicit [DONE] and a tool_calls finish reason; **it never executes tools or authorizes publishing a comment**.
- P89 disposable Android Activity verifies a **real Android pipe InputStream** delivering timed events into the main-thread TextView, with first Chinese delta displayed before producer ends, reasoning separate, and tool argument reassembly. The external HTTP chunked network streaming path remains independently tested by P87 JVM tests.

Limitations / required next step:
1. Original DSH MainActivity/model network InputStream owner -> P89 consumer -> actual original chat message state/adapter **NOT_WIRED**. P88 categorical method inventory does not identify a validated callsite. No live original DSH + OmniGate end-to-end evidence.
2. Original browser tool_result and user-approved Bilibili publish path are separate gates. Assembled tool calls are untrusted data, **not** executed.
3. P51 disposable test package has no INTERNET permission and is different from the installed signed DSH. Do not treat Android pipe as OmniGate production network.
4. No original key/signature, production APK, credential, token, user message, proxy port, process restart or changing active model state in this task.
