package com.dsh.android.p89;

import com.dsh.android.p87.P87SseDecoder;
import java.io.IOException;
import java.io.InputStream;

/** Reads an already-owned HTTP response body; never opens, closes or retries a connection. */
public final class P89ExistingStreamPump {
    public interface Observer {
        void onEvent(P87SseDecoder.Event event);
        void onTerminal(boolean explicitDone, String reason);
    }
    private static final int MAX_BYTES = 16 * 1024 * 1024;
    private P89ExistingStreamPump() {}

    public static boolean isSseContentType(String header) {
        if (header == null) return false;
        return "text/event-stream".equalsIgnoreCase(header.split(";", 2)[0].trim());
    }

    /** Invoke on the existing network response reader thread, never the UI thread. */
    public static boolean consume(InputStream body, Observer observer) {
        if (body == null || observer == null) throw new IllegalArgumentException("P89_NULL_ARGUMENT");
        P87SseDecoder decoder = new P87SseDecoder(observer::onEvent);
        byte[] buffer = new byte[4096];
        int total = 0, emptyReads = 0;
        String failure = "MISSING_EXPLICIT_DONE";
        boolean done = false;
        try {
            int len;
            while (!decoder.sawDone() && (len = body.read(buffer)) != -1) {
                if (len == 0) {
                    if (++emptyReads > 128) throw new IOException("ZERO_PROGRESS_READS");
                    continue;
                }
                emptyReads = 0;
                if (len > MAX_BYTES - total) throw new IOException("RESPONSE_BYTE_LIMIT");
                total += len;
                decoder.accept(buffer, 0, len);
            }
            done = decoder.finishEof();
            if (done) failure = "NONE";
        } catch (IOException ex) {
            failure = "INPUT_STREAM_FAILED";
        } catch (RuntimeException ex) {
            failure = "SSE_PARSE_OR_CONSUMER_FAILED";
        } finally {
            observer.onTerminal(done, failure);
        }
        return done;
    }
}
