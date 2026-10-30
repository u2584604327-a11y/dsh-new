"""P10 exact remaining native raw diagnostic bundle construction gates.

Two additional original methods still construct complete diagnostic ZIPs:
  LogViewerActivity.exportBundle$lambda$41, code_off 3300360 at pc64
  LogUploader.collectCrashScenes, code_off 3505812 at pc442
P1 ART-safe deny already prevents the legacy upload$lambda$49 body; P9
denies LogCommandBridge.doExport. This P10 removes the two remaining
non-DiagnosticBundle build$default callsites, leaving local log viewing intact.

Source-only, in-RAM bounded patch; no APK exported or signed. Must pass ART.
"""
import hashlib,struct,zlib
from androguard.core.dex import DEX
from patch_deny import sha

P9_PREIMAGE="db1d61fdae52f55b569cc92bc82afbc82c31f305295ef4a2fd3a431177038d29"
BUILDER="Lcom/dsh/android/log/DiagnosticBundle;->build$default("
SPECS=[
  ("Lcom/dsh/android/LogViewerActivity;","exportBundle$lambda$41",
    "(Lcom/dsh/android/LogViewerActivity;)V",3300360,79,64,70,72,"invoke-static"),
  ("Lcom/dsh/android/log/LogUploader;","collectCrashScenes",
    "(Ljava/io/File;)Ljava/io/File;",3505812,476,442,448,450,"if-nez"),
]

