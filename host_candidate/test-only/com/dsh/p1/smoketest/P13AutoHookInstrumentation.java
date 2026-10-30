package com.dsh.p1.smoketest;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ProviderInfo;
import android.content.ComponentName;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.View;

/** P13 product-autohook detection. Test never invokes P12.attach().
 * Requires actual AndroidX Startup provider discovery in modified APK.
 */
public final class P13AutoHookInstrumentation extends Instrumentation {
  static final String EXPECTED="预览脱敏诊断包";
  static void verify(boolean c,String msg){if(!c)throw new AssertionError(msg);}
  @Override public void onCreate(Bundle bundle){super.onCreate(bundle);start();}
  @Override public void onStart(){
    Bundle result=new Bundle();
    String stage="MANIFEST_STARTUP_DISCOVERY";
    Activity home=null;Activity viewer=null;
    try{
      ProviderInfo info=getTargetContext().getPackageManager().getProviderInfo(
          new ComponentName("com.dsh.android","androidx.startup.InitializationProvider"),
          PackageManager.GET_META_DATA);
      verify(info!=null&&info.metaData!=null,"startup provider metadata missing");
      verify("androidx.startup".equals(info.metaData.getString(
          "com.dsh.p12.P13NativeReviewInitializer")),"P13 metadata discovery missing");

      stage="APP_START";
      Intent intent=new Intent();intent.setClassName("com.dsh.android","com.dsh.android.MainActivity");
      intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
      home=startActivitySync(intent);
      verify(home!=null,"real MainActivity could not start");

      stage="LOGVIEWER_OPEN_NO_MANUAL_ATTACH";
      ActivityMonitor monitor=addMonitor("com.dsh.android.LogViewerActivity",null,false);
      final Activity originalHome=home;
      runOnMainSync(()->{
        Intent i=new Intent();
        i.setClassName("com.dsh.android","com.dsh.android.LogViewerActivity");
        originalHome.startActivity(i);
      });
      viewer=waitForMonitorWithTimeout(monitor,12000);
      verify(viewer!=null,"real LogViewerActivity did not start");

      stage="AUTO_HOOK_EXISTING_NATIVE_BUTTONS";
      final Activity logView=viewer;
      final int exportId=logView.getResources().getIdentifier("logExport","id",logView.getPackageName());
      final int uploadId=logView.getResources().getIdentifier("logUpload","id",logView.getPackageName());
      verify(exportId!=0&&uploadId!=0&&exportId!=uploadId,"original native buttons IDs changed");
      final View export=logView.findViewById(exportId);
      final View upload=logView.findViewById(uploadId);
      verify(export!=null&&upload!=null,"original native buttons absent");
      boolean hooked=false;
      for(int attempt=0;attempt<50;attempt++){
        final boolean[] now={false};
        runOnMainSync(()->{
          CharSequence a=export.getContentDescription();
          CharSequence b=upload.getContentDescription();
          now[0]=a!=null&&b!=null&&a.toString().contains(EXPECTED)
              &&b.toString().contains(EXPECTED);
        });
        if(now[0]){hooked=true;break;}
        SystemClock.sleep(150);
      }
      verify(hooked,"automatic AndroidX Startup callback did not rebind original buttons");

      stage="P13_LOCAL_ONLY_BUTTON_CLICK";
      runOnMainSync(()->{
        verify(export.performClick(),"safe preview export button not clickable");
        verify(upload.performClick(),"safe preview upload button not clickable");
      });

      result.putString("P13_ANDROIDX_STARTUP_METADATA","PASS_REAL_APPLICATION");
      result.putString("P13_LOGVIEWER_AUTOMATIC_HOOK","PASS_NO_MANUAL_ATTACH");
      result.putString("P13_REAL_EXPORT_UPLOAD_BUTTONS","REBOUND_TO_LOCAL_REVIEW");
      result.putString("P13_LEGACY_RAW_ZIP_SEND","P10_DEFAULT_DENY_PRESERVED");
      result.putString("P13_APPROVED_NETWORK_SEND","NOT_CONNECTED");
      result.putString("P13_GENERIC_NODE_SAME_UID_EGRESS","NOT_BLOCKED");
      result.putString("P13_REAL_PHONE_UPGRADE","NOT_TESTED");
      finish(Activity.RESULT_OK,result);
    }catch(Throwable error){
      result.putString("FAIL_PHASE",stage);
      result.putString("FAIL_TYPE",error.getClass().getSimpleName());
      finish(Activity.RESULT_CANCELED,result);
    }finally{
      final Activity v=viewer;final Activity h=home;
      if(v!=null)try{runOnMainSync(v::finish);}catch(Throwable ignored){}
      if(h!=null)try{runOnMainSync(h::finish);}catch(Throwable ignored){}
    }
  }
}
