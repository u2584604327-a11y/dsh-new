package com.dsh.android.p87;
import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import java.nio.charset.StandardCharsets;
/** Real Android TextView incremental update test. Generated fixture only. */
public final class P87AndroidUiProbe {
 private static final String TAG="P87_STREAM_UI";
 private P87AndroidUiProbe(){}
 private static void log(String value){Log.i(TAG,value);}
 private static void fail(String code){Log.e(TAG,"P87_STREAM_UI_"+code+"=FAIL");}
 private static void emit(P87SseDecoder d,String raw){
  byte[] b=raw.getBytes(StandardCharsets.UTF_8);
  for(int at=0;at<b.length;at+=3)d.accept(b,at,Math.min(3,b.length-at));
 }
 public static void run(Activity activity){
  if(!"com.dsh.p51.isolatedprobe".equals(activity.getPackageName())||
     Looper.myLooper()!=Looper.getMainLooper())
    throw new SecurityException("P87_ISOLATED_TEST_ACTIVITY_ONLY");
  final P87ChatStreamView ui=new P87ChatStreamView(activity);
  final long run=ui.begin();
  final Handler main=new Handler(Looper.getMainLooper());
  new Thread(()->{
   try{
    P87SseDecoder p=new P87SseDecoder(ev->ui.event(run,ev));
    emit(p,": keepalive\n\n"+
      "data: {\"choices\":[{\"delta\":{\"reasoning_content\":\"private\"}}]}\n\n");
    Thread.sleep(300);
    main.post(()->{
     if(ui.completed()||!ui.visibleText().isEmpty())fail("THINKING_EARLY_COMPLETE");
     else log("P87_THINKING_EVENT_NO_FAKE_DONE=PASS");
    });
    emit(p,"data: {\"choices\":[{\"delta\":{\"content\":\"你\"}}]}\n\n");
    Thread.sleep(220);
    main.post(()->{
     if(!"你".equals(ui.visibleText())||ui.completed()||ui.paints()<1)
      fail("FIRST_VISIBLE_DELTA_BEFORE_DONE");
     else log("P87_ANDROID_FIRST_CONTENT_PAINT_BEFORE_DONE=PASS");
    });
    Thread.sleep(110);
    emit(p,"data: {\"choices\":[{\"delta\":{\"content\":\"好🌊\"}}]}\n\n");
    Thread.sleep(230);
    emit(p,"data: [DONE]\n\n");
    if(!p.finishEof())throw new IllegalStateException("P87_MISSING_DONE");
    main.postDelayed(()->{
     if(!ui.completed()||ui.failed()||!"你好🌊".equals(ui.visibleText())||
        ui.paints()<2||ui.deltas()!=2||ui.reasoningEvents()!=1)
      fail("FINAL_UI_OR_RENDER_RATE");
     else {
      log("P87_ANDROID_MAIN_THREAD_INCREMENTAL_TEXTVIEW_TWO_PAINTS=PASS");
      log("P87_REASONING_NOT_RENDERED_AS_ANSWER=PASS");
      log("P87_ANDROID_SYNTHETIC_SSE_NO_ORIGINAL_DSH_NETWORK=YES");
     }
    },160);
   }catch(Exception e){fail("SYNTHETIC_SSE_READER");}
  },"p87-sse-producer").start();
 }
}
