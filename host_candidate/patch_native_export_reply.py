#!/usr/bin/env python3
"""P8 bounded original native logs-export reply privacy patch.

Only suppresses JSON 'bundlePath' exposure in LogCommandBridge.doExport.
Original DiagnosticBundle.build/other JSON status remain unchanged.
No filesystem permission change, no UID isolation, no APK signing.
"""
import argparse,hashlib,json,pathlib,struct,zlib
from androguard.core.dex import DEX
from patch_deny import sha
EXPECTED_P2="9a7cd89f4a5c86394770febf703a9345a44d8c12c39abec9d494635587d8f221"
HOST="Lcom/dsh/android/LogCommandBridge;"
NAME="doExport"
DESC="(Lorg/json/JSONObject;)V"
CODE_OFF=3287332
# Androguard instruction positions are byte offsets from code_item.insns.
TARGETS=((128,"const-string","bundlePath",4),
         (132,"invoke-virtual","Ljava/io/File;->getAbsolutePath()",6),
         (138,"move-result-object","",2),
         (140,"invoke-virtual","Lorg/json/JSONObject;->put(",6))
START=128
END=146

def apply(source):
    if sha(source)!=EXPECTED_P2:raise ValueError("UNVERIFIED_P2_COMBINED_DEX")
    dex=DEX(source)
    matches=[m for cls in dex.get_classes() if cls.get_name()==HOST
             for m in cls.get_methods() if m.get_name()==NAME and m.get_descriptor()==DESC]
    if len(matches)!=1:raise ValueError("ORIGINAL_LOG_EXPORT_METHOD_NOT_UNIQUE")
    method=matches[0]
    code=method.get_code()
    if method.get_code_off()!=CODE_OFF or code.get_insns_size()!=311:
        raise ValueError("NATIVE_EXPORT_PREIMAGE_CODE_SHAPE_CHANGED")
    instructions={pc:ins for pc,ins in method.get_instructions_idx()}
    if sum("bundlePath" in ins.get_output() for ins in instructions.values()) != 1:
        raise ValueError("BUNDLE_PATH_KEY_COUNT_CHANGED")
    for pc,op_name,ref,length in TARGETS:
        ins=instructions.get(pc)
        if ins is None or ins.get_name()!=op_name or ins.get_length()!=length:
            raise ValueError("NATIVE_EXPORT_INSTRUCTION_PREIMAGE_MISMATCH:"+str(pc))
        if ref and ref not in ins.get_output():
            raise ValueError("NATIVE_EXPORT_REFERENCE_PREIMAGE_MISMATCH:"+str(pc))
    if END-START!=sum(entry[3] for entry in TARGETS):
        raise AssertionError("TARGET_LENGTH_CHANGED")
    patch_start=CODE_OFF+16+START
    patch_end=CODE_OFF+16+END
    output=bytearray(source)
    output[patch_start:patch_end]=b"\x00"*(patch_end-patch_start)
    output[12:32]=hashlib.sha1(output[32:]).digest()
    struct.pack_into("<I",output,8,zlib.adler32(output[12:])&0xffffffff)
    changed={n for n,(x,y) in enumerate(zip(source,output)) if x!=y}
    allowed=set(range(8,32))|set(range(patch_start,patch_end))
    if len(source)!=len(output) or not changed<=allowed:
        raise AssertionError("UNAUTHORIZED_DEX_BYTE_CHANGED")
    check=DEX(bytes(output))
    mutated=[m for cls in check.get_classes() if cls.get_name()==HOST
             for m in cls.get_methods() if m.get_name()==NAME and m.get_descriptor()==DESC][0]
    after={pc:ins for pc,ins in mutated.get_instructions_idx()}
    for pc in range(START,END,2):
        if after[pc].get_name()!="nop":
            raise AssertionError("REMOVED_NATIVE_PATH_INVOKES_STILL_PRESENT")
    if mutated.get_code_off()!=CODE_OFF or mutated.get_code().get_insns_size()!=311:
        raise AssertionError("CODE_HEADER_OR_METHOD_CHANGED")
    for cls in dex.get_classes():
        for m in cls.get_methods():
            if m.get_code_off()==0:continue
            pos=m.get_code_off()+16
            length=m.get_code().get_insns_size()*2
            if (m.get_class_name(),m.get_name(),m.get_descriptor())==(HOST,NAME,DESC):
                if source[pos:patch_start]!=output[pos:patch_start] or source[patch_end:pos+length]!=output[patch_end:pos+length]:
                    raise AssertionError("OTHER_EXPORT_INSTRUCTIONS_CHANGED")
            elif source[pos:pos+length]!=output[pos:pos+length]:
                raise AssertionError("UNAUTHORIZED_METHOD_BODY_CHANGED")
    report={"INPUT_P2_DEX_SHA256":sha(source),"P8_DEX_SHA256":sha(output),
       "SCOPED_METHOD":HOST+NAME+DESC,"ORIGINAL_METHOD_CODE_OFF":CODE_OFF,
       "BYTE_RANGE_REMOVED":[patch_start,patch_end],
       "PATCHED_PATH_JSON_WRITE_BYTES":18,
       "REPLACED_WITH_NOP_CODE_UNITS":9,
       "ORIGINAL_BUNDLE_GENERATION_PRESERVED":True,
       "ORIGINAL_FILE_SIZE_JSON_WRITE_PRESERVED":True,
       "OTHER_METHOD_BODIES_UNCHANGED":True,
       "NATIVE_EXPORT_REPLY_BUNDLE_PATH_REMOVED":"PASS_STATIC",
       "NODE_SAME_UID_FILE_ACCESS":"NOT_SOLVED",
       "FULL_DIAGNOSTIC_UPLOAD_GATE":"NOT_VERIFIED",
       "APK_BUILT":"NO","ART":"NOT_VERIFIED"}
    return bytes(output),report

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("p2_dex");cli.add_argument("--output",required=True)
    cli.add_argument("--report",required=True)
    args=cli.parse_args();patched,r=apply(pathlib.Path(args.p2_dex).read_bytes())
    pathlib.Path(args.output).write_bytes(patched)
    pathlib.Path(args.report).write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(r,indent=2))
