#!/usr/bin/env python3
"""Verify that exact P2 bounded DEX removes the known native diagnostic HTTP sink.

This intentionally does NOT claim full Android or Node network closure. Uses
the already SHA-pinned 7-method bounded patch; never writes patched APK/DEX.
"""
import argparse, hashlib, json, pathlib, re, zipfile
from androguard.core.dex import DEX
from patch_deny import apply as deny, sha, EXPECTED_APK
from patch_browser import apply_browser
from patch_privacy import apply_privacy

EXPECTED_COMBINED_SHA = "9a7cd89f4a5c86394770febf703a9345a44d8c12c39abec9d494635587d8f221"
SCOPE = {
    "Lcom/dsh/android/log/LogUploader;",
    "Lcom/dsh/android/LogViewerActivity;",
    "Lcom/dsh/android/LogCommandBridge;",
}
SINK_PATTERN = re.compile(
    r"(?:Ljava/net/URL;->(?:openConnection|<init>)\(|"
    r"Ljava/net/HttpURLConnection;->(?:getOutputStream|setDoOutput|setRequestMethod|connect)\(|"
    r"Ljavax/net/ssl/HttpsURLConnection;->(?:getOutputStream|connect)\(|"
    r"Lokhttp3/(?:OkHttpClient|Call);->(?:newCall|execute|enqueue)\()"
)

def sha_file(path):
    h = hashlib.sha256()
    with open(path,"rb") as handle:
        for block in iter(lambda: handle.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def scan(dex_bytes):
    d = DEX(dex_bytes)
    sites = []
    for cls in d.get_classes():
        class_name = cls.get_name()
        if class_name not in SCOPE:
            continue
        for m in cls.get_methods():
            if not m.get_code():
                continue
            for offset, ins in m.get_instructions_idx():
                if not ins.get_name().startswith("invoke-"):
                    continue
                match = SINK_PATTERN.search(ins.get_output())
                if match:
                    sites.append({
                        "class":class_name, "method":m.get_name(),
                        "pc":offset,"sink":match.group(0).split("(")[0]
                    })
    return sites

def verify(apk):
    if sha_file(apk) != EXPECTED_APK:
        raise ValueError("BASELINE_APK_SHA256_MISMATCH")
    with zipfile.ZipFile(apk) as archive:
        if archive.testzip() is not None:raise ValueError("APK_CRC_FAILED")
        original=archive.read("classes.dex")
    original_sites=scan(original)
    if not any(x["method"]=="doUpload" and "getOutputStream" in x["sink"] for x in original_sites):
        raise AssertionError("ORIGINAL_UPLOAD_NETWORK_SINK_NOT_LOCATED")
    p1,_=deny(original)
    p2,_=apply_browser(p1)
    bounded,_=apply_privacy(p2)
    if sha(bounded)!=EXPECTED_COMBINED_SHA:
        raise AssertionError("BOUNDED_DEX_FINAL_SHA_MISMATCH")
    final_sites=scan(bounded)
    if final_sites:
        raise AssertionError("NATIVE_DIAGNOSTIC_HTTP_SINK_STILL_REACHABLE_IN_SCOPED_METHODS")
    return {
        "V138_BASELINE":"SHA256_VERIFIED",
        "ORIGINAL_DIAGNOSTIC_HTTP_SITES":len(original_sites),
        "ORIGINAL_METHOD_SINK_KINDS":sorted({x["sink"] for x in original_sites}),
        "P2_BOUNDED_DEX_SHA256":sha(bounded),
        "BOUNDED_DEX_SCOPED_HTTP_SITES":len(final_sites),
        "KNOWN_ORIGINAL_NATIVE_UPLOADER_HTTP_INSTRUCTIONS_REMOVED":"PASS",
        "REPLAYED_NATIVE_METHODS":7,
        "NATIVE_ART_VERIFIED":"NO",
        "ALL_NATIVE_AND_NODE_EGRESS_BLOCKED":"NOT_VERIFIED",
        "USER_APPROVED_SENDER_CONNECTED":"NO",
        "APK_BUILT":"NO",
        "PHONE_CHANGED":"NO",
    }

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("v138_apk")
    cli.add_argument("--report",default="native-diagnostic-sink-delta.json")
    args=cli.parse_args()
    result=verify(args.v138_apk)
    pathlib.Path(args.report).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
