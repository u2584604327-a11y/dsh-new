package com.dsh.android.p87;
import java.nio.charset.StandardCharsets;
import java.util.*;
public final class P87SseDecoderTest {
 static int n;
 static void check(boolean v,String s){n++;if(!v)throw new AssertionError(s);}
 static void feed(P87SseDecoder p,String s,int chunk){
  byte[] b=s.getBytes(StandardCharsets.UTF_8);
  for(int i=0;i<b.length;i+=chunk)p.accept(b,i,Math.min(chunk,b.length-i));
 }
 public static void main(String[] a){
  List<P87SseDecoder.Event> seen=new ArrayList<>();
  P87SseDecoder p=new P87SseDecoder(seen::add);
  feed(p,": heartbeat\r\nid:abc\r\ndata: {\"delta\":\"你\"}\r\n\r\n"
         +"data: {\"delta\":\"好🌊\"}\n\n"
         +"data: [DONE]\r\n\r\n",1);
  check(seen.size()==3,"3 events");
  check(seen.get(0).data.contains("你"),"UTF8 CJK");
  check(seen.get(1).data.contains("好🌊"),"UTF8 split emoji");
  check(seen.get(2).done,"terminal explicit");
  check(p.finishEof(),"DONE true");
  seen.clear();P87SseDecoder unfinished=new P87SseDecoder(seen::add);
  feed(unfinished,"data: partial\n\n",2);
  check(seen.size()==1,"event before EOF");
  check(!unfinished.finishEof(),"no DONE if EOF only");
  seen.clear();P87SseDecoder multi=new P87SseDecoder(seen::add);
  feed(multi,"event: token\ndata: one\ndata: two\n\n",3);
  check(seen.size()==1&&seen.get(0).data.equals("one\ntwo"),"multiline");
  check(seen.get(0).event.equals("token"),"event label");
  check(!multi.finishEof(),"no invented DONE");
  boolean fail=false;
  try{new P87SseDecoder(e->{}).accept(new byte[]{(byte)0xff,10},0,2);}
  catch(IllegalArgumentException e){fail=true;}
  check(fail,"invalid UTF8 fail closed");
  fail=false;
  try{P87SseDecoder huge=new P87SseDecoder(e->{});
      byte[] bytes=new byte[131073];Arrays.fill(bytes,(byte)'x');
      huge.accept(bytes,0,bytes.length);
  }catch(IllegalStateException e){fail=true;}
  check(fail,"oversize line rejected");
  System.out.println("P87_UTF8_SSE_INCREMENTAL_EVENTS_DONE_BOUNDS=PASS assertions="+n);
  System.out.println("P87_EOF_WITHOUT_DONE_IS_TRUNCATED=PASS");
 }
}
