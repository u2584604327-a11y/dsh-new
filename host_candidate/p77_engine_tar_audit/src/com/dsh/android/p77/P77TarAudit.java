package com.dsh.android.p77;

import com.dsh.android.p78.P78ModuleSlot;

import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.StandardCharsets;
import java.nio.charset.CodingErrorAction;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.zip.GZIPInputStream;

/** Streaming source-only TAR verification. Never extracts or executes scripts. */
public final class P77TarAudit {
  public static final String EXPECTED_TREE=
    "b2c7e52890351c4d1a3200c67ccb9be6154389a20da0b0b590d16676ce47b1e1";
  public static final int EXPECTED_MEMBERS=30411, EXPECTED_ADDONS=9;
  public static final long EXPECTED_REGULAR_BYTES=262498938L;
  private static final int BLOCK=512;
  private static final long MAX_MEMBER=128L*1024*1024, MAX_TOTAL=4L*1024*1024*1024;
  private P77TarAudit(){}
  public static final class Result {
    public final int members,addons;
    public final long bytes;
    public final String treeSha256;
    private Result(int m,int a,long b,String h){
      members=m;addons=a;bytes=b;treeSha256=h;
    }
    public boolean isExactOriginal(){
      return members==EXPECTED_MEMBERS && addons==EXPECTED_ADDONS &&
             bytes==EXPECTED_REGULAR_BYTES && EXPECTED_TREE.equals(treeSha256);
    }
  }
  private static MessageDigest digest(){
    try{return MessageDigest.getInstance("SHA-256");}
    catch(Exception e){throw new IllegalStateException("P77_SHA256_UNAVAILABLE");}
  }
  private static String hex(byte[] bytes){
    char[] symbols="0123456789abcdef".toCharArray();
    char[] out=new char[bytes.length*2];int i=0;
    for(byte b:bytes){int v=b&255;out[i++]=symbols[v>>>4];out[i++]=symbols[v&15];}
    return new String(out);
  }
  private static int fill(InputStream in,byte[] b)throws IOException{
    int count=0;
    while(count<b.length){
      int n=in.read(b,count,b.length-count);
      if(n<0)break;
      if(n>0)count+=n;
    }
    return count;
  }
  private static void readExact(InputStream in,byte[] b)throws IOException{
    if(fill(in,b)!=b.length)throw new EOFException("P77_TRUNCATED_TAR");
  }
  private static boolean zero(byte[] b){
    for(byte v:b)if(v!=0)return false;return true;
  }
  private static String decoded(byte[] b,int start,int len)throws IOException{
    int end=start+len;
    for(int i=start;i<start+len;i++)if(b[i]==0){end=i;break;}
    try {
      return StandardCharsets.UTF_8.newDecoder()
        .onMalformedInput(CodingErrorAction.REPORT)
        .onUnmappableCharacter(CodingErrorAction.REPORT)
        .decode(ByteBuffer.wrap(b,start,end-start)).toString();
    }catch(CharacterCodingException e){
      throw new IOException("P77_BAD_MEMBER_NAME_UTF8",e);
    }
  }
  private static long octal(byte[] h,int start,int len)throws IOException{
    if((h[start]&0x80)!=0)throw new IOException("P77_UNSUPPORTED_BASE256");
    long v=0;boolean begun=false;
    for(int i=start;i<start+len;i++){
      int c=h[i]&255;
      if(c==0||c==32){if(begun)break;continue;}
      if(c<48||c>55)throw new IOException("P77_BAD_OCTAL");
      begun=true;v=(v<<3)+(c-48);
      if(v<0)throw new IOException("P77_NUMERIC_OVERFLOW");
    }
    return v;
  }
  private static void checksum(byte[] h)throws IOException{
    long expected=octal(h,148,8),calculated=0;
    for(int i=0;i<BLOCK;i++)
      calculated+=(i>=148&&i<156)?32:(h[i]&255);
    if(expected!=calculated)throw new IOException("P77_TAR_HEADER_CHECKSUM");
  }
  private static String canonical(String name)throws IOException{
    if(name==null||name.isEmpty())throw new IOException("P77_EMPTY_PATH");
    if(name.startsWith("./"))name=name.substring(2);
    while(name.endsWith("/"))name=name.substring(0,name.length()-1);
    if(name.isEmpty()||name.length()>1024||name.startsWith("/")||
       name.indexOf('\\')>=0)throw new IOException("P77_UNSAFE_MEMBER_PATH");
    for(int i=0;i<name.length();i++)
      if(name.charAt(i)<32||name.charAt(i)==127)
        throw new IOException("P77_CONTROL_IN_PATH");
    for(String item:name.split("/",-1))
      if(item.isEmpty()||item.equals(".")||item.equals(".."))
        throw new IOException("P77_PATH_TRAVERSAL");
    return name;
  }
  private static void consume(InputStream in,long bytes,MessageDigest md)throws IOException{
    consume(in,bytes,md,null);
  }
  private static void consume(InputStream in,long bytes,MessageDigest md,
                              P78ModuleSlot selected)throws IOException{
    byte[] buffer=new byte[65536];long remaining=bytes;
    while(remaining>0){
      int n=in.read(buffer,0,(int)Math.min(remaining,buffer.length));
      if(n<0)throw new EOFException("P77_TRUNCATED_MEMBER");
      if(n==0)continue;
      if(md!=null)md.update(buffer,0,n);
      if(selected!=null)selected.accept(buffer,0,n);
      remaining-=n;
    }
  }
  private static void pad(InputStream in,long bytes)throws IOException{
    consume(in,(BLOCK-bytes%BLOCK)%BLOCK,null);
  }
  private static byte[] extended(InputStream in,long bytes)throws IOException{
    if(bytes<0||bytes>65536)throw new IOException("P77_PAX_TOO_LARGE");
    byte[] raw=new byte[(int)bytes];
    readExact(in,raw);pad(in,bytes);
    return raw;
  }
  private static Map<String,String> pax(byte[] raw)throws IOException{
    Map<String,String> attrs=new HashMap<>();int offset=0;
    while(offset<raw.length){
      int space=-1;
      for(int i=offset;i<raw.length&&i<offset+12;i++)
        if(raw[i]==' '){space=i;break;}
      if(space<0)throw new IOException("P77_PAX_LENGTH");
      int size;
      try{size=Integer.parseInt(new String(raw,offset,space-offset,
                                            StandardCharsets.US_ASCII));}
      catch(NumberFormatException e){throw new IOException("P77_PAX_NUMBER",e);}
      if(size<4||size>raw.length-offset||raw[offset+size-1]!='\n')
        throw new IOException("P77_PAX_RECORD_SIZE");
      String pair=decoded(raw,space+1,size-(space-offset)-2);
      int equals=pair.indexOf('=');
      if(equals<1)throw new IOException("P77_PAX_KEY");
      attrs.put(pair.substring(0,equals),pair.substring(equals+1));
      offset+=size;
    }
    return attrs;
  }
  public static Result inspectGzip(InputStream source)throws IOException{
    return inspectGzip(source,null);
  }
  public static Result inspectGzip(InputStream source,
                                    P78ModuleSlot selectedModule)throws IOException{
    try(GZIPInputStream tar=new GZIPInputStream(source,65536)){
      MessageDigest root=digest();
      root.update("P54_IMMUTABLE_ENGINE_TREE_V1\0".getBytes(StandardCharsets.US_ASCII));
      Set<String> seen=new HashSet<>();
      byte[] header=new byte[BLOCK];int members=0,addons=0;long total=0;
      String longName=null;Map<String,String> pending=new HashMap<>();
      for(;;){
        int n=fill(tar,header);
        if(n==0)throw new IOException("P77_NO_TAR_TERMINATOR");
        if(n!=BLOCK)throw new IOException("P77_TRUNCATED_HEADER");
        if(zero(header)){
          byte[] second=new byte[BLOCK];readExact(tar,second);
          if(!zero(second))throw new IOException("P77_INVALID_TAR_TERMINATOR");
          break;
        }
        checksum(header);
        int type=header[156]&255;
        long size=octal(header,124,12);
        if(size<0||size>MAX_MEMBER)throw new IOException("P77_TAR_ITEM_TOO_LARGE");
        if(type=='x'||type=='g'){
          Map<String,String> attrs=pax(extended(tar,size));
          if(type=='g'){
            if(attrs.containsKey("path")||attrs.containsKey("size"))
              throw new IOException("P77_GLOBAL_PATH_OVERRIDE");
          }else pending.putAll(attrs);
          continue;
        }
        if(type=='L'){
          byte[] longData=extended(tar,size);
          longName=decoded(longData,0,longData.length);
          continue;
        }
        if(type!=0&&type!='0'&&type!='5')
          throw new IOException("P77_LINK_OR_SPECIAL_NOT_ALLOWED");
        String name=decoded(header,0,100);
        String prefix=decoded(header,345,155);
        if(!prefix.isEmpty())name=prefix+"/"+name;
        if(longName!=null){name=longName;longName=null;}
        if(pending.containsKey("path"))name=pending.get("path");
        if(pending.containsKey("size")){
          try{size=Long.parseLong(pending.get("size"));}
          catch(NumberFormatException bad){throw new IOException("P77_PAX_SIZE",bad);}
        }
        pending.clear();
        name=canonical(name);
        if(!seen.add(name))throw new IOException("P77_DUPLICATE_CANONICAL_NAME");
        if(++members>100000||size<0||size>MAX_MEMBER)
          throw new IOException("P77_COUNT_OR_SIZE_LIMIT");
        boolean directory=type=='5';
        if(directory&&size!=0)throw new IOException("P77_DIRECTORY_PAYLOAD");
        if(!directory){
          total+=size;
          if(total>MAX_TOTAL)throw new IOException("P77_TOTAL_DECOMPRESSED_LIMIT");
        }
        boolean selected=selectedModule!=null &&
             selectedModule.begin(name,directory,size);
        MessageDigest member=digest();
        consume(tar,size,member,selected?selectedModule:null);
        if(selected)selectedModule.endMember();
        pad(tar,size);
        byte[] path=name.getBytes(StandardCharsets.UTF_8);
        root.update(ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN)
                  .putInt(path.length).array());
        root.update(path);
        root.update((byte)(directory?1:0));
        root.update(ByteBuffer.allocate(8).order(ByteOrder.BIG_ENDIAN)
                  .putLong(size).array());
        root.update(member.digest());
        if(!directory&&name.endsWith(".node"))addons++;
      }
      if(longName!=null||!pending.isEmpty())
        throw new IOException("P77_DANGLING_EXTENDED_HEADER");
      Result complete=new Result(members,addons,total,hex(root.digest()));
      if(selectedModule!=null)selectedModule.sealOriginal(complete);
      return complete;
    }
  }
}
