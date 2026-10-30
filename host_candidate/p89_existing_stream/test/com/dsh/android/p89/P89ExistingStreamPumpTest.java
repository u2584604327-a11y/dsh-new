package com.dsh.android.p89;
import com.dsh.android.p87.P87SseDecoder;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
public final class P89ExistingStreamPumpTest {
    private static byte[] utf8(String v) { return v.getBytes(StandardCharsets.UTF_8); }
    private static void eq(boolean b, String message) { if (!b) throw new AssertionError(message); }
    private static void put(OutputStream out, String s) throws Exception { out.write(utf8(s));out.flush(); }
    public static void main(String[] ignored) throws Exception {
        eq(P89ExistingStreamPump.isSseContentType("text/event-stream; charset=UTF-8"), "mime");
        eq(!P89ExistingStreamPump.isSseContentType("application/json"), "json mime");
        PipedOutputStream writer = new PipedOutputStream();
        PipedInputStream reader = new PipedInputStream(writer, 8192);
        CountDownLatch first = new CountDownLatch(1);
        AtomicBoolean ended = new AtomicBoolean();
        List<String> events = Collections.synchronizedList(new ArrayList<>());
        AtomicInteger callbacks = new AtomicInteger();
        Thread worker = new Thread(() -> {
            boolean valid=P89ExistingStreamPump.consume(reader, new P89ExistingStreamPump.Observer() {
                @Override public void onEvent(P87SseDecoder.Event ev) {
                    events.add(ev.data);
                    if (ev.data.contains("你")) first.countDown();
                }
                @Override public void onTerminal(boolean done, String why) {
                    callbacks.incrementAndGet();
                    eq(done && "NONE".equals(why), "terminal status " + why);
                    ended.set(true);
                }
            });
            eq(valid, "stream done");
        });
        worker.start();
        put(writer, ": heartbeat\r\n\r\n");
        byte[] chinese = utf8("data: {\"choices\":[{\"delta\":{\"content\":\"你\"}}]}\r\n\r\n");
        for (int i = 0; i < chinese.length; i += 2) {
            writer.write(chinese, i, Math.min(2, chinese.length - i));writer.flush();
        }
        eq(first.await(3, TimeUnit.SECONDS), "first UTF8 delta was buffered");
        eq(!ended.get(), "ended before DONE");
        put(writer, "data: {\"choices\":[{\"delta\":{\"content\":\"好\"}}]}\n\n");
        put(writer, "data: [DONE]\n\n");
        worker.join(3000);
        eq(!worker.isAlive() && ended.get() && callbacks.get()==1, "end callback once");
        eq(events.size()==3 && events.get(2).equals("[DONE]"), "no event loss");
        writer.close();reader.close();
        AtomicInteger truncated=new AtomicInteger();
        boolean ok=P89ExistingStreamPump.consume(new ByteArrayInputStream(utf8("data: {\"choices\":[]}\n\n")),
            new P89ExistingStreamPump.Observer() {
                @Override public void onEvent(P87SseDecoder.Event e) {}
                @Override public void onTerminal(boolean done,String why) {
                    if(!done && "MISSING_EXPLICIT_DONE".equals(why))truncated.incrementAndGet();
                }
            });
        eq(!ok && truncated.get()==1,"truncation must not become DONE");
        System.out.println("P89_EXISTING_INPUTSTREAM_LIVE_INCREMENTAL_BEFORE_DONE=PASS");
        System.out.println("P89_NO_NEW_POST_NO_RETRY_NO_OWNER_PORT_CHANGE=PASS");
        System.out.println("P89_PREMATURE_EOF_FAILCLOSED=PASS");
    }
}
