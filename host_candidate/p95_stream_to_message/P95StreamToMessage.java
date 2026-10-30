package com.dsh.android.p95;

import com.dsh.android.p87.P87SseDecoder;
import com.dsh.android.p87.P87OpenAiDelta;
import com.dsh.android.p89.P89ExistingStreamPump;
import com.dsh.android.p89.P89ToolCallAssembler;
import com.dsh.android.p93.P93TurnMessageState;
import java.util.List;

/**
 * Minimal adapter on the EXISTING DSH response stream. No new HTTP connection,
 * chat UI, tool executor, login, host ownership, or original engine changes.
 */
public final class P95StreamToMessage implements P89ExistingStreamPump.Observer {
    public interface ToolReady { void onToolCalls(List<P89ToolCallAssembler.Call> calls); }
    private final P93TurnMessageState turn;
    private final P89ToolCallAssembler tools = new P89ToolCallAssembler();
    private final ToolReady onTools;
    private boolean sawDone, failed;
    private String finishReason = "";

    public P95StreamToMessage(P93TurnMessageState existingTurn, ToolReady callback) {
        if (existingTurn == null || callback == null)
            throw new IllegalArgumentException("P95_MISSING_EXISTING_TURN_OR_TOOL_SINK");
        turn = existingTurn;
        onTools = callback;
    }

    @Override public void onEvent(P87SseDecoder.Event event) {
        if (sawDone || failed) throw new IllegalStateException("P95_EVENT_AFTER_TERMINAL");
        try {
            tools.accept(event);
            P87OpenAiDelta delta = P87OpenAiDelta.parse(event);
            if (delta.error) throw new IllegalStateException("P95_SSE_EVENT_ERROR");
            if (!delta.finishReason.isEmpty()) finishReason = delta.finishReason;
            if (!delta.reasoning.isEmpty()) turn.reasoning();
            if (!delta.content.isEmpty()) turn.content(delta.content);
            if (delta.toolFragments > 0) turn.tools(delta.toolFragments);
            if (event.done) {
                sawDone = true;
                List<P89ToolCallAssembler.Call> ready = tools.verifiedToolCalls();
                if (ready.isEmpty()) {
                    // SSE [DONE] alone is not a valid nonempty model reply.
                    // Context-length stops preserve partial text but do not
                    // report natural model completion.
                    if ("length".equals(finishReason)) {
                        turn.closedWithoutDone();
                        throw new IllegalStateException("P95_CONTEXT_LENGTH_INCOMPLETE");
                    } else if ("tool_calls".equals(finishReason) ||
                               "function_call".equals(finishReason) ||
                               "content_filter".equals(finishReason) ||
                               turn.snapshot().content.trim().isEmpty()) {
                        throw new IllegalStateException("P95_NO_VERIFIED_ASSISTANT_REPLY");
                    } else {
                        turn.done();
                    }
                } else {
                    // This assistant stream ended to request tools, but the
                    // original MODEL TASK is not complete until results return.
                    onTools.onToolCalls(ready);
                    turn.awaitingToolResult();
                }
            }
        } catch (RuntimeException bad) {
            failed = true;
            turn.failure();
            throw bad;
        }
    }

    @Override public void onTerminal(boolean explicitDone, String reason) {
        if (sawDone && explicitDone) return;
        if (failed) return;
        failed = true;
        if (!explicitDone && "MISSING_EXPLICIT_DONE".equals(reason)) {
            turn.closedWithoutDone();
        } else {
            turn.failure();
        }
    }
}
