package com.dsh.android.p85;
import android.app.Activity;
import android.util.Log;
import org.json.JSONObject;

/** Independent Android process-lifetime test, no public site or login. */
public final class P85RestartProbe {
  private static final String LOG="P85_RESTART";
  private static final String RUNNING="p85-unsettled-01";
  private static final String COMPLETED="p85-settled-01";
  private P85RestartProbe(){}
  private static void good(String code){Log.i(LOG,code+"=PASS");}
  public static void run(Activity host,String mode){
    if(host==null||!"com.dsh.p51.isolatedprobe".equals(host.getPackageName()))
      throw new SecurityException("P85_ISOLATED_TEST_ONLY");
    try {
      P85DurableReplyJournal journal=new P85DurableReplyJournal(host);
      if("seed".equals(mode)){
        if(!journal.begin(RUNNING)||!journal.begin(COMPLETED))
          throw new IllegalStateException("SEED_NOT_FRESH");
        JSONObject completed=new JSONObject();
        completed.put("id",COMPLETED);completed.put("ok",true);
        completed.put("code","OK");completed.put("outcomeUnknown",false);
        completed.put("retrySafe",false);
        journal.finish(COMPLETED,completed);
        good("P85_REAL_ANDROID_PRE_FORCESTOP_DURABLE_START_AND_TERMINAL");
      }else if("recover".equals(mode)){
        JSONObject unknown=journal.replayOrUnknown(RUNNING);
        if(unknown==null||unknown.optBoolean("ok",true)||
           !P85DurableReplyJournal.UNKNOWN.equals(unknown.optString("code"))||
           !unknown.optBoolean("outcomeUnknown",false)||
           unknown.optBoolean("retrySafe",true)||journal.begin(RUNNING))
          throw new IllegalStateException("INTERRUPTED_REQUEST_NOT_FAIL_CLOSED");
        good("P85_ANDROID_PROCESS_RESTART_INFLIGHT_UNKNOWN_NO_REPLAY");
        JSONObject same=journal.replayOrUnknown(COMPLETED);
        if(same==null||!same.optBoolean("ok",false)||
           !COMPLETED.equals(same.optString("id"))||
           !"OK".equals(same.optString("code"))||journal.begin(COMPLETED))
          throw new IllegalStateException("COMMITTED_REPLY_NOT_RESTORED");
        good("P85_ANDROID_PROCESS_RESTART_COMMITTED_REPLY_RECOVERED");
        boolean denied=false;
        try{journal.begin("../unsafe");}catch(SecurityException expected){denied=true;}
        if(!denied)throw new IllegalStateException("PATH_INJECTION");
        good("P85_INVALID_REQUEST_ID_REJECTED");
        good("P85_REAL_ANDROID_FORCESTOP_DURABLE_TOOL_OUTCOMES");
        Log.i(LOG,"P85_PUBLIC_COMMENT_POSTED=NO");
      }else throw new IllegalArgumentException("UNKNOWN_MODE");
    }catch(Exception e){Log.e(LOG,"P85_RESTART_PROBE=FAIL_SAFE");}
  }
}
