#!/usr/bin/env python3
"""P69 inspect EXACT v138+P6 browser tool execution/reply assets without executing JS.

Outputs only normalized JS structure, never string literals, credentials,
cookies, URLs, original code bytes, user message text, or provider tokens.
Analysis is read-only: no patch to installed DSH, no simulated passing tool.
"""
import argparse,collections,hashlib,io,json,pathlib,re,sys,zipfile
ORIGINAL="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
P6="3af586c2c83d1aea67d119357672559eb09371c77ef4e06900bb697c06d11fd5"
LOOK=("no.reply","no_reply","noreply","tool_calls","toolcalls",
      "browser","reply","invoke","dispatch","callback","pending",
      "resolve","reject","timeout","eval","read","scroll","click",
      "cookie","storage","persist","webview","bridge","send",
      "requestid","callid","permission","toolresult","onmessage","postmessage")
GROUPS={
 "TOOL_CALL_PARSE":("tool_calls","toolcalls","dsml","function_call","toolcall"),
 "REQUEST_REPLY":("reply","callback","onmessage","postmessage","requestid","callid","toolresult"),
 "DISPATCH":("dispatch","invoke","execute","browser","plugin","permission"),
 "TIMEOUT":("timeout","pending","resolve","reject","abort","cancel"),
 "BROWSER_ACTION":("scroll","read","click","eval","input","type"),
 "PERSISTENCE":("cookie","storage","persist","webview","profile","clearcache","cleardata"),
}
def digest(x):return hashlib.sha256(x).hexdigest()
def zip_entries(b):
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  if z.testzip() is not None:raise ValueError("BAD_NESTED_ZIP_CRC")
  return {i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
def mask(text):
 """Replace literal string/template/comment contents preserving code identifiers."""
 result=[];i=0;n=len(text);state="CODE"
 while i<n:
  c=text[i];d=text[i+1] if i+1<n else ""
  if state=="CODE":
   if c in ("'",'"',"\x60"):
    state=c;result.append(" STR ");i+=1;continue
   if c=="/" and d=="/":
    state="LINE";result.append(" ");i+=2;continue
   if c=="/" and d=="*":
    state="BLOCK";result.append(" ");i+=2;continue
   result.append(c);i+=1;continue
  if state in ("'",'"',"\x60"):
   if c=="\\":
    i+=2;continue
   if c==state:state="CODE"
   i+=1;continue
  if state=="LINE":
   if c in "\r\n":state="CODE";result.append("\n")
   i+=1;continue
  if state=="BLOCK":
   if c=="*" and d=="/":state="CODE";i+=2;continue
   i+=1;continue
 return "".join(result)
def skeleton(raw,term,max_hits=2):
 """Only JS identifiers/punctuation from lexical code after literal masking."""
 redacted=mask(raw)
 sites=[m.start() for m in re.finditer(re.escape(term),redacted,re.I)]
 out=[]
 for x in sites[:max_hits]:
  context=redacted[max(0,x-115):x+125]
  tokens=re.findall(r"[A-Za-z_$][A-Za-z0-9_$]{0,48}|[{}()\[\].,;:=]",context)
  out.append(" ".join(tokens[:45])[:220])
 return out
def inspect(original,p6):
 if digest(original)!=ORIGINAL or digest(p6)!=P6:
  raise ValueError("UNPINNED_APK_OR_P6_PREIMAGE")
 a=zip_entries(original)
 release=zip_entries(p6)
 overlay=zip_entries(release["output/DSH_V139_P6_ASSET_OVERLAY_NOT_APK.zip"])
 records=[]
 for filename in ("assets/browser-tool.zip","assets/browser-pane.zip"):
  if filename not in a or filename not in overlay:
   raise ValueError("EXPECTED_BROWSER_ASSET_MISSING")
  for version,data in (("V138",a[filename]),("P6",overlay[filename])):
   nested=zip_entries(data)
   for name,payload in sorted(nested.items()):
    if not name.lower().endswith((".js",".mjs",".html",".json")):
     continue
    text=payload.decode("utf-8","replace")
    if len(text)>5_000_000:
     raise ValueError("UNBOUNDED_BROWSER_SCRIPT")
    reduced=mask(text)
    counts={k:sum(reduced.lower().count(token) for token in group)
            for k,group in GROUPS.items()}
    examples={}
    for key in ("tool_calls","no_reply","noreply","reply","dispatch",
                "postMessage","browser","cookie","storage","timeout"):
     if key.lower() in reduced.lower():
      examples[key]=skeleton(text,key,2)
    records.append({"asset":filename.split("/")[-1],
                    "version":version,"file":name,
                    "bytes":len(payload),
                    "mask_counts":counts,
                    "samples":examples})
 return records
def report(records):
 print("P69_EXACT_SIGNED_V138_AND_P6_ASSET_INSPECTION=PASS")
 print("P69_BROWSER_FILES_COUNT="+str(len(records)))
 for row in records:
  if sum(row["mask_counts"].values())==0:continue
  print("P69_BROWSER_STRUCTURE="+json.dumps(row,sort_keys=True,ensure_ascii=True))
 print("P69_ORIGINAL_SOURCE_OR_STRING_LITERALS_PRINTED=NO")
 print("P69_REAL_TOOL_DISPATCH_EXECUTION=NOT_TESTED")
 print("P69_NO_REPLY_REPRODUCED=NOT_YET")
 print("P69_EXISTING_DSH_BROWSER_PROFILE_PERSISTENCE=NOT_PROVEN")
def selftest():
 original="function handle(){ const secret='ghp_TOTALLY_PRIVATE'; /* NO_REPLY_TOKEN */ browser.dispatch(); return data.reply; }"
 red=mask(original)
 assert "TOTALLY_PRIVATE" not in red and "NO_REPLY_TOKEN" not in red
 assert "browser.dispatch" in red and "data.reply" in red
 assert "ghp_" not in str(skeleton(original,"browser"))
 assert skeleton(original,"browser")
 assert not skeleton(original,"NO_REPLY_TOKEN")
 print("P69_SYNTHETIC_LITERAL_REDACTION=PASS")
if __name__=="__main__":
 ap=argparse.ArgumentParser()
 ap.add_argument("--original");ap.add_argument("--p6");ap.add_argument("--selftest",action="store_true")
 args=ap.parse_args()
 if args.selftest:selftest()
 else:
  if not args.original or not args.p6:ap.error("original and p6 required")
  report(inspect(pathlib.Path(args.original).read_bytes(),
                 pathlib.Path(args.p6).read_bytes()))
