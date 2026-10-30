package com.dsh.p30.nodeprobe;

import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import org.json.JSONArray;
import org.json.JSONObject;

/** Strictly fixed-purpose user-triggered P29 original Node OS boundary probe.
 * Original v138 ARM64 Node with fixed --eval code, no arbitrary inputs.
 * All original runtime binaries are immutable installer-extracted ELF.
 */
public final class P30Worker extends Service {
  private static final String EXEC="libdshnode_p21_exec.so";
  private static final String ORIGINAL_NODE_SHA=
      "a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6";
  private static final String ORIGINAL_SIGNED_APK_SHA=
      "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5";
  private static final int MAX_LIBS=10;
  /** Fixed source: no input-provided JS, scripts, URLs or payload. */
  private static final String FIXED_JS =
    "const fs=require('node:fs'),net=require('node:net');"
    +"const out={uid:process.getuid(),file:'UNTESTED',local:'UNTESTED',remote:'UNTESTED'};"
    +"try{fs.readFileSync(process.env.P30_CANARY_PATH);out.file='ALLOWED';}"
    +"catch(e){out.file=['EACCES','EPERM'].includes(e.code)?'DENIED_'+e.code:'OTHER_'+String(e.code||'UNKNOWN');}"
    +"function tcp(host,port){return new Promise(done=>{"
    +"let sock,ended=false;function finish(x){if(ended)return;ended=true;if(sock)sock.destroy();done(x);}"
    +"try{sock=net.connect({host,port});sock.once('connect',()=>finish('CONNECTED'));"
    +"sock.once('error',e=>finish(['EACCES','EPERM'].includes(e.code)?'DENIED_'+e.code:'OTHER_'+String(e.code||'UNKNOWN')));"
    +"sock.setTimeout(2500,()=>finish('TIMEOUT'));}"
    +"catch(e){finish('OTHER_'+String(e.code||'UNKNOWN'));}"
    +"});}"
    +"Promise.all([tcp('127.0.0.1',9),tcp('198.51.100.1',443)])"
    +".then(r=>{out.local=r[0];out.remote=r[1];console.log(JSON.stringify(out));})"
    +".catch(()=>{process.exitCode=43;});";
  private static boolean denied(String code){
    return "DENIED_EACCES".equals(code)||"DENIED_EPERM".equals(code);
  }
  private static String limitedProcessOutput(InputStream input)throws Exception {
    ByteArrayOutputStream out=new ByteArrayOutputStream();
    byte[] buf=new byte[1024];int count;
    while((count=input.read(buf))!=-1){
      if(out.size()+count>3072)throw new IllegalStateException("NODE_OUTPUT_EXCESSIVE");
      out.write(buf,0,count);
    }
    return out.toString("UTF-8").trim();
  }

