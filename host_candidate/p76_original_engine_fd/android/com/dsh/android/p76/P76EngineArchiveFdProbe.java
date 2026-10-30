package com.dsh.android.p76;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.ParcelFileDescriptor;
import android.os.RemoteException;
import java.io.File;
import java.io.FileInputStream;
import com.dsh.android.p77.P77TarAudit;
import com.dsh.android.p78.P78ModuleSlot;
import java.util.Arrays;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * P76: SHA-pinned original v138 engine.bin GZIP transfer to the real
 * Android isolated Service by O_RDONLY anonymous/unlinked file descriptor.
 * Does not unpack TAR, run Node, execute scripts, or transfer host paths.
 * The signed-original APK SHA + protected asset comparison is a CI precondition.
 */
public final class P76EngineArchiveFdProbe {
  public static final int TRANSFER=760;
  public static final int ACK=761;
  public static final long MAX_BYTES=128L*1024L*1024L;
  public interface Listener {
    void report(String status);
    void fail(String code);
  }
  private P76EngineArchiveFdProbe(){}
  private static String hex(byte[] bytes) {
    StringBuilder b=new StringBuilder(bytes.length*2);
    for(byte v:bytes)b.append(String.format(Locale.ROOT,"%02x",v&255));
    return b.toString();
  }
  private static MessageDigest sha() throws Exception {
    return MessageDigest.getInstance("SHA-256");
  }
  /** Only this side-by-side test Activity can request the real source archive. */
  public static void start(Activity host,Messenger isolated,String session,
                           Listener listener) {
    if(host==null || isolated==null || listener==null || session==null ||
       !session.matches("[0-9a-f]{64}") ||
       !"com.dsh.p51.isolatedprobe".equals(host.getPackageName()))
      throw new SecurityException("P76_PINNED_ORIGINAL_SIDECAR_REQUIRED");
    final Handler main=new Handler(Looper.getMainLooper());
    final long[] expectedBytes={-1};
    final String[] expectedSha={null};
    final boolean[] terminal={false};
    final Messenger replies=new Messenger(new Handler(Looper.getMainLooper()){
      @Override public void handleMessage(Message m){
        if(terminal[0])return;
        Bundle b;
        try{b=m.getData();}catch(RuntimeException invalid){
          terminal[0]=true;listener.fail("P76_MALFORMED_ACK");return;
        }
        if(m.what!=ACK || m.sendingUid<0 ||
           !android.os.Process.isIsolatedUid(m.sendingUid) ||
           !session.equals(b.getString("session")) ||
           !b.getBoolean("verified",false) ||
           !b.getBoolean("p77_full_tree_verified",false) ||
           !b.getBoolean("p78_bounded_module_read_verified",false) ||
           b.getLong("bytes",-1)!=expectedBytes[0] ||
           expectedSha[0]==null || !expectedSha[0].equals(b.getString("sha256"))) {
          terminal[0]=true;listener.fail("P76_REPLY_UID_SESSION_OR_HASH_MISMATCH");return;
        }
        terminal[0]=true;
        listener.report("P76_REAL_ORIGINAL_ENGINE_GZIP_READONLY_FD_ISOLATED_SHA=PASS");
        listener.report("P77_REAL_ORIGINAL_TAR_FULL_TREE_SHA_MATCH_IN_ISOLATED_UID=PASS");
        listener.report("P78_BOUNDED_ORIGINAL_JS_BYTES_READ_ONCE_IN_ISOLATED_UID=PASS");
        listener.report("P76_ISOLATED_SOURCE_ARCHIVE_NOT_EXECUTED=YES");
        listener.report("P76_PRODUCTION_NODE_MODULE_LOADING_READY=NOT_WIRED");
      }
    });
    new Thread(()->{
      File temporary=null;
      ParcelFileDescriptor input=null;
      boolean posted=false;
      try {
        // Copy with a strict cap; in-App AssetManager may compress engine.bin
        // and thus not support openFd directly.
        temporary=File.createTempFile("p76-engine-archive-", ".bin",host.getCacheDir());
        MessageDigest digest=sha();
        long total=0;int n;byte[] buffer=new byte[65536];
        int first=-1,second=-1;
        try(InputStream in=host.getAssets().open("engine.bin");
            FileOutputStream out=new FileOutputStream(temporary)) {
          while((n=in.read(buffer))!=-1){
            if(n==0)continue;
            if(total==0){first=buffer[0]&255;if(n>1)second=buffer[1]&255;}
            else if(total==1 && second<0)second=buffer[0]&255;
            if(n>MAX_BYTES-total)throw new IOException("P76_ARCHIVE_TOO_LARGE");
            digest.update(buffer,0,n);out.write(buffer,0,n);total+=n;
          }
          out.getFD().sync();
        }
        if(total<1024 || first!=0x1f || second!=0x8b ||
           total!=temporary.length())
          throw new IOException("P76_SOURCE_ARCHIVE_NOT_EXACT_GZIP");
        String digestHex=hex(digest.digest());
        input=ParcelFileDescriptor.open(temporary,ParcelFileDescriptor.MODE_READ_ONLY);
        // Critical: revoke host pathname before Binder transfer.
        if(!temporary.delete())throw new IOException("P76_FAILED_TO_UNLINK_HOST_PATH");
        temporary=null;
        Message msg=Message.obtain(null,TRANSFER);
        Bundle b=new Bundle();
        b.putString("session",session);
        b.putLong("bytes",total);
        b.putString("sha256",digestHex);
        b.putParcelable("archive_fd",input);
        msg.replyTo=replies;msg.setData(b);
        final long length=total;
        final String sha256=digestHex;
        main.post(()->{
          expectedBytes[0]=length;expectedSha[0]=sha256;
          main.postDelayed(()->{
            if(!terminal[0]){
              terminal[0]=true;
              listener.fail("P76_ENGINE_FD_ACK_TIMEOUT");
            }
          },25000);
        });
        // Post the actual send to the SAME main handler after expected bytes,
        // so a quick Binder ACK cannot overtake expectation registration.
        final Message outbound=msg;
        final ParcelFileDescriptor outboundFd=input;
        main.post(()->{
          try{isolated.send(outbound);}
          catch(RemoteException unavailable){
            if(!terminal[0]){terminal[0]=true;listener.fail("P76_ISOLATED_BINDER_SEND_FAILED");}
          }finally{
            try{outboundFd.close();}catch(IOException ignored){}
          }
        });
        posted=true;
      }catch(Exception fail){
        main.post(()->{
          if(!terminal[0]){terminal[0]=true;listener.fail("P76_ARCHIVE_SOURCE_OR_FD_FAILED");}
        });
      }finally {
        // Binder parceling occurs after send(), and the sender can close
        // its descriptor only once send() has completed. The posted main
        // callback must own that closure; not this worker's finally.
        if(!posted && input!=null)try{input.close();}catch(IOException ignored){}
        if(temporary!=null)temporary.delete();
      }
    },"p76-original-engine-source-copy").start();
  }
  /** Called only after original P43 Service verified host UID and session. */
  public static void receiveInIsolatedWorker(Bundle body,Messenger reply,String session) {
    if(!android.os.Process.isIsolated() || reply==null || body==null ||
       session==null || !session.equals(body.getString("session")))
      return;
    final long expectedLength=body.getLong("bytes",-1);
    final String expectedHash=body.getString("sha256");
    if(expectedLength<1024||expectedLength>MAX_BYTES || expectedHash==null ||
       !expectedHash.matches("[0-9a-f]{64}"))return;
    final ParcelFileDescriptor fd;
    try {
      fd=(ParcelFileDescriptor)body.getParcelable("archive_fd");
    } catch(RuntimeException badParcel){return;}
    if(fd==null)return;
    new Thread(()->{
      try(ParcelFileDescriptor.AutoCloseInputStream in=
          new ParcelFileDescriptor.AutoCloseInputStream(fd)){
        MessageDigest digest=sha();
        long count=0;byte[] buffer=new byte[65536];int n,first=-1,second=-1;
        while((n=in.read(buffer))!=-1){
          if(n==0)continue;
          if(count==0){first=buffer[0]&255;if(n>1)second=buffer[1]&255;}
          else if(count==1&&second<0)second=buffer[0]&255;
          if(n>MAX_BYTES-count)throw new IOException("P76_WORKER_READ_OVERSIZE");
          count+=n;digest.update(buffer,0,n);
        }
        if(count!=expectedLength || first!=0x1f || second!=0x8b ||
           !expectedHash.equals(hex(digest.digest())))
          throw new IOException("P76_WORKER_HASH_OR_SIZE_MISMATCH");
        // The same O_RDONLY unlinked FD is seekable; no raw file path,
        // extraction, chmod or Node script execution is involved.
        in.getChannel().position(0);
        P78ModuleSlot module=new P78ModuleSlot(session);
        P77TarAudit.Result original=P77TarAudit.inspectGzip(in,module);
        if(!original.isExactOriginal() || !module.isReady())
          throw new IOException("P78_ORIGINAL_ROOT_OR_JS_CANDIDATE_MISMATCH");
        byte[] js=module.takeOnce(session,module.opaqueId());
        try {
          if(js.length<1 || js.length>P78ModuleSlot.MAX_JS_BYTES ||
             !module.moduleSha().equals(hex(sha().digest(js))))
            throw new IOException("P78_MODULE_DIGEST_OR_SIZE_MISMATCH");
        }finally{
          Arrays.fill(js,(byte)0);
        }
        if(module.isReady())
          throw new IOException("P78_MODULE_ONESHOT_REPLAY");
        Bundle b=new Bundle();b.putString("session",session);
        b.putLong("bytes",count);b.putString("sha256",expectedHash);
        b.putBoolean("verified",true);
        b.putBoolean("p77_full_tree_verified",true);
        b.putBoolean("p78_bounded_module_read_verified",true);
        Message ack=Message.obtain(null,ACK);ack.setData(b);reply.send(ack);
      }catch(Exception failure){
        // Never send an unverified success; no private archive bytes or paths
        // are printed, and no script is loaded.
      }
    },"p76-real-archive-fd-hash-only").start();
  }
}
