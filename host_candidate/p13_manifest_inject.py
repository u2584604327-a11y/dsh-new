"""P13 native AndroidX Startup metadata injection into exact v138 binary AXML.
One <meta-data> child inside existing InitializationProvider only.
No application IDs, permissions, authorities, exported bits or version changes.
"""
import hashlib,struct

BASELINE_SHA="fa9e134048fc416e267106600af7bdf28ca1f9dd46e4cf055f1e6a87b69d5987"
CLASS="com.dsh.p12.P13NativeReviewInitializer"
PROVIDER="androidx.startup.InitializationProvider"
DISCOVERY="androidx.startup"
def u32(b,o):return struct.unpack_from("<I",b,o)[0]
def chunk(b,o):
    t,h,s=struct.unpack_from("<HHI",b,o)
    if h<8 or s<h or o+s>len(b):raise ValueError("BAD_AXML_CHUNK")
    return t,h,s
def strings_from_pool(b):
    if chunk(b,8)[0]!=1:raise ValueError("STRING_POOL_MISSING")
    n,styles,flags,start,style_start=struct.unpack_from("<5I",b,16)
    if flags or styles or style_start or start!=28+4*n:raise ValueError("UNKNOWN_AXML_STRING_POOL")
    out=[]
    for i in range(n):
        pos=8+start+u32(b,8+28+4*i)
        size=struct.unpack_from("<H",b,pos)[0]
        if size>=0x8000:raise ValueError("LONG_UTF16_UNSUPPORTED")
        if b[pos+2+2*size:pos+4+2*size]!=b"\0\0":raise ValueError("UTF16_NO_TERMINATOR")
        out.append(b[pos+2:pos+2+2*size].decode("utf-16le"))
    return out
def attrs(b,off,ss):
    begin,width,count=struct.unpack_from("<HHH",b,off+24)
    if width!=20:raise ValueError("AXML_ATTR_WIDTH")
    out={}
    for i in range(count):
        pos=off+16+begin+i*width
        ns,name,raw,tsize,r0,typ,data=struct.unpack_from("<IIIHBBI",b,pos)
        if tsize!=8 or name>=len(ss):raise ValueError("AXML_BAD_TYPED_ATTR")
        out[ss[name]]=(ss[data] if typ==3 and data<len(ss) else data,pos,typ,raw,data)
    return out
def select_template(b,ss):
    pos=8;stack=[];start=None;end=None;choices=[];meta_start=None
    while pos<len(b):
        typ,hs,size=chunk(b,pos)
        if typ==0x102:
            n=ss[u32(b,pos+20)]
            a=attrs(b,pos,ss)
            if n=="provider" and a.get("name",(None,))[0]==PROVIDER:
                if start is not None:raise ValueError("TWO_STARTUP_PROVIDERS")
                start=pos
            if n=="meta-data" and start is not None and stack and stack[-1]==("provider",start):
                if a.get("name",(None,))[0]==CLASS:raise ValueError("P13_ALREADY_REGISTERED")
                if a.get("value",(None,))[0]==DISCOVERY:choices.append(pos)
            stack.append((n,pos))
        elif typ==0x103:
            if not stack:raise ValueError("AXML_UNBALANCED")
            n,begin=stack.pop()
            if n=="meta-data" and begin in choices:
                if pos!=begin+chunk(b,begin)[2]:raise ValueError("NESTED_STARTUP_METADATA")
                meta_start=(begin,pos+size)
            if n=="provider" and begin==start:end=pos
        pos+=size
    if stack or end is None or meta_start is None:raise ValueError("STARTUP_PROVIDER_METADATA_MISSING")
    return end,bytearray(b[meta_start[0]:meta_start[1]])
def inject(b):
    if hashlib.sha256(b).hexdigest()!=BASELINE_SHA:raise ValueError("V138_MANIFEST_SHA_MISMATCH")
    if chunk(b,0)!=(3,8,len(b)):raise ValueError("BAD_MANIFEST_HEADER")
    ss=strings_from_pool(b)
    if CLASS in ss:raise ValueError("P13_STRING_ALREADY_PRESENT")
    at,src=select_template(b,ss)
    a=attrs(src,0,ss)
    if a["value"][0]!=DISCOVERY or a["name"][2]!=3:raise ValueError("METADATA_TEMPLATE_WRONG")
    pos=a["name"][1];idx=len(ss)
    struct.pack_into("<I",src,pos+8,idx)
    struct.pack_into("<I",src,pos+16,idx)
    oldpoollen=chunk(b,8)[2];pool=b[8:8+oldpoollen]
    oldcount=u32(pool,8);start=u32(pool,20)
    olddata=pool[start:]
    encoded=struct.pack("<H",len(CLASS))+CLASS.encode("utf-16le")+b"\0\0"
    raw=olddata+encoded
    raw+=b"\0"*((-len(raw))%4)
    pool2=bytearray(pool[:28])
    struct.pack_into("<I",pool2,8,oldcount+1)
    struct.pack_into("<I",pool2,20,start+4)
    pool2+=pool[28:start]+struct.pack("<I",len(olddata))+raw
    struct.pack_into("<I",pool2,4,len(pool2))
    output=bytearray(b[:8]+pool2+b[8+oldpoollen:at]+src+b[at:])
    struct.pack_into("<I",output,4,len(output))
    output=bytes(output)
    if strings_from_pool(output)!=ss+[CLASS]:raise AssertionError("P13_STRING_POOL_CORRUPT")
    if chunk(output,0)!=(3,8,len(output)):raise AssertionError("P13_MANIFEST_BAD_SIZE")
    count=0;pos=8
    while pos<len(output):
        t,h,size=chunk(output,pos)
        if t==0x102 and strings_from_pool(output)[u32(output,pos+20)]=="meta-data":
            a=attrs(output,pos,ss+[CLASS])
            if a.get("name",(None,))[0]==CLASS:
                if a["value"][0]!=DISCOVERY:raise AssertionError("INVALID_STARTUP_MARKER")
                count+=1
        pos+=size
    if count!=1:raise AssertionError("P13_META_NOT_UNIQUE")
    return output,{
      "ORIGINAL_MANIFEST_SHA256":BASELINE_SHA,
      "P13_NEW_MANIFEST_SHA256":hashlib.sha256(output).hexdigest(),
      "P13_ANDROIDX_META_DATA_COUNT":count,
      "P13_BINARY_AXML_STRUCTURE":"PASS_STATIC",
      "P13_OTHER_MANIFEST_CHUNKS":"ORIGINAL_BYTES_UNMODIFIED",
      "P13_ANDROID_RUNTIME":"NOT_YET_VERIFIED"}