  private static boolean safeName(String s) {
    return s!=null && s.matches("lib[a-zA-Z0-9_.+-]{1,70}\\.so")
        && !s.contains("..") && s.indexOf('/')<0;
  }
  private static String hash(File f) throws Exception {
    if(!f.isFile() || !f.canRead() || f.length()<1000
        || f.length()>128L*1024*1024)
      throw new IllegalStateException("MISSING_OR_UNREASONABLE_ELF");
    MessageDigest digest=MessageDigest.getInstance("SHA-256");
    try(InputStream source=new FileInputStream(f)) {
      byte[] buffer=new byte[65536];int count;
      while((count=source.read(buffer))!=-1)digest.update(buffer,0,count);
    }
    StringBuilder out=new StringBuilder();
    for(byte b:digest.digest())out.append(String.format(Locale.ROOT,"%02x",b&255));
    return out.toString();
  }
  private static String readAsset(InputStream source)throws Exception{
    try(InputStream input=source;ByteArrayOutputStream out=new ByteArrayOutputStream()) {
      byte[] bytes=new byte[1024];int n;
      while((n=input.read(bytes))!=-1){
        if(out.size()+n>16384)throw new IllegalStateException("LOCK_OVERSIZED");
        out.write(bytes,0,n);
      }
      return new String(out.toByteArray(),StandardCharsets.UTF_8);
    }
  }
  private final Messenger binder=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message request){
      if(request.what!=1 || request.replyTo==null || !Process.isIsolated())
        return;
      // Framework-authenticated caller must be our normal package UID.
      if(request.sendingUid!=getApplicationInfo().uid)return;
      final Messenger receiver=request.replyTo;
      // Capture while this Binder Message is still valid, before worker thread starts.
      final String suppliedCanary;
      try{
        suppliedCanary=request.getData().getString("canaryPath");
      }catch(RuntimeException malformed){return;}
      new Thread(()->{
        boolean allHashes=false,uidMatch=false;
        String childUid="NOT_TESTED",fileCode="NOT_TESTED",
            localCode="NOT_TESTED",remoteCode="NOT_TESTED",
            nodeExit="NOT_TESTED";
        String phase="START",note="NONE",status="BLOCKED";
        java.lang.Process nodeProcess=null;
        try{
          phase="REQUIRE_REAL_ARM64_ANDROID";
          boolean arm64=false;
          for(String candidate:Build.SUPPORTED_ABIS)
            if("arm64-v8a".equals(candidate))arm64=true;
          if(!arm64)throw new IllegalStateException("ARM64_ABI_NOT_AVAILABLE");
          if(Build.VERSION.SDK_INT<34)
            throw new IllegalStateException("ANDROID_API_BELOW_34");
          if(checkSelfPermission(android.Manifest.permission.INTERNET)
                ==PackageManager.PERMISSION_GRANTED)
            throw new SecurityException("ISOLATED_WORKER_HAS_INTERNET");
          phase="VERIFY_INSTALLER_IMMUTABLE_NATIVE_DIR";
          File directory=new File(getApplicationInfo().nativeLibraryDir).getCanonicalFile();
          if(!directory.isDirectory())throw new IllegalStateException("NATIVE_DIR_ABSENT");
          File executable=new File(directory,EXEC).getCanonicalFile();
          if(!directory.equals(executable.getParentFile()) ||
              !executable.canExecute())
            throw new SecurityException("EXECUTABLE_NOT_PACKAGE_INSTALLED");
          phase="LOAD_SIGNED_BINARY_LOCK";
          JSONObject lock=new JSONObject(readAsset(getAssets().open("p28-runtime-lock.json")));
          if(!"P28_EXACT_V138_NODE_SHA_PIN".equals(lock.getString("gate")) ||
             !ORIGINAL_SIGNED_APK_SHA.equals(lock.getString("source_apk_sha256")) ||
             !ORIGINAL_NODE_SHA.equals(lock.getString("node_sha256")))
            throw new SecurityException("PINNED_SOURCE_CHANGED");
          JSONArray libs=lock.getJSONArray("libs");
          JSONArray preload=lock.getJSONArray("preload");
          if(libs.length()!=MAX_LIBS || preload.length()!=6)
            throw new SecurityException("DEPENDENCY_COUNT_MISMATCH");
          phase="VERIFY_ORIGINAL_NODE_AND_ALL_TEN_LIBRARY_BYTES";
          if(!ORIGINAL_NODE_SHA.equals(hash(executable)))
            throw new SecurityException("NODE_SHA256_MISMATCH");
          Set<String> verifiedNames=new HashSet<>();
          for(int index=0;index<libs.length();index++){
            JSONObject record=libs.getJSONObject(index);
            String alias=record.getString("alias");
            String expected=record.getString("sha256");
            if(!safeName(alias) || !expected.matches("[a-f0-9]{64}") ||
               !verifiedNames.add(alias))
              throw new SecurityException("LIBRARY_ALIAS_OR_SHA_INVALID");
            File library=new File(directory,alias).getCanonicalFile();
            if(!directory.equals(library.getParentFile()) ||
               !expected.equals(hash(library)))
              throw new SecurityException("ORIGINAL_LIBRARY_SHA_MISMATCH");
          }
          StringBuilder preloadEnv=new StringBuilder();
          Set<String> preloadAliases=new HashSet<>();
          for(int index=0;index<preload.length();index++){
            String alias=preload.getString(index);
            if(!safeName(alias) || !verifiedNames.contains(alias) ||
               !preloadAliases.add(alias))
              throw new SecurityException("PRELOAD_MAP_INVALID");
            File dependency=new File(directory,alias).getCanonicalFile();
            if(!directory.equals(dependency.getParentFile()))
              throw new SecurityException("PRELOAD_OUTSIDE_IMMUTABLE_DIR");
            if(index>0)preloadEnv.append(':');
            preloadEnv.append(dependency.getAbsolutePath());
          }
          allHashes=true;
          phase="VALIDATE_HOST_PRIVATE_CANARY_PATH";
          String supplied=suppliedCanary;
          if(supplied==null || supplied.length()>512)
            throw new SecurityException("CANARY_PATH_INVALID");
          File canary=new File(supplied).getCanonicalFile();
          File intendedParent=new File(getApplicationInfo().dataDir,"files").getCanonicalFile();
          if(!canary.getParentFile().equals(intendedParent) ||
             !"p30_private_canary.bin".equals(canary.getName()))
            throw new SecurityException("CANARY_NOT_HOST_PRIVATE_SCOPE");
          phase="EXECUTE_FIXED_NODE_PROCESS_GETUID_AND_DENIAL_PROBES";
          // Node's real process.getuid() and node:fs/node:net APIs:
          // never read host content into our report or upload it.
          ProcessBuilder pb=new ProcessBuilder(executable.getAbsolutePath(),
              "--no-warnings","--eval",FIXED_JS);
          pb.redirectErrorStream(true);
          pb.directory(new File("/"));
          Map<String,String> environment=pb.environment();
          environment.clear();
          environment.put("PATH","/system/bin");
          environment.put("HOME","/");
          environment.put("LD_LIBRARY_PATH",directory.getAbsolutePath());
          environment.put("LD_PRELOAD",preloadEnv.toString());
          environment.put("P30_CANARY_PATH",canary.getAbsolutePath());
          nodeProcess=pb.start();
          phase="WAIT_FIXED_18_SECONDS";
          if(!nodeProcess.waitFor(18,TimeUnit.SECONDS))
            throw new IllegalStateException("NODE_BOUNDARY_TEST_TIMEOUT");
          int code=nodeProcess.exitValue();
          nodeExit=String.valueOf(code);
          if(code!=0)throw new IllegalStateException("NODE_NONZERO_EXIT");
          phase="VALIDATE_REAL_CHILD_NODE_JSON";
          String output=limitedProcessOutput(nodeProcess.getInputStream());
          // No raw path, file bytes or stderr may be printed to UI.
          if(!output.startsWith("{") || !output.endsWith("}"))
            throw new IllegalStateException("NO_BOUNDED_CHILD_JSON");
          JSONObject child=new JSONObject(output);
          long observed=child.getLong("uid");
          childUid=String.valueOf(observed);
          uidMatch=observed==Process.myUid();
          fileCode=child.getString("file");
          localCode=child.getString("local");
          remoteCode=child.getString("remote");
          if(!uidMatch) {
            status="FAIL_CHILD_UID_MISMATCH";
            note="NODE_PROCESS_GETUID_DIFFERS_FROM_WORKER_UID";
          } else if(!denied(fileCode)) {
            status="BLOCKED_PRIVATE_CANARY_NOT_EXPLICITLY_DENIED";
            note="FILE_ERRNO_"+fileCode+"_NOT_ACCESS_DENIAL_PASS";
          } else if(!denied(localCode) || !denied(remoteCode)){
            status="BLOCKED_NETWORK_ISOLATION_NOT_PROVEN";
            note="TCP_DENIAL_NEEDS_EXPLICIT_EACCES_OR_EPERM";
          } else{
            status="PASS_FIXED_REAL_NODE_UID_PRIVATE_FILE_AND_TCP_DENIAL";
            note="ONLY_THIS_PROCESS_PROBE_NOT_FULL_DSH_VM";
          }
          phase="FIXED_CHILD_BOUNDARY_PROBE_FINISHED";
        }catch(Exception failure){
          status="BLOCKED";
          if("NONE".equals(note))note=failure.getClass().getSimpleName();
          // Do not include raw exception, original paths, contents or stdout.
        }catch(LinkageError failure){
          status="BLOCKED";
          note="NATIVE_LINKAGE_ERROR";
        }finally{
          if(nodeProcess!=null && nodeProcess.isAlive())nodeProcess.destroyForcibly();
        }
        Bundle result=new Bundle();
        result.putInt("workerUid",Process.myUid());
        result.putBoolean("workerIsolated",Process.isIsolated());
        result.putBoolean("allHashes",allHashes);
        result.putBoolean("uidMatch",uidMatch);
        result.putString("childUid",childUid);
        result.putString("privateFile",fileCode);
        result.putString("loopback",localCode);
        result.putString("testnet",remoteCode);
        result.putString("nodeExit",nodeExit);
        result.putString("status",status);
        result.putString("phase",phase);
        result.putString("note",note);
        Message m=Message.obtain(null,1);
        m.setData(result);
        try{receiver.send(m);}catch(Exception ignored){}
      },"p30-real-child-uid-and-egress").start();
    }
  });
  @Override public IBinder onBind(Intent intent){
    if(!Process.isIsolated())throw new SecurityException("ISOLATED_ONLY");
    return binder.getBinder();
  }
}
