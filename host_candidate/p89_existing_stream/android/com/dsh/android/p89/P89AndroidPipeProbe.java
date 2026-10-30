package com.dsh.android.p89;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.os.ParcelFileDescriptor;
import android.util.Log;
import com.dsh.android.p87.P87ChatStreamView;
import com.dsh.android.p87.P87SseDecoder;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Test-only: real Android pipe read -> SSE decoder -> UI updates before producer closes. */
public final class P89AndroidPipeProbe {
    private static final String TAG = "P89_ANDROID_PIPE";
    private P89AndroidPipeProbe() {}
    private static void pass(String code) { Log.i(TAG,"P89_"+code+"=PASS"); }
    private static void fail(String code) { Log.e(TAG,"P89_"+code+"=FAIL"); }

    private static String event(JSONObject delta,String reason) throws Exception {
        JSONObject choice = new JSONObject()
            .put("delta",delta)
            .put("finish_reason",reason==null?JSONObject.NULL:reason);
        return "data: " + new JSONObject()
            .put("choices",new JSONArray().put(choice)).toString() + "\n\n";
    }
    private static void send(OutputStream out,String wire) throws Exception {
        byte[] bytes = wire.getBytes(StandardCharsets.UTF_8);
        for(int pos=0;pos<bytes.length;pos+=3) {
            out.write(bytes,pos,Math.min(3,bytes.length-pos));
            out.flush();
        }
    }
    private static JSONObject tool(String name,String arguments,boolean first) throws Exception {
        JSONObject function = new JSONObject().put("name",name).put("arguments",arguments);
        JSONObject call = new JSONObject().put("index",0).put("function",function);
        if(first)call.put("id","call_fixture").put("type","function");
        return new JSONObject().put("tool_calls",new JSONArray().put(call));
    }
    public static void run(Activity activity) {
        if(!"com.dsh.p51.isolatedprobe".equals(activity.getPackageName()) ||
           Looper.myLooper()!=Looper.getMainLooper())
            throw new SecurityException("P89_DISPOSABLE_ACTIVITY_ONLY");
        P87ChatStreamView view = new P87ChatStreamView(activity);
        long generation = view.begin();
        Handler main = new Handler(Looper.getMainLooper());
        AtomicBoolean terminated = new AtomicBoolean();
        AtomicBoolean completed = new AtomicBoolean();
        AtomicReference<List<P89ToolCallAssembler.Call>> verified = new AtomicReference<>();
        final ParcelFileDescriptor[] pipe;
        try { pipe=ParcelFileDescriptor.createPipe(); }
        catch(Exception err) {fail("PIPE_CREATION");return;}
        new Thread(()->{
            P89ToolCallAssembler calls = new P89ToolCallAssembler();
            try(InputStream in=new ParcelFileDescriptor.AutoCloseInputStream(pipe[0])) {
                P89ExistingStreamPump.consume(in,new P89ExistingStreamPump.Observer(){
                    @Override public void onEvent(P87SseDecoder.Event item) {
                        calls.accept(item);
                        if(item.done)verified.set(calls.verifiedToolCalls());
                        view.event(generation,item);
                    }
                    @Override public void onTerminal(boolean done,String reason) {
                        completed.set(done);
                        terminated.set(true);
                        if(!done)view.truncated(generation);
                    }
                });
            }catch(Exception err){terminated.set(true);view.truncated(generation);}
        },"p89-existing-body-reader").start();
        new Thread(()->{
            try(OutputStream out=new ParcelFileDescriptor.AutoCloseOutputStream(pipe[1])) {
                send(out,": heartbeat\r\n\r\n");
                send(out,event(new JSONObject().put("reasoning_content","private thought"),null));
                Thread.sleep(240);
                send(out,event(new JSONObject().put("content","你"),null));
                Thread.sleep(420);
                send(out,event(new JSONObject().put("content","好🌊"),null));
                Thread.sleep(190);
                send(out,event(tool("get_","{\"q\":",true),null));
                Thread.sleep(130);
                send(out,event(tool("page","\"hi\"}",false),null));
                Thread.sleep(130);
                send(out,event(new JSONObject(),"tool_calls"));
                Thread.sleep(130);
                send(out,"data: [DONE]\n\n");
            }catch(Exception err){fail("PIPE_WRITER");}
        },"p89-fixture-SSE-fragments").start();
        main.postDelayed(()->{
            if(view.completed() || terminated.get() || !"你".equals(view.visibleText()) || view.paints()<1)
                fail("FIRST_ANDROID_PAINT_WHILE_PIPE_OPEN");
            else pass("FIRST_ANDROID_PAINT_WHILE_PIPE_OPEN");
        },490);
        main.postDelayed(()->{
            List<P89ToolCallAssembler.Call> assembled=verified.get();
            if(!terminated.get() || !completed.get() || !view.completed() || view.failed() ||
               !"你好🌊".equals(view.visibleText()) || view.paints()<2 ||
               view.reasoningEvents()!=1 || assembled==null || assembled.size()!=1 ||
               !"call_fixture".equals(assembled.get(0).id) ||
               !"get_page".equals(assembled.get(0).name) ||
               !"{\"q\":\"hi\"}".equals(assembled.get(0).arguments)) {
                fail("FINAL_INCREMENTAL_TEXT_AND_TOOL_FRAGMENT_REASSEMBLY");
            }else{
                pass("FINAL_INCREMENTAL_TEXT_AND_TOOL_FRAGMENT_REASSEMBLY");
                pass("REASONING_SEPARATE_TOOL_NOT_EXECUTED");
                Log.i(TAG,"P89_DISPOSABLE_PIPE_NOT_ORIGINAL_DSH_NETWORK=YES");
            }
        },1900);
    }
}
