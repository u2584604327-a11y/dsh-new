#!/usr/bin/env python3
"""P69 focused mailbox+native bridge skeleton. NO raw string/user data output."""
import argparse,io,json,pathlib,re,sys,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from audit_browser_reply import zip_entries,mask,digest,ORIGINAL,P6
PATTERNS=["CMD_FILE","RESULT_FILE","WAIT_TIMEOUT_MS","POLL_INTERVAL_MS",
          "readJson","writeJson","resPath","cmdPath","reply.id",
          "function invoke","function browser","function execute",
          "function dispatch","function call","async function",
          "no reply","throw new Error","readFileSync","renameSync",
          "unlinkSync","mkdirSync","requestId","setTimeout"]
def sanitize_piece(masked,pos):
 start=max(0,pos-190);end=min(len(masked),pos+590)
 piece=masked[start:end]
 # Never emit original literal, source path or base64, only masked syntax;
 # whitespace normalized so no arbitrary multiline output.
 return re.sub(r"\s+"," ",piece).strip()[:780]
def inspect(apk,p6):
 a=apk.read_bytes();b=p6.read_bytes()
 if digest(a)!=ORIGINAL or digest(b)!=P6:raise ValueError("HASH_MISMATCH")
 orig=zip_entries(a)
 p6files=zip_entries(b)
 archive=zip_entries(p6files["output/DSH_V139_P6_ASSET_OVERLAY_NOT_APK.zip"])
 for kind,assets in (("ORIGINAL",orig),("P6",archive)):
  file=zip_entries(assets["assets/browser-tool.zip"])["lib/index.js"]
  sanitized=mask(file.decode("utf-8","replace"))
  print("P69_TOOL_BACKEND_VERSION="+kind)
  for pattern in PATTERNS:
   found=[m.start() for m in re.finditer(re.escape(pattern),sanitized,re.I)]
   if not found:continue
   print("P69_TOOL_BACKEND_SITE="+json.dumps({
    "marker":pattern,"count":len(found),
    "masked_neighborhoods":[sanitize_piece(sanitized,x) for x in found[:2]]
   },sort_keys=True,ensure_ascii=True))
 print("P69_MASKED_LITERAL_VALUES_LEAKED=NO")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--original",required=True);p.add_argument("--p6",required=True)
 args=p.parse_args();inspect(pathlib.Path(args.original),pathlib.Path(args.p6))
