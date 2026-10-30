package com.dsh.android.p89;

import com.dsh.android.p87.P87SseDecoder;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Incremental OpenAI Chat Completions tool-call assembly; never executes a tool. */
public final class P89ToolCallAssembler {
    public static final class Call {
        public final int index;
        public final String id, name, arguments;
        private Call(int n,String i,String f,String a) {
            index=n; id=i; name=f; arguments=a;
        }
    }
    private static final class Partial {
        String id = "";
        final StringBuilder name = new StringBuilder();
        final StringBuilder args = new StringBuilder();
    }
    private final TreeMap<Integer, Partial> calls = new TreeMap<>();
    private String finish = "";
    private boolean done;
    private int events;

    public void accept(P87SseDecoder.Event event) {
        if (done) throw new IllegalStateException("P89_EVENT_AFTER_DONE");
        if (++events > 100000) throw new IllegalStateException("P89_EVENT_LIMIT");
        if (event.done) {
            done = true;
            return;
        }
        if ("error".equals(event.event)) throw new IllegalArgumentException("P89_UPSTREAM_ERROR");
        try {
            JSONObject root = new JSONObject(event.data);
            if (root.has("error")) throw new IllegalArgumentException("P89_UPSTREAM_ERROR");
            JSONArray choices = root.optJSONArray("choices");
            if (choices == null || choices.length() == 0) return;
            JSONObject choice = choices.optJSONObject(0);
            if (choice == null) throw new IllegalArgumentException("P89_BAD_CHOICE");
            if (!choice.isNull("finish_reason")) {
                String reason = choice.optString("finish_reason", "");
                if (!reason.isEmpty()) {
                    if (!finish.isEmpty() && !finish.equals(reason))
                        throw new IllegalArgumentException("P89_CONFLICTING_FINISH");
                    finish = reason;
                }
            }
            JSONObject delta = choice.optJSONObject("delta");
            if (delta == null) return;
            JSONArray fragments = delta.optJSONArray("tool_calls");
            if (fragments == null) return;
            for (int j = 0; j < fragments.length(); j++) {
                JSONObject item = fragments.optJSONObject(j);
                if (item == null || !item.has("index"))
                    throw new IllegalArgumentException("P89_MISSING_TOOL_INDEX");
                int index = item.getInt("index");
                if (index < 0 || index >= 16) throw new IllegalArgumentException("P89_TOOL_INDEX_LIMIT");
                String kind = item.optString("type", "function");
                if (!"function".equals(kind)) throw new IllegalArgumentException("P89_UNSUPPORTED_TOOL_TYPE");
                Partial p = calls.get(index);
                if (p == null) {p = new Partial();calls.put(index,p);}
                String id = item.optString("id", "");
                if (!id.isEmpty()) {
                    if (id.length() > 256 || (!p.id.isEmpty() && !p.id.equals(id)))
                        throw new IllegalArgumentException("P89_TOOL_ID_CONFLICT");
                    p.id = id;
                }
                JSONObject function = item.optJSONObject("function");
                if (function != null) {
                    String name = function.optString("name", "");
                    if (!name.isEmpty()) {
                        String current = p.name.toString();
                        if (!name.equals(current)) {
                            if (name.startsWith(current)) p.name.replace(0,p.name.length(),name);
                            else p.name.append(name);
                        }
                        if (p.name.length() > 256) throw new IllegalArgumentException("P89_TOOL_NAME_LIMIT");
                    }
                    String args = function.optString("arguments", "");
                    if (p.args.length() + args.length() > 262144)
                        throw new IllegalArgumentException("P89_TOOL_ARGS_LIMIT");
                    p.args.append(args);
                }
            }
        } catch (IllegalArgumentException bad) {
            throw bad;
        } catch (Exception malformed) {
            throw new IllegalArgumentException("P89_MALFORMED_TOOL_DELTA");
        }
    }

    /** Read only after explicit DONE. Validation is not authorization to execute. */
    public List<Call> verifiedToolCalls() {
        if (!done) throw new IllegalStateException("P89_NOT_DONE");
        if (calls.isEmpty()) return Collections.emptyList();
        if (!"tool_calls".equals(finish))
            throw new IllegalStateException("P89_TOOL_FINISH_NOT_CONFIRMED");
        List<Call> result = new ArrayList<>();
        for (Map.Entry<Integer,Partial> e : calls.entrySet()) {
            Partial p = e.getValue();
            String args = p.args.toString();
            if (p.id.isEmpty() || p.name.length() == 0 || args.isEmpty())
                throw new IllegalStateException("P89_INCOMPLETE_TOOL");
            try { new JSONObject(args); }
            catch (Exception malformed) {
                throw new IllegalArgumentException("P89_TOOL_ARGUMENTS_INVALID_JSON");
            }
            result.add(new Call(e.getKey(),p.id,p.name.toString(),args));
        }
        return Collections.unmodifiableList(result);
    }
    public boolean sawDone() {return done;}
    public int toolCount() {return calls.size();}
}
