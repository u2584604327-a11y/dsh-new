package com.dsh.android.p73;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebSettings;
import com.dsh.android.p71.P71ToolReplyOnce;

/**
 * Genuine Android WebView.evaluateJavascript callback -> exactly-one native
 * tool result. Synthetic local page only, no user credentials or Bilibili
 * network/publishing. NOT original DSH browser/model dispatcher integration.
 */
public final class P73BrowserToolCallbackProbe {
  private static final String ORIGIN="https://p73-webview.test/";
  private static final String TAG="P73_BROWSER_TOOL";
  private final Activity activity;
  private final Handler main=new Handler(Looper.getMainLooper());
  private WebView web;
  private int step;
  private boolean finished;
  private P73BrowserToolCallbackProbe(Activity owner){activity=owner;}
  private static void report(String value){android.util.Log.i(TAG,value);}
  private void fail(String code){
    if(finished)return;
    finished=true;
    report("P73_NATIVE_BROWSER_CALLBACK_"+code+"=FAIL");
    if(web!=null)web.destroy();
  }
  public static void run(Activity activity){
    if(!"com.dsh.p51.isolatedprobe".equals(activity.getPackageName()))
      throw new SecurityException("P73_PRIVATE_SIDECAR_ONLY");
    new P73BrowserToolCallbackProbe(activity).begin();
  }
  private void begin(){
    web=new WebView(activity);
    WebSettings cfg=web.getSettings();
    cfg.setJavaScriptEnabled(true);
    cfg.setDomStorageEnabled(true);
    activity.setContentView(web);
    web.setWebViewClient(new WebViewClient(){
      @Override public void onPageFinished(WebView view,String url){
        if(!ORIGIN.equals(url)){fail("WRONG_ORIGIN");return;}
        runStep();
      }
    });
    web.loadDataWithBaseURL(ORIGIN,
       "<!doctype html><html><body style='min-height:3000px'>"
       +"<h1>P73 synthetic comment test page</h1>"
       +"<textarea id='comment'></textarea><button id='publish'>Publish</button>"
       +"<output id='posted'>0</output>"
       +"<script>document.getElementById('publish').onclick=function(){"
       +"document.getElementById('posted').textContent='1'}</script>"
       +"</body></html>",
       "text/html","UTF-8",null);
  }
  private void runStep(){
    if(finished)return;
    if(step>=5){
      finished=true;
      report("P73_BROWSER_READ_SCROLL_FIND_TYPE_CALLBACK_CHAIN=PASS");
      report("P73_PUBLIC_COMMENT_ACTUALLY_SENT=NO");
      report("P73_ORIGINAL_DSH_MODEL_CONTINUATION=NOT_WIRED");
      web.destroy();
      return;
    }
    String id="p73call"+step;
    P71ToolReplyOnce outcome=new P71ToolReplyOnce(id,result->{
      if(!result.ok)fail(result.code);
    });
    if(!outcome.markDispatched()){fail("NOT_DISPATCHED");return;}
    final int index=step;
    if(index==4) {
      // Publishing must not be triggered without an actual native user
      // confirmation. Verify synthetic button was never clicked.
      if(!P71ToolReplyOnce.requiresNativeConfirmation("postComment")){
        fail("MISSING_NATIVE_APPROVAL_GATE");return;
      }
    }
    final String js;
    switch(index){
      case 0:
        js="(function(){return document.body.textContent.indexOf('P73 synthetic comment test page')>=0})()";
        break;
      case 1:
        js="(function(){window.scrollTo(0,900);return document.body.scrollHeight>innerHeight})()";
        break;
      case 2:
        js="(function(){return document.querySelector('#comment') instanceof HTMLTextAreaElement})()";
        break;
      case 3:
        js="(function(){var box=document.querySelector('#comment');"
          +"box.value='synthetic draft only';box.dispatchEvent(new Event('input',{bubbles:true}));"
          +"return box.value==='synthetic draft only'})()";
        break;
      case 4:
        js="(function(){return document.querySelector('#posted').textContent==='0'"
          +"&&document.querySelector('#comment').value==='synthetic draft only'})()";
        break;
      default:fail("INVALID_STEP");return;
    }
    main.postDelayed(()->{
      if(index==step && !finished && outcome.deadlineElapsed())
        fail("NO_JAVASCRIPT_REPLY");
    },8000);
    web.evaluateJavascript(js,value->{
      if(finished || index!=step)return;
      if(!"true".equals(value)){
        outcome.executorConfirmedFailure("NATIVE_EVAL_RESULT_FALSE");
        fail("EVALUATION_NEGATIVE");return;
      }
      if(!outcome.executorConfirmedSuccess()){
        fail("DUPLICATE_NATIVE_CALLBACK");return;
      }
      report("P73_WEBVIEW_CALLBACK_STEP_"+index+"=PASS");
      step++;
      runStep();
    });
  }
}
