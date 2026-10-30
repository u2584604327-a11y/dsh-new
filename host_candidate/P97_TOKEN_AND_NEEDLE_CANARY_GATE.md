# P97 Token provenance and experimental NEEDLE tool model — release boundaries

Status: TOKEN_DISPLAY_SOURCE_CANDIDATE=CI_PASS; REAL_PROVIDER_USAGE=NOT_VERIFIED; DSH_INSTALLED_APK=NOT_MODIFIED; NEEDLE_INTEGRATION=DEFERRED.

## Exact shipped vs source-tested boundary

The original user's DSH Token display may show `0 tok` for local/LAN API turns. In this repo `patch_token_usage_p14.py` only patches exact SHA-pinned P6 `assets/browser-tool.zip` / `payload/mobile-ui/lib/client.js`. It does not modify the installed DSH APK or original Cordis token accounting. CI proves archive-scoped byte integrity and three-state UI representation, **not** authoritative live counts from user local model.

The updated classifier preserves both unprefixed input/output values, marks both estimated values as estimated, and does **not** falsely convert mixed `5 tok` + `≈25 tok` into provider-official usage. For mixed source fields, original per-field numbers remain unchanged, zero turn total is hidden, and the turn header becomes `来源混合`. When neither actual nor justified estimate exists, `— tok` replaces ambiguous zero, not an invented count.

For a production token counter, the preferred source order is: verified provider `usage` with its response/turn ID; verified model tokenizer metadata applied to exact prompt/result only as **estimate**; `unavailable` otherwise. Streaming `usage` typically arrives in a later completion frame, so the display must update when the authoritative frame arrives; *never* accumulate cumulative usage across frame repeats, *never* assume a missing usage field means zero, *never* claim exact model tokens from character counts, *never* classify a prefixed `≈` value as provider. Reconcile each turn exactly once, handle multi-step tool calls without summing the same context multiple times unless provider explicitly bills each step.

OmniGate's current native SSE proxy forwards bytes but does not by itself establish accurate native provider token counts for DSH's original per-turn UI. First require a real LAN API fixture with explicit `usage`, then validate `stream:true`, tools and nonstream API separately, including `stream_options.include_usage` support detection rather than assuming every backend implements it. Token costs are UNKNOWN until the provider supplies billing units; local model generated tokens do not imply a paid API charge.

## Deferred local model: XIAOYU NEEDLE V2.2 R16 / R5

Candidate is *not* authorized to operate the actual browser, Android UI, files, remote API, or Bilibili. Prior R2 20L validation was 326/616 (52.92%) and the post-gate policy violation proxy was 119/462 (25.76%); subsequent R4 and R5 evidence has not produced a valid locked primary candidate. R5 post-train local inference dependency/reproducible measurement is blocked, V5 independent holdout remains unopened, and PRIMARY_CANDIDATE_LOCK is not created. Those older numbers do not predict its current R5 capability.

Plan only, default OFF:
1. Verify actual R5 inference runtime, base model + adapter compatibility and required CPU memory/latency on the user's Windows machine. No model registration until validation results are available. Never put model paths/secrets in repo.
2. Freeze a scored candidate and complete independent holdout, no-tool, argument correctness, prompt-injection rejection, refusal/safety, denial and timeout metrics. Do not infer a safe browser tool agent from training loss alone.
3. Create a separate explicitly selectable local model profile only after the supported API transport (e.g. OpenAI-compatible) is confirmed; use the already verified original DSH pi-ai model adapter. No replacement of the current model by default; a manual fallback remains.
4. Start in **dry-run/no side effects**: fake read-only tools, no network egress, no filesystem, and no live Android broker. Compare actual model tool-call arguments with expected and capture only synthetic traces.
5. For a later real phone pilot, Android trusted host must enforce tool allowlist, per-action user approval, signed request/turn/call IDs, single-flight, result provenance and no auto-retry of unknown outcomes. The model's tool request is never permission by itself.
6. All existing production blockers still apply: original EngineManager and Cordis AgentLoop session wiring, isolated Node 127.0.0.1 EACCES, OmniGate runtime-owner 409 fail-closed, live streamed UI and original APK signature. No build or publish until proven.

This is a **deferred integration gate** and source-tested token display improvement, not a working local model connector, training job, security certification or Android release.
