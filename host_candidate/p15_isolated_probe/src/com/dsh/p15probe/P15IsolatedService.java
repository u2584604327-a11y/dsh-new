package com.dsh.p15probe;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import java.io.File;
import java.io.FileInputStream;

/** A deliberately powerless isolated Android Service for UID/FS proof.
 * Test fixture ONLY. Not the DSH Node runtime, does not execute shell,
 * open files on the user's behalf, access the network or run plugins.
 */
public final class P15IsolatedService extends Service {
    static final int PROBE=1;
    private final Messenger server=new Messenger(new Handler(Looper.getMainLooper()){
        @Override public void handleMessage(Message request){
            if(request.what!=PROBE || request.replyTo==null)return;
            boolean readable=false;
            File appCanary=new File(getApplicationInfo().dataDir,"files/p15-isolation-canary.tmp");
            try(FileInputStream input=new FileInputStream(appCanary)){
                readable=input.read()>=0;
            }catch(Exception expected){readable=false;}
            Bundle answer=new Bundle();
            answer.putBoolean("isolated",Process.isIsolated());
            answer.putInt("uid",Process.myUid());
            answer.putBoolean("appCanaryReadable",readable);
            Message reply=Message.obtain(null,PROBE);
            reply.setData(answer);
            try{request.replyTo.send(reply);}catch(Exception ignored){}
        }
    });
    @Override public IBinder onBind(Intent intent){return server.getBinder();}
    @Override public int onStartCommand(Intent intent,int flags,int id){
        return START_NOT_STICKY;
    }
}
