package com.dsh.android.p93;
import android.os.Handler;
import android.os.Looper;

/** No setContentView, no synthetic chat panel: snapshots are delivered to the
 * existing original DSH chat store adapter on the Android main thread.
 */
public final class P93MainThreadPatchDispatcher implements P93TurnMessageState.Sink {
    public interface OriginalStorePatch {
        void apply(P93TurnMessageState.Frame immutableSnapshot);
    }
    private final Handler main=new Handler(Looper.getMainLooper());
    private final OriginalStorePatch store;
    private long generation=-1,shownRevision=-1;
    private String turnId="";
    private boolean firstTextShown,scheduled;
    private P93TurnMessageState.Frame pending;
    public P93MainThreadPatchDispatcher(OriginalStorePatch realStore){
        if(realStore==null)throw new IllegalArgumentException("P93_MISSING_REAL_STORE_ADAPTER");
        store=realStore;
    }
    @Override public void accept(P93TurnMessageState.Frame state){
        synchronized(this){
            if(generation!=-1 && state.generation<generation)return;
            if(generation!=state.generation || !turnId.equals(state.turnId)){
                generation=state.generation;
                turnId=state.turnId;
                shownRevision=-1;
                firstTextShown=false;scheduled=false;pending=null;
            }
            if(state.revision<=shownRevision)return;
            pending=state;
            boolean paintFirst=!state.content.isEmpty()&&!firstTextShown;
            if(paintFirst)firstTextShown=true;
            if(paintFirst || state.terminal){
                main.post(this::flush);
            }else if(!scheduled){
                scheduled=true;
                main.postDelayed(this::flush,48);
            }
        }
    }
    private void flush(){
        P93TurnMessageState.Frame latest;
        synchronized(this){
            latest=pending;pending=null;scheduled=false;
            if(latest==null || latest.generation!=generation ||
               !latest.turnId.equals(turnId) || latest.revision<=shownRevision)return;
            shownRevision=latest.revision;
        }
        store.apply(latest);
    }
}
