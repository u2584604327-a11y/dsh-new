package com.dsh.android.p87;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
/** Actual loopback HTTP/1.1 chunked SSE streamed through an InputStream. */
public final class P87HttpStreamingTest {
 private static byte[] text(String s){return s.getBytes(StandardCharsets.UTF_8);}
 private static void chunk(OutputStream out,String payload)throws Exception{
  byte[] b=text(payload);
  out.write(text(Integer.toHexString(b.length)+"\r\n"));
  out.write(b);out.write(text("\r\n"));out.flush();
 }
 public static void main(String[] ignored)throws Exception{
  ServerSocket listener=new ServerSocket(0,1,InetAddress.getByName("127.0.0.1"));
  AtomicLong serverEnded=new AtomicLong(0);
  Thread server=new Thread(()->{
   try(Socket client=listener.accept()){
    OutputStream out=client.getOutputStream();
    out.write(text("HTTP/1.1 200 OK\r\nContent-Type: text/event-stream; charset=utf-8\r\n"+
      "Transfer-Encoding: chunked\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n"));
    out.flush();
    chunk(out,": thinking heartbeat\n\n");
    Thread.sleep(120);
    chunk(out,"data: {\"choices\":[{\"delta\":{\"reasoning_content\":\"hidden reasoning\"}}]}\n\n");
    Thread.sleep(120);
    chunk(out,"data: {\"choices\":[{\"delta\":{\"content\":\"你\"}}]}\n\n");
    Thread.sleep(120);
    chunk(out,"data: {\"choices\":[{\"delta\":{\"content\":\"好🌊\"}}]}\n\n");
    Thread.sleep(120);
    chunk(out,"data: [DONE]\n\n");
    out.write(text("0\r\n\r\n"));out.flush();
    serverEnded.set(System.nanoTime());
   }catch(Exception e){serverEnded.set(-1);}
  });
  server.start();
  HttpURLConnection con=(HttpURLConnection)new URL("http://127.0.0.1:"+listener.getLocalPort()+"/v1/chat/completions").openConnection();
  con.setConnectTimeout(3000);con.setReadTimeout(6000);
  con.setRequestProperty("Accept","text/event-stream");
  if(con.getResponseCode()!=200)throw new AssertionError("http 200");
  if(!con.getContentType().toLowerCase().startsWith("text/event-stream"))
   throw new AssertionError("SSE media type");
  List<String> events=new ArrayList<>();
  List<Long> timings=new ArrayList<>();
  P87SseDecoder decoder=new P87SseDecoder(event->{
   events.add(event.data);timings.add(System.nanoTime());
  });
  byte[] buf=new byte[7];
  try(InputStream in=con.getInputStream()){
   int n;
   while((n=in.read(buf))!=-1)decoder.accept(buf,0,n);
  }
  boolean completed=decoder.finishEof();
  server.join(4000);listener.close();con.disconnect();
  if(!completed||events.size()!=4)throw new AssertionError("SSE count/terminal");
  if(!events.get(1).contains("你")||!events.get(2).contains("好🌊"))
   throw new AssertionError("UTF8 split over HTTP");
  if(serverEnded.get()<=0||timings.get(1)>=serverEnded.get())
   throw new AssertionError("first user-visible text was buffered until EOF");
  if(timings.get(2)<=timings.get(1))
   throw new AssertionError("second event never streamed later");
  System.out.println("P87_HTTP_CHUNKED_SSE_REAL_INPUTSTREAM_INCREMENTAL=PASS");
  System.out.println("P87_FIRST_CONTENT_BEFORE_UPSTREAM_EOF=PASS");
  System.out.println("P87_REDUCES_UI_BATCHING_RISK_BUT_ORIGINAL_DSH_NOT_WIRED=YES");
 }
}
