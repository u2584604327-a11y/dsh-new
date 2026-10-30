#!/usr/bin/env python3
"""P2 bounded DEX replayer: exact v138 -> P1 deny -> browser -> privacy.
Pure RAM candidate and metadata only: never writes modified DEX/APK or signs.
This does NOT establish ART, runtime privacy or any diagnostic-send safety.
"""
import argparse,hashlib,json,struct,zipfile,zlib
from pathlib import Path
from loguru import logger
logger.disable('androguard')
from androguard.core.dex import DEX
from patch_deny import apply as deny, sha, EXPECTED_APK, SPECS
from patch_browser import apply_browser, KEYS as BROWSER_KEYS
from patch_privacy import apply_privacy, KEY as PRIVACY_KEY

EXPECTED_RESULT="9a7cd89f4a5c86394770febf703a9345a44d8c12c39abec9d494635587d8f221"
EXPECTED_UNCHANGED=52004
EXPECTED_CHANGED_BYTES=2569

def verify(apk):
    raw=Path(apk).read_bytes()
    if sha(raw)!=EXPECTED_APK:raise ValueError("INVALID_OR_UNKNOWN_V138_APK_HASH")
    with zipfile.ZipFile(apk) as z:
        if z.testzip() is not None:raise ValueError("APK_ZIP_CRC_FAIL")
        original=z.read("classes.dex")
    p1,rep1=deny(original)
    p2,rep2=apply_browser(p1)
    output,rep3=apply_privacy(p2)
    if sha(output)!=EXPECTED_RESULT:raise AssertionError("EXPECTED_COMBINED_DEX_HASH_MISMATCH")
    if not len(original)==len(output):raise AssertionError("DEX_SIZE_CHANGED")
    a,b=DEX(original),DEX(output)
    def indexed(d):return {m.get_method_idx():m for c in d.get_classes() for m in c.get_methods()}
    old,new=indexed(a),indexed(b)
    if old.keys()!=new.keys():raise AssertionError("METHOD_INDEX_CHANGED")
    allowed=set(range(8,32))
    targets=set(SPECS)|BROWSER_KEYS|{PRIVACY_KEY}
    unchanged=0;changed=[]
    for index,m in old.items():
        n=new[index]
        if m.get_code_off()!=n.get_code_off() or m.get_access_flags()!=n.get_access_flags():
            raise AssertionError("METHOD_HEADER_OR_ACCESS_CHANGED")
        off=m.get_code_off()
        if off==0:continue
        co=m.get_code();newcode=n.get_code()
        end=off+16+co.get_insns_size()*2
        if original[off:off+16]!=output[off:off+16]:raise AssertionError("CODE_HEADER_CHANGED")
        if newcode.get_insns_size()!=co.get_insns_size():raise AssertionError("INSNS_SIZE_CHANGED")
        if [t.get_raw() for t in co.get_tries()]!=[t.get_raw() for t in newcode.get_tries()]:
            raise AssertionError("EXCEPTION_TRY_CHANGED")
        h1=co.get_handlers();h2=newcode.get_handlers()
        if (h1.get_raw() if h1 else None)!=(h2.get_raw() if h2 else None):
            raise AssertionError("EXCEPTION_HANDLERS_CHANGED")
        key=(m.get_class_name(),m.get_name())
        if key in targets:
            allowed.update(range(off+16,end))
            if sum(i.get_length() for i in n.get_instructions())!=co.get_insns_size()*2:
                raise AssertionError("BAD_DEX_INSTRUCTION_BOUNDARY")
            changed.append({"class":key[0],"method":key[1],"method_index":index})
        else:
            if original[off+16:end]!=output[off+16:end]:
                raise AssertionError("UNAUTHORIZED_CODE_BODY_CHANGE")
            unchanged+=1
    changed_bytes=sum(x!=y for x,y in zip(original,output))
    if changed_bytes!=EXPECTED_CHANGED_BYTES:raise AssertionError("CHANGED_BYTE_COUNT_MISMATCH")
    if len(changed)!=7 or unchanged!=EXPECTED_UNCHANGED:
        raise AssertionError("UNEXPECTED_METHOD_SCOPE")
    if any(x!=y and i not in allowed for i,(x,y) in enumerate(zip(original,output))):
        raise AssertionError("UNAUTHORIZED_DEX_OFFSET_CHANGE")
    if output[12:32]!=hashlib.sha1(output[32:]).digest():raise AssertionError("DEX_SHA1_INVALID")
    if struct.unpack_from('<I',output,8)[0] != zlib.adler32(output[12:]) & 0xffffffff:
        raise AssertionError("DEX_ADLER_INVALID")
    if output[0x301bb2:0x301bb8]!=b'\0'*6:raise AssertionError("TABLE_GUARD_CHANGED")
    return {
        "P2_P1_DENY_METHODS":len(rep1["methods"]),
        "P2_BROWSER_METHODS":len(rep2["methods"]),
        "P2_WEBVIEW_SETTINGS_METHODS":1,
        "P2_BASELINE_DEX_SHA256":sha(original),
        "P2_BOUNDED_DEX_SHA256":sha(output),
        "P2_BOUNDED_DEX_CHANGED_BYTES":changed_bytes,
        "P2_METHODS_IN_SCOPE":changed,
        "P2_UNCHANGED_METHOD_CODE_BODIES":unchanged,
        "P2_DEX_METHOD_SCOPE_AND_REFERENCES":"PASS",
        "P2_ANDROID_ART":"NOT_VERIFIED",
        "P2_USER_DATA_PRESERVATION":"NOT_VERIFIED",
        "P2_FULL_NATIVE_AND_NODE_EGRESS":"NOT_VERIFIED",
        "P2_DEVICE_SETTINGS_UI":"NOT_INTEGRATED",
        "P2_STORAGE_ISOLATION":"NOT_IMPLEMENTED",
        "P2_NEW_APK_BUILT":"NO",
        "P2_NEW_APK_SIGNED":"NO",
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("v138_apk")
    p.add_argument("--report",default="p2-bounded-dex-report.json")
    a=p.parse_args()
    result=verify(a.v138_apk)
    Path(a.report).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