def apply(source):
    if sha(source)!=P9_PREIMAGE:raise ValueError("EXACT_P9_INPUT_DEX_MISMATCH")
    dex=DEX(source);methods={(m.get_class_name(),m.get_name(),m.get_descriptor()):m
                         for cls in dex.get_classes() for m in cls.get_methods()}
    patched=bytearray(source)
    ranges=[];reports=[]
    for cls,name,desc,co,insns,pc,movepc,followpc,shape in SPECS:
        method=methods.get((cls,name,desc))
        if method is None or method.get_code_off()!=co or method.get_code().get_insns_size()!=insns:
            raise ValueError("EXPECTED_NATIVE_BUILDER_CALLER_SHAPE_MISMATCH")
        instructions={offset:instruction for offset,instruction in method.get_instructions_idx()}
        call=instructions.get(pc);move=instructions.get(movepc);follow=instructions.get(followpc)
        if (call is None or call.get_name()!="invoke-static/range" or
            call.get_length()!=6 or BUILDER not in call.get_output()):
            raise ValueError("NATIVE_BUILDER_PREIMAGE_INSTRUCTION_MISMATCH")
        if not move or move.get_name()!="move-result-object" or move.get_length()!=2 or "v0" not in move.get_output():
            raise ValueError("BUILDER_RESULT_REGISTER_MISMATCH")
        if followpc!=movepc+2 or not follow:
            raise ValueError("BUILDER_FOLLOWUP_MISSING")
        if cls.startswith("Lcom/dsh/android/log/"):
            if follow.get_name()!="if-nez" or not follow.get_output().startswith("v0,"):
                raise ValueError("CRASH_SCENE_DENY_BRANCH_MISSING")
        else:
            if follow.get_name()!="invoke-static" or "Lkotlin/Result;->constructor-impl(" not in follow.get_output():
                raise ValueError("MANUAL_EXPORT_KOTLIN_RESULT_BRANCH_MISSING")
        absolute=co+16+pc
        # const/4 v0, #0 (DEX format 11n, encoded 0x0012),
        # followed by 3 plain NOPs. The v0 move-result is now another NOP.
        patched[absolute:absolute+8]=struct.pack("<4H",0x0012,0,0,0)
        ranges.append((absolute,absolute+8))
        reports.append({"owner":cls,"method":name,"code_off":co,
                        "callsite_pc":pc,"patched_byte_range":[absolute,absolute+8],
                        "existing_followup_op":follow.get_name(),
                        "try_count":method.get_code().get_tries_size()})
    patched[12:32]=hashlib.sha1(patched[32:]).digest()
    struct.pack_into("<I",patched,8,zlib.adler32(patched[12:])&0xffffffff)
    patched=bytes(patched)
    permitted=set(range(8,32))
    for lo,hi in ranges:permitted.update(range(lo,hi))
    if len(source)!=len(patched) or any(a!=b and i not in permitted
        for i,(a,b) in enumerate(zip(source,patched))):
        raise AssertionError("UNAUTHORIZED_P10_DEX_BYTE_CHANGE")
    after=DEX(patched)
    after_methods={(m.get_class_name(),m.get_name(),m.get_descriptor()):m
                  for cls in after.get_classes() for m in cls.get_methods()}
    if after_methods.keys()!=methods.keys():raise AssertionError("DEX_METHOD_TABLE_CHANGED")
    remaining=[]
    for cls in after.get_classes():
        if cls.get_name().startswith("Lcom/dsh/android/") and            cls.get_name()!="Lcom/dsh/android/log/DiagnosticBundle;":
            for m in cls.get_methods():
                if m.get_code():
                    for pc,instr in m.get_instructions_idx():
                        if instr.get_name().startswith("invoke-") and BUILDER in instr.get_output():
                            remaining.append({"class":cls.get_name(),"method":m.get_name(),"pc":pc})
    if remaining:raise AssertionError("OTHER_EXTERNAL_DIRECT_DIAGNOSTIC_BUILDER_REMAINS:"+str(remaining))
    by_method={(r["owner"],r["method"]):r for r in reports}
    untouched=0
    for ident,old in methods.items():
        new=after_methods[ident]
        if old.get_code_off()!=new.get_code_off() or old.get_access_flags()!=new.get_access_flags():
            raise AssertionError("METHOD_LOCATION_OR_ACCESS_CHANGED")
        if not old.get_code():continue
        start=old.get_code_off()+16;end=start+old.get_code().get_insns_size()*2
        if source[old.get_code_off():start]!=patched[old.get_code_off():start]:
            raise AssertionError("CODE_HEADER_CHANGED")
        if (ident[0],ident[1]) not in by_method:
            if source[start:end]!=patched[start:end]:
                raise AssertionError("UNAUTHORIZED_METHOD_BODY_CHANGED")
            untouched+=1
        else:
            for lo,hi in ranges:
                if start<=lo<end:
                    if source[start:lo]!=patched[start:lo] or source[hi:end]!=patched[hi:end]:
                        raise AssertionError("OTHER_CODE_IN_TARGET_METHOD_CHANGED")
                    at=(lo-start)
                    opcodes={pc:i for pc,i in new.get_instructions_idx()}
                    if opcodes[at].get_name()!="const/4" or                         any(opcodes[at+x].get_name()!="nop" for x in (2,4,6)) or                         struct.unpack_from("<H",patched,lo)[0]!=0x0012:
                        raise AssertionError("DENY_REGISTER_OR_NOP_SEQUENCE_NOT_VERIFIED")
                    break
    return patched,{
      "P9_INPUT_SHA256":P9_PREIMAGE,
      "P10_MAIN_DEX_SHA256":sha(patched),
      "PATCHED_ORIGINAL_METHODS":reports,
      "OTHER_METHOD_CODE_BODIES_IDENTICAL":untouched,
      "ALL_DIRECT_EXTERNAL_DIAGNOSTIC_BUILD_DEFAULT_CALLS":"ZERO_STATIC",
      "ORIGINAL_CRASH_LOG_STORAGE":"NOT_DELETED",
      "ORIGINAL_LOG_VIEW_READ_SUMMARY":"NOT_MODIFIED",
      "ORDINARY_FILE_IMAGE_TRANSPORT":"NOT_MODIFIED_BY_P10",
      "EXISTING_ZIPS_SAME_UID_NODE_ACCESSIBLE":"YES",
      "NODE_JNI_DYNAMIC_BUILD_PATH":"NOT_VERIFIED",
      "ART":"NOT_TESTED",
      "VERSION_CODE":"138_UNCHANGED",
      "PRODUCTION_APK":"NOT_BUILT"
    }
