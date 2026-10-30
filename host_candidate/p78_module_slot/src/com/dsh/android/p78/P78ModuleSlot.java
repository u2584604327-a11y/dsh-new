package com.dsh.android.p78;

import com.dsh.android.p77.P77TarAudit;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;

/**
 * Source-only isolated-worker module slot. Capture at most one bounded original
 * JS module during complete P77 archive scan. Never execute or export to host.
 * It is released ONLY after exact canonical P54 root and byte counts match.
 */
public final class P78ModuleSlot {
  public static final int MAX_JS_BYTES=65536;
  private final String session;
  private byte[] buffer;
  private int filled;
  private String opaqueId;
  private String moduleSha;
  private int declared=-1;
  private boolean collecting,finished,sealed,taken;
  public P78ModuleSlot(String hostGeneratedSession) {
    if(hostGeneratedSession==null ||
       !hostGeneratedSession.matches("[0-9a-f]{64}"))
      throw new SecurityException("P78_TRUSTED_SESSION_REQUIRED");
    session=hostGeneratedSession;
  }
  private static MessageDigest digest() {
    try{return MessageDigest.getInstance("SHA-256");}
    catch(Exception e){throw new IllegalStateException("P78_HASH_UNAVAILABLE");}
  }
  private static String hex(byte[] b) {
    char[] out=new char[b.length*2];
    final String abc="0123456789abcdef";
    for(int i=0;i<b.length;i++){
      int value=b[i]&255;
      out[2*i]=abc.charAt(value>>>4);
      out[2*i+1]=abc.charAt(value&15);
    }
    return new String(out);
  }
  public boolean begin(String canonicalName,boolean directory,long size)
      throws IOException {
    if(opaqueId!=null||collecting||finished||directory||
       size<=0||size>MAX_JS_BYTES)return false;
    if(!canonicalName.endsWith(".js") && !canonicalName.endsWith(".cjs") &&
       !canonicalName.endsWith(".mjs"))return false;
    if(canonicalName.indexOf('\\')>=0||canonicalName.startsWith("/")||
       canonicalName.equals("..")||canonicalName.startsWith("../")||
       canonicalName.contains("/../")||canonicalName.contains("/./")||
       canonicalName.startsWith("./")||canonicalName.contains("//"))
      throw new IOException("P78_UNSAFE_SOURCE_NAME");
    opaqueId=hex(digest().digest(canonicalName.getBytes(StandardCharsets.UTF_8)));
    declared=(int)size;
    buffer=new byte[declared];filled=0;
    collecting=true;
    return true;
  }
  public void accept(byte[] source,int offset,int length)throws IOException {
    if(!collecting||sealed||finished||source==null ||
       offset<0||length<0||offset>source.length-length||
       filled+length>declared)
      throw new IOException("P78_MODULE_WINDOW_BOUNDS");
    System.arraycopy(source,offset,buffer,filled,length);
    filled+=length;
  }
  public void endMember()throws IOException {
    if(!collecting||finished||filled!=declared)
      throw new IOException("P78_MODULE_SHORT_READ");
    collecting=false;finished=true;
    moduleSha=hex(digest().digest(buffer));
  }
  /** The only production sealing function. Synthetic archives MUST NOT seal. */
  public void sealOriginal(P77TarAudit.Result source)throws IOException {
    if(source==null || !source.isExactOriginal() || !finished||
       collecting || moduleSha==null || declared<=0 ||
       filled!=declared || sealed)
      throw new IOException("P78_EXACT_ORIGINAL_ROOT_OR_WINDOW_REQUIRED");
    sealed=true;
  }
  public boolean isReady(){return sealed&&!taken;}
  public String opaqueId(){
    if(!sealed||opaqueId==null)throw new SecurityException("P78_NOT_VERIFIED");
    return opaqueId;
  }
  public String moduleSha(){
    if(!sealed||moduleSha==null)throw new SecurityException("P78_NOT_VERIFIED");
    return moduleSha;
  }
  /** Only call from already authenticated isolated P76 worker. One use only. */
  public byte[] takeOnce(String authenticatedSession,String requestedId) {
    if(!sealed||taken||authenticatedSession==null||
       !session.equals(authenticatedSession)||requestedId==null||
       !requestedId.equals(opaqueId))
      throw new SecurityException("P78_NOT_AUTHORIZED_OR_ALREADY_CONSUMED");
    taken=true;
    byte[] bytes=buffer;
    buffer=null;filled=0;
    return bytes;
  }
}
