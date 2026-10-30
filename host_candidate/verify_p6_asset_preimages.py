#!/usr/bin/env python3
"""P6 asset overlay preimage gate on the *exact signed v138* APK.
Does NOT modify an APK, sign, install, upload, or activate any JavaScript.
"""
import argparse,hashlib,io,json,pathlib,zipfile
EXPECTED_APK="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
EXPECTED_P6="3af586c2c83d1aea67d119357672559eb09371c77ef4e06900bb697c06d11fd5"
EXPECTED_PATHS={
    "assets/browser-tool.zip",
    "assets/browser-pane.zip",
    "assets/dsh-fetch-guard.mjs",
}
def sha_bytes(data):return hashlib.sha256(data).hexdigest()
def sha_file(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
 return h.hexdigest()
def verify(apk,p6):
 if sha_file(apk)!=EXPECTED_APK:raise ValueError("UNKNOWN_APK_PREIMAGE")
 if sha_file(p6)!=EXPECTED_P6:raise ValueError("UNKNOWN_P6_PREIMAGE")
 with zipfile.ZipFile(p6) as outer,zipfile.ZipFile(apk) as app:
  if outer.testzip() is not None or app.testzip() is not None:raise ValueError("ZIP_CRC_FAIL")
  overlay=outer.read("output/DSH_V139_P6_ASSET_OVERLAY_NOT_APK.zip")
  with zipfile.ZipFile(io.BytesIO(overlay)) as new:
   if new.testzip() is not None:raise ValueError("OVERLAY_CRC_FAIL")
   manifest=json.loads(new.read("ASSET_DELTA_MANIFEST.json"))
   if manifest.get("type")!="DSH_P6_ASSET_OVERLAY_SOURCE_ONLY":raise ValueError("BAD_OVERLAY_TYPE")
   if set(manifest["changes"])!=EXPECTED_PATHS:raise ValueError("UNEXPECTED_OVERLAY_PATHS")
   if set(new.namelist())!=EXPECTED_PATHS|{"ASSET_DELTA_MANIFEST.json"}:
    raise ValueError("UNEXPECTED_OVERLAY_CONTENT")
   items=[]
   for path in sorted(EXPECTED_PATHS):
    original=app.read(path)
    replacement=new.read(path)
    spec=manifest["changes"][path]
    if sha_bytes(original)!=spec["original_sha256"] or len(original)!=spec["original_size"]:
     raise ValueError("APK_ASSET_PREIMAGE_MISMATCH_"+path)
    if sha_bytes(replacement)!=spec["new_sha256"] or len(replacement)!=spec["new_size"]:
     raise ValueError("OVERLAY_ASSET_HASH_MISMATCH_"+path)
    if path.endswith(".zip"):
     with zipfile.ZipFile(io.BytesIO(replacement)) as nested:
      if nested.testzip() is not None:raise ValueError("NESTED_ASSET_CRC_FAIL_"+path)
    items.append({"path":path,"baseline_sha256":sha_bytes(original),"candidate_sha256":sha_bytes(replacement)})
 return {"V138_ASSET_OVERLAY_PREIMAGES":"PASS",
   "overlay_files":items,
   "ASSET_OVERLAY_STAGED":"YES",
   "APK_MODIFIED":"NO",
   "APK_BUILT":"NO",
   "APK_SIGNED":"NO",
   "JS_ASSETS_ACTIVE_ON_PHONE":"NOT_VERIFIED",
   "NATIVE_NODE_DIAGNOSTIC_EGRESS":"NOT_VERIFIED",
   "ART":"NOT_VERIFIED"}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("v138");p.add_argument("p6");p.add_argument("--report",default="p6-asset-preimages.json")
 a=p.parse_args()
 res=verify(a.v138,a.p6)
 pathlib.Path(a.report).write_text(json.dumps(res,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(res,indent=2))
