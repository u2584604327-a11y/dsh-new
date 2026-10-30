package com.dsh.android.p77;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.zip.GZIPOutputStream;

/** Adversarial synthetic TAR: never opens original private source. */
public final class P77TarAuditTest {
  private static int count;
  private static void check(boolean value,String why){
    count++;if(!value)throw new AssertionError("P77_"+why);
  }
  private static void ascii(byte[] dst,int off,int size,String text){
    byte[] b=text.getBytes(StandardCharsets.US_ASCII);
    if(b.length>size)throw new IllegalArgumentException("FIELD");
    System.arraycopy(b,0,dst,off,b.length);
  }
  private static void number(byte[] dst,int off,int size,long value){
    String s=Long.toOctalString(value);
    if(s.length()>size-1)throw new IllegalArgumentException("OCTAL");
    for(int i=off;i<off+size;i++)dst[i]=(byte)'0';
    ascii(dst,off+size-1-s.length(),s.length(),s);
    dst[off+size-1]=0;
  }
  private static void file(ByteArrayOutputStream out,String name,byte[] contents,int type)
      throws IOException {
    byte[] header=new byte[512];
    ascii(header,0,100,name);
    number(header,100,8,0644);
    number(header,108,8,0);number(header,116,8,0);
    number(header,124,12,contents.length);
    number(header,136,12,0);
    for(int i=148;i<156;i++)header[i]=(byte)' ';
    header[156]=(byte)type;
    ascii(header,257,6,"ustar");
    long sum=0;for(byte b:header)sum+=b&255;
    number(header,148,8,sum);
    out.write(header);out.write(contents);
    int pad=(512-contents.length%512)%512;
    out.write(new byte[pad]);
  }
  private static byte[] gzip(ByteArrayOutputStream tar)throws IOException{
    tar.write(new byte[1024]);
    ByteArrayOutputStream out=new ByteArrayOutputStream();
    try(GZIPOutputStream gz=new GZIPOutputStream(out)){gz.write(tar.toByteArray());}
    return out.toByteArray();
  }
  private static P77TarAudit.Result inspect(byte[] gzip)throws IOException{
    return P77TarAudit.inspectGzip(new ByteArrayInputStream(gzip));
  }
  private static boolean fails(byte[] gzip){
    try{inspect(gzip);return false;}catch(IOException expected){return true;}
  }
  public static void main(String[] args)throws Exception {
    ByteArrayOutputStream normal=new ByteArrayOutputStream();
    file(normal,"pkg/index.js","42".getBytes(StandardCharsets.UTF_8),'0');
    P77TarAudit.Result good=inspect(gzip(normal));
    check(good.members==1&&good.bytes==2&&good.addons==0,"synthetic_regular");
    check(good.treeSha256.matches("[0-9a-f]{64}"),"opaque_tree_hash");
    check(!good.isExactOriginal(),"synthetic_cannot_impersonate_source");
    ByteArrayOutputStream traversal=new ByteArrayOutputStream();
    file(traversal,"../escape","x".getBytes(StandardCharsets.UTF_8),'0');
    check(fails(gzip(traversal)),"traversal_denied");
    ByteArrayOutputStream duplicate=new ByteArrayOutputStream();
    file(duplicate,"same.js",new byte[]{1},'0');
    file(duplicate,"same.js",new byte[]{2},'0');
    check(fails(gzip(duplicate)),"duplicate_denied");
    ByteArrayOutputStream link=new ByteArrayOutputStream();
    file(link,"target",new byte[0],'2');
    check(fails(gzip(link)),"symlink_denied");
    byte[] corruptedHeader=normal.toByteArray();
    corruptedHeader[23]^=8;
    ByteArrayOutputStream wrong=new ByteArrayOutputStream();
    wrong.write(corruptedHeader);
    check(fails(gzip(wrong)),"corrupt_tar_header_checksum_denied");
    ByteArrayOutputStream nativeFile=new ByteArrayOutputStream();
    file(nativeFile,"pkg/native.node",new byte[]{1,2,3,4},'0');
    P77TarAudit.Result addon=inspect(gzip(nativeFile));
    check(addon.addons==1,"native_addon_count_only");
    System.out.println("P77_SYNTHETIC_CANONICAL_TAR_AND_SHA=PASS assertions="+count);
    System.out.println("P77_SYNTHETIC_ORIGINAL_PRIVATE_DATA_ACCESSED=NO");
  }
}
