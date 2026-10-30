package com.dsh.android.p43;
import android.app.Service;
import android.content.Intent;
import android.os.*;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import com.dsh.android.p48.P48FixedIsolatedChild;
import com.dsh.android.p50.P50OriginalNodeFixedChild;
import com.dsh.android.p76.P76EngineArchiveFdProbe;
/**
 * P43 separate isolated-Service test inside original DSH APK only.
 * No Node, files, networking, credentials or capabilities.
 */
public final class P43IsolatedWorker extends Service {
  public static final int INIT=431, HELLO=432;
  private boolean used=false;
  private int acceptedHostUid=-1;
  private String acceptedSession;
  private P48FixedIsolatedChild p48Child;
  private P50OriginalNodeFixedChild p50Child;
  private boolean p76ArchiveUsed;
  private final Messenger inbox=new Messenger(new Handler(Looper.getMainLooper()) {
    @Override public void handleMessage(Message message) {
      if(message.what==P76EngineArchiveFdProbe.TRANSFER){
        if(!used || p76ArchiveUsed || !android.os.Process.isIsolated() ||
           message.sendingUid!=acceptedHostUid || message.replyTo==null ||
           acceptedSession==null)return;
        final Bundle bundle;
        try{bundle=message.getData();}catch(RuntimeException bad){return;}
        if(!acceptedSession.equals(bundle.getString("session")))return;
        p76ArchiveUsed=true;
        P76EngineArchiveFdProbe.receiveInIsolatedWorker(
            bundle,message.replyTo,acceptedSession);
        return;
      }
      // P48 is a second, separately sequenced one-shot session, allowed ONLY
      // after P43/P44/P45/P46's verified original-host initiation.
      if(message.what==P48FixedIsolatedChild.START) {
        if(!used || p48Child!=null || p50Child!=null || !android.os.Process.isIsolated() ||
           message.sendingUid!=acceptedHostUid || message.replyTo==null)
          return;
        String p48Session;
        try{p48Session=message.getData().getString("session");}
        catch(RuntimeException e){return;}
        if(acceptedSession==null||!acceptedSession.equals(p48Session))return;
        final String mode;
        try{mode=message.getData().getString("p50_mode");}
        catch(RuntimeException badMode){return;}
        if("p50-exact-original-node".equals(mode)) {
          p50Child=new P50OriginalNodeFixedChild(
              P43IsolatedWorker.this,message.replyTo,acceptedSession);
          p50Child.start();
        } else if(mode==null || "p48-fixed-id".equals(mode)) {
          p48Child=new P48FixedIsolatedChild(message.replyTo,acceptedSession);
          p48Child.start();
        }
        // Unknown modes cannot obtain arbitrary process execution.
        return;
      }
      if(message.what==P48FixedIsolatedChild.STOP ||
         message.what==P48FixedIsolatedChild.KILL) {
        if(message.sendingUid!=acceptedHostUid || (p48Child==null && p50Child==null))return;
        String session;
        try{session=message.getData().getString("session");}
        catch(RuntimeException e){return;}
        if(!acceptedSession.equals(session))return;
        if(p48Child!=null)p48Child.stop(message.what==P48FixedIsolatedChild.KILL);
        if(p50Child!=null)p50Child.stop(message.what==P48FixedIsolatedChild.KILL);
        return;
      }
      if(message.what!=INIT || used || !android.os.Process.isIsolated() ||
         message.replyTo==null ||
         message.sendingUid!=getApplicationInfo().uid) return;
      Bundle data=message.getData();
      String session=data.getString("session");
      if(session==null || !session.matches("[a-f0-9]{64}"))return;
      // The profile is only a simulated view. A syntactically malformed,
      // noncanonical or unexpectedly privileged profile fails closed.
      final P44VirtualDeviceProfile profile;
      try {
        profile=P44VirtualDeviceProfile.parse(data.getString("p44_profile"));
      } catch(RuntimeException invalidProfile) { return; }
      if(profile.canMakeSystemVirtualMachine() ||
         profile.altersRealHardwareIdentity() ||
         profile.grantsNetworkOrFilesystemAccess() ||
         profile.hasIndependentKernel())return;
      // P45: receive ONLY one host-minted synthetic private asset as an
      // O_RDONLY file descriptor. No path, raw bytes, credentials, or
      // filesystem privilege is sent through Messenger. 64-byte hard cap.
      final ParcelFileDescriptor inputFd;
      try {
        inputFd=(ParcelFileDescriptor)data.getParcelable("p45_readonly_fd");
      } catch(RuntimeException invalid) {return;}
      if(inputFd==null || data.getInt("p45_max_bytes",-1)!=64)return;
      final byte[] content;
      try(InputStream reader=new ParcelFileDescriptor.AutoCloseInputStream(inputFd);
          ByteArrayOutputStream output=new ByteArrayOutputStream()) {
        byte[] chunk=new byte[32];int n;
        while((n=reader.read(chunk))!=-1) {
          if(n>64-output.size())return;
          output.write(chunk,0,n);
        }
        content=output.toByteArray();
      }catch(IOException invalidInput){return;}
      // This probe intentionally uses *synthetic*, public, non-user data.
      // Actual runtime file leasing and script approval are not enabled.
      byte[] expected="P45_SYNTHETIC_PRIVATE_ASSET_V1".getBytes(StandardCharsets.UTF_8);
      if(!Arrays.equals(expected,content))return;
      // P46 two-part manifest and both O_RDONLY PFDs must verify before the
      // one-shot Binder grant is consumed. No unverified bytes are executed.
      final String p46Digest=P46WorkerBundle.verifyFixture(data);
      if(p46Digest==null)return;
      final String assetHash;
      try {
        byte[] hash=MessageDigest.getInstance("SHA-256").digest(content);
        StringBuilder b=new StringBuilder(64);
        for(byte v:hash)b.append(String.format(java.util.Locale.ROOT,"%02x",v&255));
        assetHash=b.toString();
      }catch(Exception hashingFailure){return;}
      used=true;
      acceptedHostUid=message.sendingUid;
      acceptedSession=session;
      Bundle response=new Bundle();
      response.putString("session",session);
      response.putString("p44_profile_hash",profile.fingerprint());
      response.putBoolean("p44_is_real_virtual_machine",false);
      response.putBoolean("p44_hardware_identity_changed",false);
      response.putString("p45_asset_sha256",assetHash);
      response.putInt("p45_asset_size",content.length);
      response.putBoolean("p45_path_transferred",false);
      response.putBoolean("p45_root_used",false);
      response.putString("p46_bundle_sha256",p46Digest);
      response.putInt("p46_verified_parts",P46ResourceBundle.COUNT);
      response.putBoolean("p46_executed_any_script",false);
      Message reply=Message.obtain(null,HELLO);
      reply.setData(response);
      try {message.replyTo.send(reply);} catch(RemoteException ignored){}
    }
  });
  @Override public void onDestroy(){
    if(p48Child!=null)p48Child.stop(true);
    if(p50Child!=null)p50Child.stop(true);
    acceptedSession=null;
    acceptedHostUid=-1;
    super.onDestroy();
  }
  @Override public IBinder onBind(Intent intent){
    if(!android.os.Process.isIsolated())throw new SecurityException("P43_ISOLATED_ONLY");
    return inbox.getBinder();
  }
}
