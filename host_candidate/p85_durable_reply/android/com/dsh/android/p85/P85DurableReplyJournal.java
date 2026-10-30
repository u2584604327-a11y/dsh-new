package com.dsh.android.p85;

import android.content.Context;
import org.json.JSONObject;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * P85 local durable single-call journal.
 * Before dispatch, persist STARTED; before notifying the P6 mailbox,
 * persist terminal JSON. On process death/restart, recover exact terminal
 * or UNKNOWN outcome; never silently replay an effectful request.
 * Test sidecar only until original DSH Node/model wiring is proven.
 */
public final class P85DurableReplyJournal {
  public static final String UNKNOWN="EXECUTION_INTERRUPTED_OUTCOME_UNKNOWN";
  private final File directory;
  public P85DurableReplyJournal(Context context){
    if(context==null || !"com.dsh.p51.isolatedprobe".equals(context.getPackageName()))
      throw new SecurityException("P85_ONLY_BOUNDARY_TEST_PACKAGE");
    directory=new File(context.getFilesDir(),"p85-native-replies");
    if(!directory.isDirectory()&&!directory.mkdir())
      throw new IllegalStateException("P85_PRIVATE_DIR_FAILED");
    if(!directory.isDirectory())throw new IllegalStateException("P85_NOT_DIRECTORY");
  }
  private static String validId(String id){
    if(id==null||!id.matches("[A-Za-z0-9_-]{1,96}"))
      throw new SecurityException("P85_INVALID_REQUEST_ID");
    return id;
  }
  private static String digest(String text){
    try {
      byte[] hash=MessageDigest.getInstance("SHA-256")
        .digest(text.getBytes(StandardCharsets.UTF_8));
      final String chars="0123456789abcdef";
      StringBuilder out=new StringBuilder(64);
      for(byte value:hash){
        int x=value&255;
        out.append(chars.charAt(x>>>4)).append(chars.charAt(x&15));
      }
      return out.toString();
    }catch(Exception ex){throw new IllegalStateException("P85_HASH_MISSING");}
  }
  private File file(String id,String ending){
    return new File(directory,digest(validId(id))+ending);
  }
  private static String load(File file)throws IOException {
    if(!file.isFile() || file.length()<2 || file.length()>4096)
      throw new IOException("P85_MISSING_OR_OVERSIZE_JOURNAL");
    byte[] b=new byte[(int)file.length()];
    try(FileInputStream in=new FileInputStream(file)){
      int n=0,read;
      while(n<b.length && (read=in.read(b,n,b.length-n))>0)n+=read;
      if(n!=b.length||in.read()!=-1)throw new IOException("P85_PARTIAL_JOURNAL");
    }
    return new String(b,StandardCharsets.UTF_8);
  }
  private static void createAtomic(File target,String content)throws IOException{
    if(target.exists())throw new IOException("P85_ALREADY_EXISTS");
    byte[] bytes=content.getBytes(StandardCharsets.UTF_8);
    if(bytes.length<2||bytes.length>4096)throw new IOException("P85_SIZE_BOUND");
    File temp=new File(target.getParentFile(),target.getName()+".pending");
    if(temp.exists()&&!temp.delete())throw new IOException("P85_STALE_TEMP");
    try(FileOutputStream out=new FileOutputStream(temp,false)){
      out.write(bytes);out.getFD().sync();
    }
    if(target.exists()||!temp.renameTo(target)){
      temp.delete();throw new IOException("P85_COMMIT_RENAME_FAILED");
    }
  }
  public synchronized boolean begin(String id)throws IOException{
    validId(id);
    if(file(id,".done").exists() || file(id,".started").exists())return false;
    try {
      JSONObject start=new JSONObject();
      start.put("id",id);start.put("status","STARTED");
      createAtomic(file(id,".started"),start.toString());
    }catch(org.json.JSONException e){throw new IOException("P85_JOURNAL_JSON",e);}
    return true;
  }
  public synchronized void finish(String id,JSONObject terminal)throws IOException{
    validId(id);
    if(terminal==null||!id.equals(terminal.optString("id",""))||
       !terminal.has("ok")||!terminal.has("code") ||
       !terminal.has("outcomeUnknown")||!terminal.has("retrySafe"))
      throw new IOException("P85_MALFORMED_TERMINAL");
    String code=terminal.optString("code","");
    if(!code.matches("[A-Z][A-Z0-9_]{1,63}"))
      throw new IOException("P85_UNSAFE_CODE");
    if(!file(id,".started").isFile()||file(id,".done").exists())
      throw new IOException("P85_UNCLAIMED_OR_DOUBLE_COMPLETE");
    createAtomic(file(id,".done"),terminal.toString());
  }
  private static JSONObject interrupted(String id){
    JSONObject o=new JSONObject();
    try {
      o.put("id",id);
      o.put("ok",false);
      o.put("code",UNKNOWN);
      o.put("outcomeUnknown",true);
      o.put("retrySafe",false);
    }catch(org.json.JSONException impossible){throw new IllegalStateException(impossible);}
    return o;
  }
  /** Null means no prior call, while UNKNOWN means don't replay. */
  public synchronized JSONObject replayOrUnknown(String id)throws IOException{
    validId(id);
    File completed=file(id,".done");
    if(completed.isFile()){
      try{
        JSONObject terminal=new JSONObject(load(completed));
        if(!id.equals(terminal.optString("id","")) ||
           !terminal.has("ok")||!terminal.has("code")||
           !terminal.has("outcomeUnknown")||!terminal.has("retrySafe"))
          throw new IOException("P85_CORRUPT_COMPLETED_REPLY");
        return terminal;
      }catch(org.json.JSONException e){throw new IOException("P85_CORRUPT_JSON",e);}
    }
    if(file(id,".started").isFile())return interrupted(id);
    return null;
  }
}
