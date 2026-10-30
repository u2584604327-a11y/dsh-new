package com.dsh.p1.smoketest;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import com.dsh.p12.P12LogViewerReviewEntry;
import java.util.Collections;

/** Disposable test only. Directly invokes candidate attach() from a trusted
 * instrumentation call; this is NOT original host lifecycle wiring.
 * No real queue, credentials, uploads, or external network use.
 */
public final class P12LogViewerInstrumentation extends Instrumentation {
  private static final String TEST_DESTINATION="https://diagnostic-test.invalid/v1/review";
  private static void check(boolean b,String label){if(!b)throw new AssertionError(label);}
  @Override public void onCreate(Bundle args){super.onCreate(args);start();}
  @Override public void onStart(){
    Bundle result=new Bundle();
    Activity main=null;
    Activity viewer=null;
    String phase="ORIGINAL_ACTIVITY";
    try{
      Intent home=new Intent();
      home.setClassName("com.dsh.android","com.dsh.android.MainActivity");
      home.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
      main=startActivitySync(home);
      check(main!=null,"main activity unavailable");

      phase="ORIGINAL_LOGVIEWER_LIFECYCLE";
      ActivityMonitor monitor=addMonitor("com.dsh.android.LogViewerActivity",null,false);
      final Activity trustedMain=main;
      runOnMainSync(()->{
        Intent intent=new Intent();
        intent.setClassName("com.dsh.android","com.dsh.android.LogViewerActivity");
        trustedMain.startActivity(intent);
      });
      viewer=waitForMonitorWithTimeout(monitor,12000);
      check(viewer!=null,"original LogViewerActivity unavailable");
      check("com.dsh.android.LogViewerActivity".equals(viewer.getClass().getName()),
          "unexpected original log viewer class");

      phase="P12_TRUSTED_NATIVE_BUTTON_ATTACH";
      final Activity logActivity=viewer;
      runOnMainSync(()->{
        P12LogViewerReviewEntry entry=P12LogViewerReviewEntry.attach(
            logActivity,TEST_DESTINATION,Collections.singleton(TEST_DESTINATION),
            (stage,item,reason,timestamp,count)->{});
        check(entry!=null,"native entry not installed");
      });
      phase="P12_TWO_EXISTING_BUTTONS";
      int exportId=viewer.getResources().getIdentifier("logExport","id",viewer.getPackageName());
      int uploadId=viewer.getResources().getIdentifier("logUpload","id",viewer.getPackageName());
      check(exportId!=0&&uploadId!=0&&exportId!=uploadId,"original button resource IDs invalid");
      View export=viewer.findViewById(exportId),upload=viewer.findViewById(uploadId);
      check(export!=null&&upload!=null,"original log buttons missing");

      phase="P12_NO_RAW_EXPORT_USER_ACTION";
      runOnMainSync(()->{
        check(export.performClick(),"export user gesture not intercepted");
        check(upload.performClick(),"upload user gesture not intercepted");
      });
      result.putString("P12_ORIGINAL_LOGVIEWER_LAUNCHED","PASS_ANDROID_FIXTURE");
      result.putString("P12_EXISTING_EXPORT_UPLOAD_BUTTONS","BOTH_INTERCEPTED_TEST_CALL");
      result.putString("P12_EMPTY_QUEUE_DEFAULT_DENY","NO_RAW_EXPORT_TRIGGERED");
      result.putString("P12_ORIGINAL_ACTIVITY_LIFECYCLE_WIRED","NO_TEST_ONLY_ATTACH");
      result.putString("P12_NATIVE_APPROVED_TRANSPORT","NOT_CONNECTED");
      result.putString("P12_REAL_PHONE","NOT_TESTED");
      finish(Activity.RESULT_OK,result);
    }catch(Throwable err){
      result.putString("FAIL_PHASE",phase);
      result.putString("FAIL_TYPE",err.getClass().getSimpleName());
      finish(Activity.RESULT_CANCELED,result);
    }finally{
      final Activity oldViewer=viewer;
      if(oldViewer!=null)try{runOnMainSync(oldViewer::finish);}catch(Throwable ignored){}
      final Activity oldMain=main;
      if(oldMain!=null)try{runOnMainSync(oldMain::finish);}catch(Throwable ignored){}
    }
  }
}
