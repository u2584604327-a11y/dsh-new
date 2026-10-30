package com.dsh.android.p93;

/** Mutable stream state for ONE original-chat turn. Does not create or replace an Activity.
 * The real original DSH message store must be connected by a later source-locked adapter.
 */
public final class P93TurnMessageState {
    public interface Sink {void accept(Frame frame);}
    public enum Phase { WAITING, THINKING, STREAMING, TOOLS, AWAITING_TOOL_RESULT, COMPLETE, TRUNCATED, FAILED }
    public static final class Frame {
        public final String turnId, content;
        public final long generation, revision;
        public final Phase phase;
        public final int reasoningEvents, toolFragments;
        public final boolean terminal;
        private Frame(String id,String text,long generation,long revision,Phase phase,
                      int reasoningEvents,int toolFragments,boolean terminal) {
            this.turnId=id;this.content=text;this.generation=generation;this.revision=revision;
            this.phase=phase;this.reasoningEvents=reasoningEvents;
            this.toolFragments=toolFragments;this.terminal=terminal;
        }
    }
    private static final int MAX_CONTENT=600000;
    private final Sink sink;
    private final String turnId;
    private final long generation;
    private final StringBuilder body=new StringBuilder();
    private Phase phase=Phase.WAITING;
    private long revision;
    private int reasoningEvents,toolFragments;
    private boolean terminal;

    public P93TurnMessageState(String id,long generation,Sink sink) {
        if(id==null||!id.matches("[A-Za-z0-9_-]{8,128}")||generation<1||sink==null)
            throw new IllegalArgumentException("P93_INVALID_TURN");
        this.turnId=id;this.generation=generation;this.sink=sink;
        emit();
    }
    private synchronized Frame frame(){
        return new Frame(turnId,body.toString(),generation,revision,phase,
                         reasoningEvents,toolFragments,terminal);
    }
    private void emit(){sink.accept(frame());}
    public void reasoning() {
        synchronized(this){
            if(terminal)throw new IllegalStateException("P93_ALREADY_TERMINAL");
            reasoningEvents++;if(body.length()==0)phase=Phase.THINKING;
            revision++;
        }
        emit();
    }
    public void content(String fragment) {
        if(fragment==null)throw new IllegalArgumentException("P93_NULL_CONTENT");
        if(fragment.isEmpty())return;
        synchronized(this){
            if(terminal)throw new IllegalStateException("P93_ALREADY_TERMINAL");
            if(fragment.length()>MAX_CONTENT-body.length()){
                phase=Phase.FAILED;terminal=true;revision++;
            } else {
                body.append(fragment);phase=Phase.STREAMING;revision++;
            }
        }
        emit();
    }
    /** Tool-call frames are state, never plain assistant text or tool authorization. */
    public void tools(int count){
        if(count<1||count>16)throw new IllegalArgumentException("P93_INVALID_TOOL_COUNT");
        synchronized(this){
            if(terminal)throw new IllegalStateException("P93_ALREADY_TERMINAL");
            toolFragments+=count;if(toolFragments>100000)
                throw new IllegalStateException("P93_TOOL_FRAGMENT_LIMIT");
            phase=Phase.TOOLS;revision++;
        }
        emit();
    }
    public void done(){
        synchronized(this){
            if(terminal)throw new IllegalStateException("P93_ALREADY_TERMINAL");
            terminal=true;phase=Phase.COMPLETE;revision++;
        }
        emit();
    }
    /** A completed SSE tool_call stream is NOT a completed original model task.
     * The tool result must return through the original authenticated dispatcher.
     */
    public void awaitingToolResult(){
        synchronized(this){
            if(terminal)throw new IllegalStateException("P93_ALREADY_TERMINAL");
            if(toolFragments<1)throw new IllegalStateException("P95_TOOL_FRAGMENTS_NOT_OBSERVED");
            terminal=true;phase=Phase.AWAITING_TOOL_RESULT;revision++;
        }
        emit();
    }
    /** EOF without explicit SSE [DONE] must not look like natural completion. */
    public void closedWithoutDone(){
        synchronized(this){
            if(terminal)return;
            terminal=true;phase=Phase.TRUNCATED;revision++;
        }
        emit();
    }
    public void failure(){
        synchronized(this){
            if(terminal)return;
            terminal=true;phase=Phase.FAILED;revision++;
        }
        emit();
    }
    public synchronized Frame snapshot(){return frame();}
}
