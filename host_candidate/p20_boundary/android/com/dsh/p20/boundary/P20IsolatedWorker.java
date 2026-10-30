package com.dsh.p20.boundary;

import android.app.Service;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import java.io.FileInputStream;
import java.net.InetSocketAddress;
import java.net.Socket;

/**
 * Isolated UID: attempts only a synthetic host file and host loopback listener.
 * The host has INTERNET, this isolated process does not inherit it.
 * Test-only: no production Node engine or real user data is available.
 */
public final class P20IsolatedWorker extends Service {
  static final int PROBE=1;
  private final Messenger work=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message request) {
      if(request.what!=PROBE || request.replyTo==null)return;
      if(!Process.isIsolated())return;
      Bundle args;
      try {args=request.getData();}
      catch(RuntimeException ignored){return;}
      final String path=args.getString("canaryPath","");
      final int port=args.getInt("port",-1);
      // Strictly a synthetic file within the disposable test package.
      if(!path.endsWith("/files/p20-synthetic-host-canary.tmp") ||
         port<1 || port>65535)return;
      final Messenger replyTarget=request.replyTo;
      // Network/Socket operations must run off Android's main looper.
      new Thread(()->{
      boolean fileReadable=false;
      try(FileInputStream stream=new FileInputStream(path)){
        fileReadable=stream.read()>=0;
      }catch(Exception denied){fileReadable=false;}
      boolean networkDeniedByOS=false;
      try(Socket socket=new Socket()){
        socket.connect(new InetSocketAddress("127.0.0.1",port),1000);
      }catch(SecurityException denied){
        networkDeniedByOS=true;
      }catch(java.net.SocketException denied){
        String reason=String.valueOf(denied.getMessage());
        networkDeniedByOS=reason.contains("EACCES") ||
                          reason.contains("EPERM") ||
                          reason.contains("Permission denied") ||
                          reason.contains("Operation not permitted");
      }catch(Exception unknown){
        // Refused/timed-out sockets are UNKNOWN rather than permission denial.
        networkDeniedByOS=false;
      }
      Bundle report=new Bundle();
      report.putBoolean("isolated",Process.isIsolated());
      report.putInt("uid",Process.myUid());
      report.putBoolean("canaryReadable",fileReadable);
      report.putBoolean("networkDeniedByOS",networkDeniedByOS);
      Message reply=Message.obtain(null,PROBE);
      reply.setData(report);
      try{replyTarget.send(reply);}catch(Exception ignored){}
      },"p20-isolated-network-permission-probe").start();
    }
  });
  @Override public IBinder onBind(Intent intent){
    if(!Process.isIsolated())throw new SecurityException("isolated UID required");
    return work.getBinder();
  }
}
