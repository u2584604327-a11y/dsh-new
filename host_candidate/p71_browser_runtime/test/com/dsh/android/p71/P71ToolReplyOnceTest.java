package com.dsh.android.p71;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
public final class P71ToolReplyOnceTest {
  static int count;
  static void check(boolean b,String name){count++;if(!b)throw new AssertionError("P71_"+name);}
  public static void main(String[] args)throws Exception {
    List<P71ToolReplyOnce.Terminal> good=new ArrayList<>();
    P71ToolReplyOnce success=new P71ToolReplyOnce("run-1",good::add);
    check(success.markDispatched(),"dispatch");
    check(!success.markDispatched(),"duplicate_dispatch");
    check(success.executorConfirmedSuccess(),"executor_success");
    check(!success.executorConfirmedSuccess(),"duplicate_success");
    check(!success.deadlineElapsed(),"timeout_after_success");
    check(good.size()==1&&good.get(0).ok,"one_success");
    List<P71ToolReplyOnce.Terminal> bad=new ArrayList<>();
    P71ToolReplyOnce missing=new P71ToolReplyOnce("run-2",bad::add);
    check(missing.markDispatched(),"missing_dispatch");
    check(missing.deadlineElapsed(),"missing_timeout");
    check(!missing.executorConfirmedSuccess(),"late_success_denied");
    check(bad.size()==1&&bad.get(0).outcomeUnknown&&!bad.get(0).retrySafe,"unknown_no_retry");
    P71ToolReplyOnce queued=new P71ToolReplyOnce("queued",bad::add);
    check(queued.deadlineElapsed(),"queue_timeout");
    check(!bad.get(1).outcomeUnknown&&bad.get(1).retrySafe,"queue_no_side_effect");
    P71ToolReplyOnce lost=new P71ToolReplyOnce("lost",bad::add);
    check(lost.markDispatched(),"lost_dispatch");
    check(lost.browserLost(),"binder_lost");
    check(!lost.executorConfirmedSuccess(),"late_after_lost_denied");
    check(bad.get(2).outcomeUnknown,"disconnect_unknown");
    check(P71ToolReplyOnce.requiresNativeConfirmation("postComment"),"publish_requires_approval");
    check(P71ToolReplyOnce.requiresNativeConfirmation("replyComment"),"reply_requires_approval");
    check(!P71ToolReplyOnce.requiresNativeConfirmation("read"),"read_does_not_publish");
    check(!P71ToolReplyOnce.requiresNativeConfirmation("scroll"),"scroll_does_not_publish");
    boolean denied=false;
    try{new P71ToolReplyOnce("bad id",bad::add);}catch(IllegalArgumentException e){denied=true;}
    check(denied,"invalid_id");
    denied=false;
    try{lost.executorConfirmedFailure("raw private error");}catch(IllegalArgumentException e){denied=true;}
    check(denied,"no_private_error_leak");
    List<P71ToolReplyOnce.Terminal> race=new ArrayList<>();
    P71ToolReplyOnce shared=new P71ToolReplyOnce("race",x->{synchronized(race){race.add(x);}});
    check(shared.markDispatched(),"race_dispatch");
    CountDownLatch go=new CountDownLatch(1);
    Thread a=new Thread(()->{try{go.await();shared.deadlineElapsed();}catch(Exception e){throw new RuntimeException(e);}});
    Thread b=new Thread(()->{try{go.await();shared.executorConfirmedSuccess();}catch(Exception e){throw new RuntimeException(e);}});
    a.start();b.start();go.countDown();a.join();b.join();
    synchronized(race){check(race.size()==1,"simultaneous_timeout_reply_one_result");}
    System.out.println("P71_TOOL_RESULT_EXACTLY_ONCE_JVM=PASS assertions="+count);
    System.out.println("P71_LATE_REPLY_NOT_RETRIED=PASS");
    System.out.println("P71_COMMENT_PUBLISH_NATIVE_CONSENT_REQUIRED=PASS");
    System.out.println("P71_ORIGINAL_DSH_MODEL_CONTINUATION=NOT_WIRED");
  }
}
