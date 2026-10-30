package com.dsh.android.p43;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * P46 minimal canonical 2-part, read-only package manifest.
 * ONLY two bundled synthetic fixtures are currently authorized.
 * No actual DSH scripts, secrets, or executable runtime deployment.
 */
public final class P46ResourceBundle {
  public static final String V="p46-1";
  public static final int COUNT=2;
  public static final int MAX_ONE=4096;
  public static final int MAX_TOTAL=8192;
  public static final String NAME0="fixture/bootstrap.js";
  public static final String NAME1="fixture/settings.json";
  public static final class Part {
    public final String name;
    public final int size;
    public final String sha256;
    private Part(String name,int size,String sha256) {
      this.name=name;this.size=size;this.sha256=sha256;
    }
  }
  public final Part[] parts;
  private final String wire;

  private P46ResourceBundle(Part[] parts,String wire) {
    this.parts=parts.clone();this.wire=wire;
  }
  public String wire(){return wire;}
  public static String digest(byte[] bytes) {
    try {
      byte[] d=MessageDigest.getInstance("SHA-256").digest(bytes);
      StringBuilder sb=new StringBuilder(64);
      for(byte b:d)sb.append(String.format(Locale.ROOT,"%02x",b&255));
      return sb.toString();
    }catch(Exception e){throw new IllegalStateException("P46_DIGEST_UNAVAILABLE",e);}
  }
  private static Part part(String name,byte[] content){
    if(content==null || content.length<=0 || content.length>MAX_ONE)
      throw new IllegalArgumentException("P46_SIZE_REJECTED");
    return new Part(name,content.length,digest(content));
  }
  public static P46ResourceBundle fromFixture(byte[] bootstrap,byte[] settings) {
    Part[] p={part(NAME0,bootstrap),part(NAME1,settings)};
    if(p[0].size+p[1].size>MAX_TOTAL)
      throw new IllegalArgumentException("P46_PACKAGE_TOO_LARGE");
    String wire=V+"|"+encode(p[0])+"|"+encode(p[1]);
    return new P46ResourceBundle(p,wire);
  }
  private static String encode(Part p){return p.name+","+p.size+","+p.sha256;}
  public static P46ResourceBundle parse(String raw) {
    if(raw==null || raw.length()>300 || raw.indexOf('\n')>=0 ||
       raw.indexOf('\r')>=0 || raw.indexOf('\u0000')>=0)
      throw new IllegalArgumentException("P46_MANIFEST_INVALID");
    String[] chunks=raw.split("\\|",-1);
    if(chunks.length!=3 || !V.equals(chunks[0]))
      throw new IllegalArgumentException("P46_MANIFEST_VERSION_OR_COUNT");
    String[] names={NAME0,NAME1};
    Part[] parts=new Part[COUNT];
    int total=0;
    for(int i=0;i<COUNT;i++){
      String[] f=chunks[i+1].split(",",-1);
      if(f.length!=3 || !names[i].equals(f[0]) ||
         !f[1].matches("[1-9][0-9]{0,3}") ||
         !f[2].matches("[0-9a-f]{64}"))
        throw new IllegalArgumentException("P46_NONCANONICAL_PART");
      int size;
      try {size=Integer.parseInt(f[1]);}
      catch(NumberFormatException bad){throw new IllegalArgumentException("P46_BAD_SIZE",bad);}
      if(size<=0 || size>MAX_ONE || total>MAX_TOTAL-size)
        throw new IllegalArgumentException("P46_SIZE_LIMIT");
      total+=size; parts[i]=new Part(f[0],size,f[2]);
    }
    String canonical=V+"|"+encode(parts[0])+"|"+encode(parts[1]);
    if(!canonical.equals(raw))
      throw new IllegalArgumentException("P46_MANIFEST_NOT_CANONICAL");
    return new P46ResourceBundle(parts,raw);
  }
  /**
   * Fail closed on short/truncated, overlong, malformed or tampered data.
   * Does not expose bytes or paths to caller. Caller owns the FD lifecycle.
   */
  public static boolean verifyPart(InputStream input,Part expected) throws IOException {
    if(input==null || expected==null)return false;
    ByteArrayOutputStream out=new ByteArrayOutputStream(Math.min(expected.size,256));
    byte[] buf=new byte[512];int n;
    while((n=input.read(buf))!=-1){
      if(n>expected.size-out.size())return false;
      out.write(buf,0,n);
    }
    byte[] bytes=out.toByteArray();
    return bytes.length==expected.size && digest(bytes).equals(expected.sha256);
  }
  public String fingerprint() {
    return digest(wire.getBytes(StandardCharsets.US_ASCII));
  }
}
