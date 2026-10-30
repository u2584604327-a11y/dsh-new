package com.dsh.android.p79;
import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import com.dsh.android.p71.P71ToolReplyOnce;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;
import org.json.JSONObject;
import com.dsh.android.p85.P85DurableReplyJournal;
import com.dsh.android.p83.P83HiddenBrowserPane;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Native command/result file producer; P51 independent test package ONLY. */
public final class P79NativeBrowserMailboxProbe {
  private static final String TAG="P79_BROWSER_MAILBOX";
  private static final String ORIGIN="https://p79-fixture.test/";
  private final Activity owner;
  private final Handler main=new Handler(Looper.getMainLooper());
  private final File cmd,res;
  private volatile boolean stopped;
  private final Set<String> seen=new HashSet<>();
  private WebView view;
  private final P85DurableReplyJournal journal;
  private final boolean p83Mode;
  private boolean p86External;
  private boolean p86Ready;
  private static P79NativeBrowserMailboxProbe p86Instance;
  private P83HiddenBrowserPane p83;
  private P79NativeBrowserMailboxProbe(Activity a,String command,String reply,boolean withHide){
    p83Mode=withHide;
    owner=a;
    journal=new P85DurableReplyJournal(a);
    if(!"com.dsh.p51.isolatedprobe".equals(a.getPackageName())||
       command==null||reply==null||
       !command.matches("[A-Za-z0-9._-]{1,80}")||
       !reply.matches("[A-Za-z0-9._-]{1,80}")||
       command.equals(reply)||command.equals(".")||command.equals("..")||
       reply.equals(".")||reply.equals(".."))
      throw new SecurityException("P79_SIDECAR_AND_EXACT_FILENAMES_REQUIRED");
    File home=new File(a.getFilesDir(),"p79-private-browser");
    if((!home.isDirectory()&&!home.mkdir())||!home.isDirectory())
      throw new IllegalStateException("P79_PRIVATE_DIR_UNAVAILABLE");
    cmd=new File(home,command);res=new File(home,reply);
  }
  private static void log(String s){android.util.Log.i(TAG,s);}
  private void fail(String label){
    if(stopped)return;
    stopped=true;log("P79_MAILBOX_"+label+"=FAIL");
    if(view!=null)main.post(()->view.destroy());
  }
  public static void run(Activity a,String cmd,String res){
    run(a,cmd,res,false);
  }
  public static void run(Activity a,String cmd,String res,boolean withHide){
    new P79NativeBrowserMailboxProbe(a,cmd,res,withHide).begin();
  }
  /** Sidecar-only ADB relay. Never add to original production manifest. */
  public static void runP86(Activity a,String cmd,String resultName){
    P79NativeBrowserMailboxProbe p=
      new P79NativeBrowserMailboxProbe(a,cmd,resultName,true);
    p.p86External=true;
    p86Instance=p;
    p.begin();
  }
  public static boolean p86Command(Activity a,String id,String action){
    P79NativeBrowserMailboxProbe p=p86Instance;
    if(p==null || p.owner!=a || !p.p86External || !p.p86Ready ||
       p.stopped || Looper.myLooper()!=Looper.getMainLooper() ||
       id==null || !id.matches("p86[a-z0-9]{2,24}") ||
       action==null || !action.matches("[a-zA-Z]{2,20}"))return false;
    p.dispatch(id,action);
    return true;
  }
  private void p86Notify(String id,boolean ok,String code){
    if(p86External){
      // Synthetic identifiers + outcome category only; NEVER raw webpage
      // bytes, authentication cookies, user chat or input values.
      Log.i("P86_NATIVE_REPLY",id+"|"+(ok?"1":"0")+"|"+code);
    }
  }
  private static String readSmall(File f)throws Exception{
    if(!f.isFile()||f.length()<1||f.length()>8192)return null;
    byte[] b=new byte[(int)f.length()];
    try(FileInputStream in=new FileInputStream(f)){
      int off=0,n;
      while(off<b.length&&(n=in.read(b,off,b.length-off))>0)off+=n;
      if(off!=b.length||in.read()!=-1)return null;
    }
    return new String(b,StandardCharsets.UTF_8);
  }
  private static void atomic(File file,JSONObject value)throws Exception{
    byte[] bytes=value.toString().getBytes(StandardCharsets.UTF_8);
    if(bytes.length>4096)throw new IOException("P79_OVERSIZE_JSON");
    File tmp=new File(file.getParentFile(),file.getName()+".pending");
    try(FileOutputStream out=new FileOutputStream(tmp,false)){
      out.write(bytes);out.getFD().sync();
    }
    if(!tmp.renameTo(file)){tmp.delete();throw new IOException("P79_ATOMIC_RENAME_FAILED");}
  }
  private void begin(){
    cmd.delete();res.delete();
    view=new WebView(owner);
    WebSettings settings=view.getSettings();
    settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(true);
    if(p83Mode){
      p83=new P83HiddenBrowserPane(owner,view);
      p83.attach();
    }else owner.setContentView(view);
    view.setWebViewClient(new WebViewClient(){
      @Override public void onPageFinished(WebView v,String url){
        if(!ORIGIN.equals(url)){fail("ORIGIN");return;}
        if(p86External){
          if(p83!=null)p83.hideBrowser();
          p86Ready=true;
          Log.i("P86_NATIVE_REPLY","P86_NATIVE_WEBVIEW_READY");
        }else{
          new Thread(()->poll(),"p79-command-reader").start();
          new Thread(()->client(),"p79-command-producer").start();
        }
      }
    });
    view.loadDataWithBaseURL(ORIGIN,
      "<!doctype html><html><body style='height:3200px'>"
      +"<h1>synthetic discussion</h1><textarea id='comment'></textarea>"
      +"<button id='publish' onclick=\"document.getElementById('posted').textContent='1'\">Publish</button>"
      +"<output id='posted'>0</output></body></html>",
      "text/html","UTF-8",null);
  }
  private void poll(){
    try{
      while(!stopped){
        String raw=readSmall(cmd);
        if(raw!=null){
          JSONObject request=new JSONObject(raw);
          String id=request.optString("id","");
          if(!id.matches("[A-Za-z0-9_-]{1,96}")){fail("BAD_ID");return;}
          if(seen.add(id)){
            String action=request.optString("action","");
            main.post(()->dispatch(id,action));
          }
        }
        SystemClock.sleep(35);
      }
    }catch(Exception e){fail("READER");}
  }
  private void terminalError(String id,String category){
    try{
      JSONObject result=new JSONObject();
      result.put("id",id);result.put("ok",false);result.put("code",category);
      result.put("outcomeUnknown",false);result.put("retrySafe",false);
      journal.finish(id,result);
      atomic(res,result);
      p86Notify(id,false,category);
    }catch(Exception e){fail("ERROR_REPLY_WRITE");}
  }
  private void dispatch(String id,String action){
    if(stopped)return;
    try {
      JSONObject cached=journal.replayOrUnknown(id);
      if(cached!=null) {
        atomic(res,cached);
        return;
      }
      if(!journal.begin(id)){
        fail("P85_UNEXPECTED_DUPLICATE_BEGIN");return;
      }
    }catch(Exception e){fail("P85_JOURNAL_OPEN");return;}
    if(P71ToolReplyOnce.requiresNativeConfirmation(action)){
      terminalError(id,"NATIVE_USER_CONFIRMATION_REQUIRED");return;
    }
    final String js;
    switch(action){
      case "read":
        js="(function(){return document.body.textContent.indexOf('synthetic discussion')>=0})()";break;
      case "scroll":
        js="(function(){window.scrollTo(0,1100);return document.body.scrollHeight>innerHeight})()";break;
      case "locate":
        js="(function(){return document.querySelector('#comment') instanceof HTMLTextAreaElement})()";break;
      case "draft":
        js="(function(){var b=document.querySelector('#comment');b.value='synthetic draft';"
          +"b.dispatchEvent(new Event('input',{bubbles:true}));return b.value==='synthetic draft'})()";break;
      case "status":
        js="(function(){return document.querySelector('#posted').textContent==='0'"
          +"&&document.querySelector('#comment').value==='synthetic draft'})()";break;
      default:terminalError(id,"ACTION_NOT_ALLOWLISTED");return;
    }
    P71ToolReplyOnce outcome=new P71ToolReplyOnce(id,t->{
      try{
        JSONObject result=new JSONObject();
        result.put("id",t.id);result.put("ok",t.ok);result.put("code",t.code);
        result.put("result",t.ok?"synthetic_native_callback":JSONObject.NULL);
        result.put("outcomeUnknown",t.outcomeUnknown);
        result.put("retrySafe",t.retrySafe);
        journal.finish(id,result);
        atomic(res,result);
        p86Notify(id,t.ok,t.code);
      }catch(Exception e){fail("TERMINAL_REPLY_WRITE");}
    });
    if(!outcome.markDispatched()){fail("DOUBLE_DISPATCH");return;}
    main.postDelayed(()->outcome.deadlineElapsed(),4000);
    view.evaluateJavascript(js,value->{
      if("true".equals(value))outcome.executorConfirmedSuccess();
      else outcome.executorConfirmedFailure("EVAL_NOT_TRUE");
    });
  }
  private void client(){
    String[] actions={"read","scroll","locate","draft","status","postComment"};
    try{
      if(p83Mode){
        CountDownLatch hidden=new CountDownLatch(1);
        main.post(()->{
          try{
            p83.hideBrowser();
            if(!p83.isHiddenAndAttached())fail("P83_WEBVIEW_WAS_DETACHED");
            else log("P83_BROWSER_HIDDEN_WITH_SAME_ATTACHED_WEBVIEW=PASS");
          }finally{hidden.countDown();}
        });
        if(!hidden.await(5,TimeUnit.SECONDS)||stopped){
          fail("P83_HIDE_FAILED");return;
        }
      }
      for(int k=0;k<actions.length;k++){
        String id="p79call"+k;
        if(!res.delete()&&res.exists())throw new IOException("P79_STALE_REPLY");
        JSONObject command=new JSONObject();command.put("id",id);
        command.put("action",actions[k]);atomic(cmd,command);
        long end=SystemClock.elapsedRealtime()+8500;
        JSONObject reply=null;
        while(!stopped&&SystemClock.elapsedRealtime()<end){
          String raw=readSmall(res);
          if(raw!=null){
            JSONObject candidate=new JSONObject(raw);
            if(id.equals(candidate.optString("id"))){reply=candidate;break;}
          }
          SystemClock.sleep(45);
        }
        if(reply==null){fail("NO_MATCHING_REPLY");return;}
        if(k<5){
          if(!reply.optBoolean("ok")||!"OK".equals(reply.optString("code"))){
            fail("MISSING_NATIVE_SUCCESS");return;
          }
        }else if(reply.optBoolean("ok")||
                !"NATIVE_USER_CONFIRMATION_REQUIRED".equals(reply.optString("code"))){
          fail("COMMENT_CONSENT_BYPASS");return;
        }
        log("P79_FILE_COMMAND_NATIVE_RESULT_STEP_"+k+"=PASS");
        if(p83Mode) {
          final int done=k+1;
          main.post(()->p83.completedStep(done,actions.length));
        }
      }
      if(p83Mode){
        CountDownLatch restore=new CountDownLatch(1);
        main.post(()->{
          if(!p83.isHiddenAndAttached()){
            fail("P83_HIDDEN_DURING_TOOL_REPLIES_NOT_PRESERVED");
            restore.countDown();return;
          }
          p83.showBrowser();
          if(!p83.isRestoredSameWebView()){
            fail("P83_RESTORED_WRONG_WEBVIEW_INSTANCE");
            restore.countDown();return;
          }
          view.evaluateJavascript(
            "(function(){return document.querySelector('#comment').value==='synthetic draft'"+
            "&&document.querySelector('#posted').textContent==='0'})()",
            value->{
              if(!"true".equals(value))fail("P83_DRAFT_CHANGED_WHILE_HIDDEN");
              else {
                log("P83_WEBVIEW_DRAFT_AND_NO_PUBLISH_SURVIVE_HIDE_REOPEN=PASS");
                log("P83_HIDDEN_WEBVIEW_TOOL_REPLIES_STILL_COMPLETE=PASS");
              }
              restore.countDown();
            });
        });
        if(!restore.await(6,TimeUnit.SECONDS)||stopped){
          fail("P83_RESTORE_FAILED");return;
        }
      }
      stopped=true;
      log("P79_REAL_ANDROID_FILE_MAILBOX_WEBVIEW_REPLY_CHAIN=PASS");
      log("P79_COMMENT_PUBLISHED=NO");
      log("P79_ORIGINAL_DSH_MODEL_CONTINUATION=NOT_WIRED");
      if(!p83Mode)main.post(()->view.destroy());
    }catch(Exception e){fail("SYNTHETIC_CLIENT");}
  }
}
