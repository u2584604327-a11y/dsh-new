package com.dsh.android.p71;

import android.app.Activity;
import android.content.SharedPreferences;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/** Disposable P51 side-by-side-only WebView persistence proof.
 * Synthetic HTTPS origin and synthetic marker only; no real credentials.
 */
public final class P71WebViewProfileProbe {
  private static final String URL="https://p71-webview.test/";
  private static final String NAME="dsh_p71_probe";
  private static final String VALUE="synthetic_v1";
  private static void report(String s){android.util.Log.i("P71_WEBVIEW_PROFILE",s);}
  private P71WebViewProfileProbe(){}
  public static void run(Activity activity) {
    if(!"com.dsh.p51.isolatedprobe".equals(activity.getPackageName()))
      throw new SecurityException("P71_SIDECAR_ONLY");
    final SharedPreferences prefs=activity.getSharedPreferences("p71_synthetic",0);
    final boolean second=prefs.getBoolean("created",false);
    final CookieManager cookie=CookieManager.getInstance();
    cookie.setAcceptCookie(true);
    final WebView view=new WebView(activity);
    WebSettings settings=view.getSettings();
    settings.setDomStorageEnabled(true);
    settings.setJavaScriptEnabled(true);
    activity.setContentView(view);
    view.setWebViewClient(new WebViewClient(){
      @Override public void onPageFinished(WebView current,String currentUrl) {
        if(!URL.equals(currentUrl)) {
          report("P71_WEBVIEW_SYNTHETIC_ORIGIN_DRIFT=FAIL");return;
        }
        if(second){
          String actual=cookie.getCookie(URL);
          boolean hasCookie=actual!=null&&actual.contains(NAME+"="+VALUE);
          view.evaluateJavascript(
              "(function(){return localStorage.getItem('"+NAME+"')})()",value->{
                boolean hasDom=("\""+VALUE+"\"").equals(value);
                if(hasCookie&&hasDom)
                  report("P71_COOKIE_DOMSTORAGE_SURVIVE_FORCE_STOP=PASS");
                else report("P71_COOKIE_OR_DOMSTORAGE_MISSING=FAIL");
                cookie.flush();
                view.destroy();
              });
        } else {
          view.evaluateJavascript("(function(){localStorage.setItem('"+
              NAME+"','"+VALUE+"');return localStorage.getItem('"+NAME+"')})()",value->{
                if(!("\""+VALUE+"\"").equals(value)){
                  report("P71_DOMSTORAGE_SEED=FAIL");view.destroy();return;
                }
                cookie.setCookie(URL,NAME+"="+VALUE+
                    "; Path=/; Max-Age=2592000; Secure; SameSite=Lax",success->{
                      if(!Boolean.TRUE.equals(success)) {
                        report("P71_COOKIE_SEED=FAIL");view.destroy();return;
                      }
                      cookie.flush();
                      if(!prefs.edit().putBoolean("created",true).commit()) {
                        report("P71_SYNTHETIC_PREFS_SEED=FAIL");view.destroy();return;
                      }
                      report("P71_COOKIE_DOMSTORAGE_SYNTHETIC_SEEDED=PASS");
                      view.destroy();
                });
          });
        }
      }
    });
    view.loadDataWithBaseURL(URL,
        "<!doctype html><html><body>synthetic local WebView state</body></html>",
        "text/html","UTF-8",null);
  }
}
