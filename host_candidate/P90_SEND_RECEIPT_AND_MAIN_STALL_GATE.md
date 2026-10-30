# P90 — 2026-10-30 user phone log evidence, fail-closed receipts

## Original user phone evidence, not a new APK result
- 18:51:43: Original DSH Node engine READY, loopback 3080, ~11.97 s.
- 18:51:45: `余额刷新(启动) 未登录`, then wallet/bonus/total were presented as 0; cannot infer actual zero balance.
- 18:51:34: Shizuku manager exists but binder=false and authorized=false; separately, DSH says uid2000 execution channel available. The original 5555 ADB TCP bridge repeatedly cannot authenticate. Do not equate manager installed or legacy helper existence to authorized live privileged execution.
- 19:43:01: DSH app-local watchdog detected `main-thread-stall` lasting 15,099 ms. It saved `crash/20261030-194301-main-thread-stall.txt`. The file itself was NOT provided. Cause/stack/lock contention NOT established; no kernel/system ANR assertion.
- 21:05:57, 21:06:30, 21:08:10: bubble injection reported `{"len":0,"sendDisabled":true}`, followed by `SENT`; this is untrusted click-level status, NOT verified model input, new user turn, or assistant generation.
- P89 incremental SSE and original DSH network/UI integration remain separate gated work.

## This branch's actual code
- `P90SendReceiptGate`: if injected editor is empty, disabled, mismatched or unparseable, `REJECTED` even when the later click log says SENT. A successful click leaves `DISPATCHED_UNCONFIRMED`. Only correlated, trusted **actual original chat user-turn observation** promotes it to `CONFIRMED`. Unknown outcomes never auto-retry, protecting against double sends. Gate does not perform JavaScript/WebView calls or touch the real model.
- `P90EvidenceProjection`: `未登录`, `未提供`, `≈估算`, and Shizuku manager/binder/authorization/channel truth all remain distinguishable. Zero is shown only when an authoritative authenticated zero was actually supplied.
- Targeted original DEX read-only method locator uses SHA-pinned signed v138, anonymous method IDs and limited categories; no original strings, tokens, APK binaries or user messages in report.

## Mandatory next production step / hard block
Identify and verify exact original bubble injected-js input readback, click callback, and original chat turn observer. Wire this gate before any successful send UI. Do NOT patch based solely on matching log strings or a method family. Inspect the 19:43:01 main-thread stack file *locally with explicit privacy review* before identifying lock contention, WebView call, thread or repair; scrub tokens, cookies and private message text. No unreviewed upload. Keep installed v138, credentials, sessions, active OmniGate native socket, and production engine untouched. No claim of real Android production repair; branch is source-only and CI read-only.
