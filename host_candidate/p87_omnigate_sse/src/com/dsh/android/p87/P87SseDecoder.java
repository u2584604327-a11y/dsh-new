package com.dsh.android.p87;
import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.*;
public final class P87SseDecoder {
 public interface Listener {void onEvent(Event value);}
 public static final class Event {
  public final String data,event,id;public final boolean done;
  Event(String d,String e,String i,boolean end){data=d;event=e;id=i;done=end;}
 }
 private static final int MAX_LINE=131072,MAX_EVENT=262144;
 private final Listener listener;
 private final ByteArrayOutputStream line=new ByteArrayOutputStream();
 private final StringBuilder data=new StringBuilder();
 private String event="",lastId="";
 private boolean hasData,afterCr,done,closed;
 private int count;
 public P87SseDecoder(Listener l){if(l==null)throw new IllegalArgumentException();listener=l;}
 public void accept(byte[] bytes,int offset,int length){
  if(closed)throw new IllegalStateException("P87_CLOSED_OR_DONE");
  if(bytes==null||offset<0||length<0||offset>bytes.length-length)
   throw new IllegalArgumentException("P87_BOUNDS");
  for(int j=offset;j<offset+length;j++){
   int c=bytes[j]&255;
   // CRLF/blank-line suffix may straddle reads AFTER the [DONE] event.
   // Only framing whitespace is allowed, never a fresh event.
   if(done){
    if(c!=10&&c!=13)throw new IllegalStateException("P87_DATA_AFTER_DONE");
    continue;
   }
   if(afterCr){afterCr=false;if(c==10)continue;}
   if(c==10||c==13){endLine();if(c==13)afterCr=true;}
   else{if(line.size()>=MAX_LINE)throw new IllegalStateException("P87_LINE_LIMIT");line.write(c);}
  }
 }
 private static String decode(byte[] value){
  try{return StandardCharsets.UTF_8.newDecoder()
   .onMalformedInput(CodingErrorAction.REPORT)
   .onUnmappableCharacter(CodingErrorAction.REPORT)
   .decode(ByteBuffer.wrap(value)).toString();
  }catch(CharacterCodingException e){throw new IllegalArgumentException("P87_MALFORMED_UTF8");}
 }
 private void endLine(){
  String raw=decode(line.toByteArray());line.reset();
  if(raw.isEmpty()){dispatch();return;}
  if(raw.startsWith(":"))return;
  int at=raw.indexOf(':');
  String name=at<0?raw:raw.substring(0,at);
  String value=at<0?"":raw.substring(at+1);
  if(value.startsWith(" "))value=value.substring(1);
  switch(name){
   case "data":
    if(data.length()+value.length()+1>MAX_EVENT)
     throw new IllegalStateException("P87_EVENT_LIMIT");
    if(hasData)data.append('\n');
    data.append(value);hasData=true;break;
   case "event":event=value;break;
   case "id":if(value.indexOf('\0')<0&&value.length()<=256)lastId=value;break;
   default:break;
  }
 }
 private void dispatch(){
  if(!hasData){event="";return;}
  if(++count>100000)throw new IllegalStateException("P87_EVENT_COUNT");
  String value=data.toString();data.setLength(0);hasData=false;
  done="[DONE]".equals(value);
  listener.onEvent(new Event(value,event,lastId,done));event="";
 }
 public boolean finishEof(){
  if(closed)throw new IllegalStateException("P87_DOUBLE_EOF");
  if(line.size()>0)endLine();
  dispatch();closed=true;return done;
 }
 public int eventCount(){return count;}
 public boolean sawDone(){return done;}
}
