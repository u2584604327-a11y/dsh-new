package com.dsh.android.p87;
import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.graphics.Color;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
/** UI adapter: streaming delta first paints immediately; later paints coalesced <=50ms.
 * Must be driven by the original network reader before production acceptance.
 */
public final class P87ChatStreamView {
 private final Handler main=new Handler(Looper.getMainLooper());
 private final TextView body,phase;
 private final StringBuilder visible=new StringBuilder();
 private long generation;
 private boolean scheduled,done,errored;
 private int actualPaints,deltaCount,reasonCount,toolCount;
 public P87ChatStreamView(Activity a){
  if(Looper.myLooper()!=Looper.getMainLooper())throw new IllegalStateException("UI_THREAD");
  LinearLayout layout=new LinearLayout(a);
  layout.setOrientation(LinearLayout.VERTICAL);
  layout.setPadding(28,32,28,20);
  layout.setBackgroundColor(Color.rgb(17,22,34));
  phase=new TextView(a);phase.setTextColor(Color.rgb(148,163,184));phase.setTextSize(14);
  body=new TextView(a);body.setTextColor(Color.WHITE);body.setTextSize(17);
  ScrollView scroll=new ScrollView(a);scroll.addView(body);
  layout.addView(phase);layout.addView(scroll);
  a.setContentView(layout);
  begin();
 }
 public synchronized long begin(){
  long id=++generation;visible.setLength(0);
  scheduled=false;done=false;errored=false;actualPaints=0;deltaCount=0;reasonCount=0;toolCount=0;
  main.post(()->{body.setText("");phase.setText("正在等待首段内容…");});
  return id;
 }
 public void event(long id,P87SseDecoder.Event message){
  P87OpenAiDelta delta=P87OpenAiDelta.parse(message);
  main.post(()->apply(id,delta));
 }
 private void apply(long id,P87OpenAiDelta delta){
  if(id!=generation || done || errored)return;
  if(delta.error){
   errored=true;phase.setText("流式格式错误，不能认定生成成功");return;
  }
  if(!delta.reasoning.isEmpty()){
   reasonCount++;
   phase.setText("正在思考…");
  }
  if(delta.toolFragments>0){
   toolCount+=delta.toolFragments;
   phase.setText("正在处理工具调用…");
  }
  if(!delta.content.isEmpty()){
   boolean first=deltaCount==0;
   visible.append(delta.content);deltaCount++;
   if(visible.length()>600000){
    errored=true;phase.setText("单次响应超过显示限制");return;
   }
   if(first)render(); else if(!scheduled){
    scheduled=true;
    main.postDelayed(()->{
     if(id!=generation || errored)return;
     scheduled=false;render();
    },48);
   }
  }
  if(delta.done){
   done=true;render();phase.setText("已完成");
  }else if(!delta.finishReason.isEmpty()){
   phase.setText("正在完成响应…");
  }
 }
 private void render(){
  body.setText(visible.toString());
  actualPaints++;
 }
 public synchronized void truncated(long id){
  main.post(()->{
   if(id==generation&&!done){
    errored=true;phase.setText("连接提前结束，保留已收到的内容");
   }
  });
 }
 public synchronized String visibleText(){return visible.toString();}
 public synchronized int paints(){return actualPaints;}
 public synchronized int deltas(){return deltaCount;}
 public synchronized int reasoningEvents(){return reasonCount;}
 public synchronized boolean completed(){return done;}
 public synchronized boolean failed(){return errored;}
}
