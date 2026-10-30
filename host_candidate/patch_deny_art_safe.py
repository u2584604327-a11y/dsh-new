"""ART-safe-candidate v2: bounded native diagnostic default deny, NO array-data payloads.

Why: original P2 generated fill-array-data-payload across an existing DEX try
boundary; Android 35 ART rejected LogUploader.retryPending with VerifyError.
This variant never writes payload pseudo-instructions: all unused code units
are ordinary NOPs, so try starts/ends remain actual instruction boundaries.

Conservative source candidate only. Must pass real Android ART before acceptance.
"""
import hashlib,struct,zlib
from androguard.core.dex import DEX
from patch_deny import EXPECTED_DEX,EXPECTED_APK,SPECS,sha,invoke

def _try_ranges(raw,offset,insns_size,tries_size):
    if not tries_size:return []
    at=offset+16+insns_size*2+(2 if insns_size%2 else 0)
    return [(struct.unpack_from("<IHH",raw,at+i*8)[0],
             struct.unpack_from("<IHH",raw,at+i*8)[1])
            for i in range(tries_size)]

def apply_art_safe(original):
    if sha(original)!=EXPECTED_DEX:
        raise ValueError("UNEXPECTED_V138_CLASSES_DEX")
    dex=DEX(original)
    refs={(m.get_class_name(),m.get_name(),m.get_descriptor()):i
          for i,m in enumerate(dex.get_methods())}
    types={dex.get_cm_type(i):i for i in range(struct.unpack_from("<I",original,64)[0])}
    log=refs['Lcom/dsh/android/log/DshLog;','w','(Ljava/lang/String; Ljava/lang/String;)I']
    box=refs['Ljava/lang/Boolean;','valueOf','(Z)Ljava/lang/Boolean;']
    pair=refs['Lkotlin/Pair;','<init>','(Ljava/lang/Object; Ljava/lang/Object;)V']
    cb=refs['Lkotlin/jvm/functions/Function2;','invoke',
            '(Ljava/lang/Object; Ljava/lang/Object;)Ljava/lang/Object;']
    # Reuse existing non-sensitive string; creates no new DEX pool reference.
    strings=dex.get_strings()
    message=next((s for s in ('UPLOAD_DENIED','diagnostic upload denied',
        '上传已禁用','LogUploader','DSH') if s in strings),'DSH')
    tag=strings.index('DSH'); msg=strings.index(message)
    if tag>65535 or msg>65535:raise ValueError("STRING_INDEX_JUMBO_UNSUPPORTED")
    out=bytearray(original)
    allowed=set(range(8,32));reports=[]
    for c in dex.get_classes():
        for m in c.get_methods():
            key=(c.get_name(),m.get_name())
            if key not in SPECS:continue
            kind=SPECS[key];code=m.get_code()
            size=code.get_insns_size();off=m.get_code_off();start=off+16
            # const-string v0 message, const-string v1 DSH; DshLog.w(tag,message).
            cu=[0x001a,msg,0x011a,tag]+invoke(0x71,log,[1,0])
            if kind in ('pair','callback'):
                cu += [0x0212]+invoke(0x71,box,[2])+[0x020c]
            if kind=='pair':
                cu += [0x0322,types['Lkotlin/Pair;']]
                cu += invoke(0x70,pair,[3,2,0])+[0x0311]
            elif kind=='callback':
                callback=code.get_registers_size()-1
                cu += invoke(0x72,cb,[callback,2,0])+[0x000e]
            else:
                cu += [0x000e]
            handlers=[]
            if code.get_handlers():
                for h in code.get_handlers().get_list():
                    handlers += [x.get_addr() for x in h.get_handlers()]
                    if h.get_size()<=0: handlers.append(h.get_catch_all_addr())
            handlers=sorted(set(handlers))
            if not all(h>=len(cu) and h+2<=size for h in handlers):
                raise ValueError("TRY_HANDLER_OVERLAPS_DENY_PREFIX")
            if size < len(cu):
                raise ValueError("INSUFFICIENT_ORIGINAL_METHOD_BODY")
            body=[0]*size
            body[:len(cu)]=cu
            for h in handlers:
                body[h:h+2]=[0x000d,0x0027]
            out[start:start+size*2]=struct.pack("<"+"H"*size,*body)
            allowed.update(range(start,start+size*2))
            reports.append({"class":key[0],"name":key[1],
                "kind":kind,"code_off":off,"prefix_cu":len(cu),
                "insns_size":size,"try_ranges":_try_ranges(original,off,size,code.get_tries_size()),
                "handlers":handlers,"no_array_payload":True})
    if len(reports)!=4:raise AssertionError("EXPECTED_FOUR_DEFAULT_DENY_METHODS")
    out[12:32]=hashlib.sha1(out[32:]).digest()
    struct.pack_into("<I",out,8,zlib.adler32(out[12:]) & 0xffffffff)
    result=bytes(out)
    if any(x!=y and i not in allowed for i,(x,y) in enumerate(zip(original,result))):
        raise AssertionError("UNAUTHORIZED_DEFAULT_DENY_BYTE_CHANGE")
    decoded=DEX(result)
    candidate_methods={(m.get_class_name(),m.get_name()):m
                       for c in decoded.get_classes() for m in c.get_methods()}
    for report in reports:
        m=candidate_methods[(report['class'],report['name'])]
        starts={pc//2 for pc,_ in m.get_instructions_idx()}
        starts.add(m.get_code().get_insns_size())
        if any(a not in starts or a+b not in starts
               for a,b in report['try_ranges']):
            raise AssertionError("ART_TRY_BOUNDARY_NOT_INSTRUCTION_START")
        if any(h not in starts for h in report['handlers']):
            raise AssertionError("CATCH_HANDLER_NOT_INSTRUCTION_START")
        if any(i.get_name().startswith('fill-array-data')
               for _,i in m.get_instructions_idx()):
            raise AssertionError("ARRAY_PAYLOAD_STILL_PRESENT")
    return result,{"status":"ART_SAFE_DENY_CANDIDATE_NOT_ART_TESTED",
          "message_existing_literal":message,
          "sha256":sha(result),"scoped_methods":reports,
          "TRY_START_END_AND_HANDLER_ALIGNMENT":"PASS_STATIC",
          "ARRAY_DATA_PSEUDO_INSTRUCTIONS":"NONE",
          "LEGACY_DIAGNOSTIC_UPLOAD":"DEFAULT_DENY",
          "ART":"NOT_VERIFIED","APK_SIGNED":"NO"}
