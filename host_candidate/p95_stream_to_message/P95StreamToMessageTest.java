package com.dsh.android.p95;

import com.dsh.android.p87.P87SseDecoder;
import com.dsh.android.p89.P89ExistingStreamPump;
import com.dsh.android.p89.P89ToolCallAssembler;
import com.dsh.android.p93.P93TurnMessageState;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;

public final class P95StreamToMessageTest {
    private static void check(boolean ok, String why) {
        if (!ok) throw new AssertionError(why);
    }
    private static String line(JSONObject json) {return "data: " + json.toString() + "\n\n";}
    private static String done(){return "data: [DONE]\n\n";}
    private static JSONObject delta(JSONObject part,String finish) throws Exception {
        JSONObject choice=new JSONObject().put("index",0).put("delta",part);
        if (finish!=null) choice.put("finish_reason",finish);
        return new JSONObject().put("choices",new JSONArray().put(choice));
    }
    private static boolean run(String utf8,P95StreamToMessage consumer){
        return P89ExistingStreamPump.consume(
            new ByteArrayInputStream(utf8.getBytes(StandardCharsets.UTF_8)),consumer);
    }
    private static void plainText()throws Exception{
        List<P93TurnMessageState.Frame> frames=new ArrayList<>();
        P93TurnMessageState turn=new P93TurnMessageState("turn_p95_normal",1,frames::add);
        List<List<P89ToolCallAssembler.Call>> tools=new ArrayList<>();
        P95StreamToMessage observer=new P95StreamToMessage(turn,tools::add);
        String s=line(delta(new JSONObject().put("reasoning_content","reasoning"),null))
                 +line(delta(new JSONObject().put("content","你"),null))
                 +line(delta(new JSONObject().put("content","好"),"stop"))+done();
        check(run(s,observer),"normal SSE completed");
        check(frames.stream().anyMatch(f->f.phase==P93TurnMessageState.Phase.THINKING),
            "reasoning phase must be observable");
        check(frames.stream().anyMatch(f->"你".equals(f.content)&&!f.terminal),
            "first content must render before DONE");
        check(turn.snapshot().phase==P93TurnMessageState.Phase.COMPLETE,
            "normal stop is completed");
        check("你好".equals(turn.snapshot().content),"body never lost");
        check(tools.isEmpty(),"normal response does not invoke tools");
        System.out.println("P95_EXISTING_SSE_TO_MESSAGE_INCREMENTAL=PASS");
    }
    private static void toolCall()throws Exception{
        List<P93TurnMessageState.Frame> frames=new ArrayList<>();
        P93TurnMessageState turn=new P93TurnMessageState("turn_p95_tools01",2,frames::add);
        List<List<P89ToolCallAssembler.Call>> callbacks=new ArrayList<>();
        P95StreamToMessage observer=new P95StreamToMessage(turn,callbacks::add);
        JSONObject first=new JSONObject().put("tool_calls",new JSONArray().put(
            new JSONObject().put("index",0).put("id","call_p95_read")
                .put("type","function").put("function",new JSONObject()
                    .put("name","read_").put("arguments","{\"url\":\""))));
        JSONObject second=new JSONObject().put("tool_calls",new JSONArray().put(
            new JSONObject().put("index",0).put("function",new JSONObject()
                .put("name","page").put("arguments","https://example.com\"}"))));
        String s=line(delta(first,null))+line(delta(second,null))
                 +line(delta(new JSONObject(),"tool_calls"))+done();
        check(run(s,observer),"tool SSE completed");
        check(callbacks.size()==1,"tool callback exactly once");
        P89ToolCallAssembler.Call call=callbacks.get(0).get(0);
        check("call_p95_read".equals(call.id)&&"read_page".equals(call.name),
            "fragmented id/name correctly assembled");
        check("https://example.com".equals(new JSONObject(call.arguments).getString("url")),
            "tool JSON arguments assembled");
        check(turn.snapshot().phase==P93TurnMessageState.Phase.AWAITING_TOOL_RESULT,
            "tool stream must not be marked model-task complete");
        check(turn.snapshot().toolFragments==2,"tool fragments are not normal text");
        check(turn.snapshot().content.isEmpty(),"tool metadata is not displayed as assistant content");
        System.out.println("P95_TOOL_STREAM_DONE_AWAITS_ORIGINAL_BROKER=PASS");
    }
    private static void prematureEof()throws Exception{
        P93TurnMessageState turn=new P93TurnMessageState("turn_p95_short01",3,f->{});
        check(!run(line(delta(new JSONObject().put("content","partial"),null)),
                 new P95StreamToMessage(turn,x->{})),"missing DONE fail");
        check(turn.snapshot().phase==P93TurnMessageState.Phase.TRUNCATED &&
              "partial".equals(turn.snapshot().content),"truncate preserves partial content");
        System.out.println("P95_EOF_PRESERVES_PARTIAL_AND_FAILS_CLOSED=PASS");
    }
    private static void badToolHandoff()throws Exception{
        P93TurnMessageState turn=new P93TurnMessageState("turn_p95_fail01",4,f->{});
        final int[] attempts={0};
        P95StreamToMessage observer=new P95StreamToMessage(turn,calls->{
           attempts[0]++;throw new IllegalStateException("BROKER_NOT_CONNECTED");
        });
        JSONObject only=new JSONObject().put("tool_calls",new JSONArray().put(
            new JSONObject().put("index",0).put("id","call_p95_fail")
                .put("function",new JSONObject().put("name","read")
                    .put("arguments","{}"))));
        String input=line(delta(only,"tool_calls"))+done();
        check(!run(input,observer),"unwired tool broker must fail closed");
        check(attempts[0]==1&&turn.snapshot().phase==P93TurnMessageState.Phase.FAILED,
            "callback failure must not misreport waiting");
        System.out.println("P95_TOOL_CALLBACK_FAILURE_NOT_AWAITING=PASS");
    }
    private static void noFalseCompletion()throws Exception{
        P93TurnMessageState empty=new P93TurnMessageState("turn_p95_empty01",5,f->{});
        String zero=line(delta(new JSONObject().put("role","assistant"),"stop"))+done();
        check(!run(zero,new P95StreamToMessage(empty,x->{})),"empty done is not a response");
        check(empty.snapshot().phase==P93TurnMessageState.Phase.FAILED,
            "empty native role/stop/DONE must fail, never display completed");
        P93TurnMessageState length=new P93TurnMessageState("turn_p95_length",6,f->{});
        String partial=line(delta(new JSONObject().put("content","已有回答"),"length"))+done();
        check(!run(partial,new P95StreamToMessage(length,x->{})),"length finish incomplete");
        check(length.snapshot().phase==P93TurnMessageState.Phase.TRUNCATED &&
             "已有回答".equals(length.snapshot().content),
             "length cap must retain partial text without false complete");
        P93TurnMessageState noTool=new P93TurnMessageState("turn_p95_notool",7,f->{});
        check(!run(line(delta(new JSONObject(),"tool_calls"))+done(),
             new P95StreamToMessage(noTool,x->{})),"orphan tool finish cannot succeed");
        check(noTool.snapshot().phase==P93TurnMessageState.Phase.FAILED,
            "tool finish without tool payload is malformed");
        P93TurnMessageState filtered=new P93TurnMessageState("turn_p95_filter",8,f->{});
        check(!run(line(delta(new JSONObject(),"content_filter"))+done(),
             new P95StreamToMessage(filtered,x->{})),"content filtered is not success");
        check(filtered.snapshot().phase==P93TurnMessageState.Phase.FAILED,
            "content-filter sentinel fails closed");
        System.out.println("P95_EMPTY_STOP_AND_LENGTH_DO_NOT_COMPLETE=PASS");
        System.out.println("P95_MALFORMED_TOOL_OR_FILTER_FINISH_FAIL_CLOSED=PASS");
    }
    public static void main(String[] args)throws Exception{
        plainText();toolCall();prematureEof();badToolHandoff();noFalseCompletion();
    }
}
