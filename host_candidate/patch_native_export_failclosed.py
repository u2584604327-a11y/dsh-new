"""P9 native legacy diagnostic export fail-close in original DEX.

After exact SHA-locked ART-safe P1..P8, remove the call to
DiagnosticBundle.build$default inside LogCommandBridge.doExport only.
Replace its move-result-object v3 with NOP. Set v3=null and preserve the
original following if-eqz branch into the existing export failure path.

No new methods/strings/IDs; no file deletion or normal user attachment changes.
Until a trusted P5 on-device preview is integrated, exporting complete raw
diagnostics must be explicitly unavailable, not just hide bundlePath.
"""
import hashlib,struct,zlib
from androguard.core.dex import DEX
from patch_deny import sha

P8_INPUT_SHA="086d0e431515d9f5072109e96a94cbbe7f37c578f1cc68722bcd787881d1acb3"
OWNER="Lcom/dsh/android/LogCommandBridge;"
METHOD="doExport"
SIGNATURE="(Lorg/json/JSONObject;)V"
CODE_OFF=3287332
# Insn offset within code_item.insns, bytes. Original:
# 116 invoke-static/range ... DiagnosticBundle.build$default (6)
# 122 move-result-object v3 (2)
# 124 if-eqz v3, existing error/failure path
BEGIN=116
END=124

def apply(source):
    if sha(source)!=P8_INPUT_SHA: raise ValueError("UNKNOWN_P8_PREIMAGE")
    dex=DEX(source)
    matches=[m for cls in dex.get_classes() if cls.get_name()==OWNER
             for m in cls.get_methods()
             if m.get_name()==METHOD and m.get_descriptor()==SIGNATURE]
    if len(matches)!=1:raise ValueError("NATIVE_EXPORT_METHOD_NOT_UNIQUE")
    m=matches[0];code=m.get_code()
    if m.get_code_off()!=CODE_OFF or code.get_insns_size()!=311:
        raise ValueError("NATIVE_EXPORT_METHOD_SHAPE_CHANGED")
    ins={pc:instr for pc,instr in m.get_instructions_idx()}
    call=ins.get(BEGIN);result=ins.get(122);branch=ins.get(124)
    if (not call or call.get_name()!="invoke-static/range" or call.get_length()!=6 or
        "Lcom/dsh/android/log/DiagnosticBundle;->build$default(" not in call.get_output()):
        raise ValueError("NATIVE_DIAGNOSTIC_EXPORT_CALL_NOT_VERIFIED")
    if result is None or result.get_name()!="move-result-object" or result.get_length()!=2 or "v3" not in result.get_output():
        raise ValueError("NATIVE_EXPORT_MOVE_RESULT_NOT_VERIFIED")
    if branch is None or branch.get_name()!="if-eqz" or not branch.get_output().startswith("v3,"):
        raise ValueError("NATIVE_EXPORT_FAILURE_BRANCH_NOT_VERIFIED")
    off=CODE_OFF+16+BEGIN
    output=bytearray(source)
    # 0x0312 = const/4 v3, #+0. Remaining code units are ordinary NOPs.
    output[off:off+8]=struct.pack("<4H",0x0312,0,0,0)
    output[12:32]=hashlib.sha1(output[32:]).digest()
    struct.pack_into("<I",output,8,zlib.adler32(output[12:]) & 0xffffffff)
    output=bytes(output)
    allowed=set(range(8,32))|set(range(off,off+8))
    if len(source)!=len(output) or any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(source,output))):
        raise AssertionError("NATIVE_EXPORT_PATCH_OUT_OF_BOUNDS")
    after=DEX(output)
    modified=[m for cls in after.get_classes() if cls.get_name()==OWNER
              for m in cls.get_methods() if m.get_name()==METHOD and m.get_descriptor()==SIGNATURE][0]
    ai={pc:x for pc,x in modified.get_instructions_idx()}
    if ai[BEGIN].get_name()!="const/4" or struct.unpack_from("<H",output,off)[0]!=0x0312:
        raise AssertionError("EXPORT_NULL_RETURN_NOT_PRESERVED")
    if any(ai[pc].get_name()!="nop" for pc in (118,120,122)):
        raise AssertionError("EXPORT_CALL_BYTES_NOT_NOP")
    if ai[124].get_name()!="if-eqz" or ai[124].get_output()!=branch.get_output():
        raise AssertionError("EXPORT_FAILURE_BRANCH_CHANGED")
    if any("Lcom/dsh/android/log/DiagnosticBundle;->build$default(" in x.get_output()
           for _,x in modified.get_instructions_idx()):
        raise AssertionError("NATIVE_DIAGNOSTIC_BUNDLE_BUILD_REMAINS")
    original_methods={(x.get_class_name(),x.get_name(),x.get_descriptor()):x
                      for c in dex.get_classes() for x in c.get_methods()}
    after_methods={(x.get_class_name(),x.get_name(),x.get_descriptor()):x
                   for c in after.get_classes() for x in c.get_methods()}
    if original_methods.keys()!=after_methods.keys():
        raise AssertionError("METHOD_TABLE_CHANGED")
    untouched=0
    for ident,orig in original_methods.items():
        new=after_methods[ident]
        if orig.get_code_off()!=new.get_code_off() or orig.get_access_flags()!=new.get_access_flags():
            raise AssertionError("CODE_OFF_OR_ACCESS_CHANGED")
        if not orig.get_code(): continue
        pos=orig.get_code_off()+16;size=orig.get_code().get_insns_size()*2
        if source[orig.get_code_off():pos]!=output[orig.get_code_off():pos]:
            raise AssertionError("CODE_HEADER_CHANGED")
        if ident!=(OWNER,METHOD,SIGNATURE):
            if source[pos:pos+size]!=output[pos:pos+size]:
                raise AssertionError("UNAUTHORIZED_OTHER_METHOD_CHANGE")
            untouched+=1
        else:
            if (source[pos:off]!=output[pos:off] or
                source[off+8:pos+size]!=output[off+8:pos+size]):
                raise AssertionError("UNAUTHORIZED_EXPORT_METHOD_CHANGE")
            if orig.get_code().get_insns_size()!=new.get_code().get_insns_size() or                orig.get_code().get_tries_size()!=new.get_code().get_tries_size():
                raise AssertionError("CODE_HEADER_SHAPE_CHANGED")
    return output,{
        "OLD_P8_DEX_SHA256":P8_INPUT_SHA,
        "NEW_P9_DEX_SHA256":sha(output),
        "NATIVE_LOG_EXPORT_BUNDLE_BUILDER_DISABLED":"PASS_STATIC",
        "RESULT_V3":"NULL",
        "EXISTING_IF_EQZ_FAILURE_PATH":"PRESERVED_STATIC",
        "CHANGED_DEX_BYTES":[off,off+8],
        "UNCHANGED_CODE_BODIES":untouched,
        "EXISTING_FILES_DELETED":"NO",
        "ORDINARY_ATTACHMENT_SEND_CHANGED":"NO",
        "NATIVE_LOG_READ_SUMMARY_CHANGED":"NO",
        "FUTURE_USER_APPROVED_DIAGNOSTIC_TRANSPORT":"NOT_CONNECTED",
        "NODE_SAME_UID_ACCESS_TO_PREEXISTING_FILES":"NOT_BLOCKED",
        "ART":"NOT_TESTED",
        "PRODUCTION_SIGNED_APK":"NO"}
