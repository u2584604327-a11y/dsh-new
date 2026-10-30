#!/usr/bin/env python3
"""SHA-locked first-party original DSH agent/tool entry contract discovery.
Print only filenames, named exports, package imports, literals and call tokens;
never print source, prompt, credentials or user-specific configuration.
"""
import argparse, collections, gzip, io, json, pathlib, re, tarfile, zipfile
from p96_original_engine_owner import SOURCE_BYTES, SOURCE_SHA, file_hash, require, sha
PKG={
 "dsh-agent-loop","dsh-agent","dsh-llm","dsh-llm-pi-ai",
 "dsh-api-session-controller","dsh-session-projection","dsh-client-ui-tool",
 "dsh-tool","dsh-tools","dsh-tool-browser"
}
TOKENS={
 "CALL_DISPATCH":(b"executeTool",b"execute(",b"callTool(",b"toolCall",b"toolCalls"),
 "TOOL_RESULTS":(b"toolResult",b"tool_result",b"toolCallId",b"toolName",b"toolResultId"),
 "MODEL_TURN":(b"session.update",b"assistantMessage",b"turnId",b"generation"),
 "TOOLS_DECLARED":(b"toolsAdded",b"getDeclaredTools",b"resolveTranscriptTools"),
 "EVENTS":(b"emit(",b".on(",b"subscribe(",b"onMessage"),
 "AGENT":(b"AgentLoop",b"runAgent",b"agentLoop",b"nextStep",b"step(")
}
MAX_MEMBER=3_000_000
def pkg(path):
 parts=path.split("/")
 return parts[2] if len(parts)>3 and parts[:2]==["node_modules","@deepseek-ai"] else None
def inspect(apk):
 require(apk.stat().st_size==SOURCE_BYTES,"APK_SIZE_DRIFT")
 require(file_hash(apk)==SOURCE_SHA,"APK_SHA_DRIFT")
 with zipfile.ZipFile(apk) as z:
  require(z.testzip() is None,"APK_CRC")
  raw=z.read("assets/engine.bin")
 entries=[]; count=0
 with tarfile.open(fileobj=gzip.GzipFile(fileobj=io.BytesIO(raw)),mode="r|") as t:
  for item in t:
   count+=1
   require(count<=50000,"TAR_COUNT")
   name=item.name
   if not item.isfile() or pkg(name) not in PKG:continue
   if not name.endswith((".js",".mjs",".cjs",".json")):continue
   require(0<=item.size<=MAX_MEMBER,"SOURCE_TOO_LARGE")
   f=t.extractfile(item)
   require(f is not None,"SOURCE_BYTES_MISSING")
   rawfile=f.read(MAX_MEMBER+1)
   require(len(rawfile)==item.size,"SHORT_SOURCE")
   if name.endswith("/package.json"):
    try:
     d=json.loads(rawfile)
     entries.append({"path":name,"packageMain":d.get("main"),
                     "nodeEngineRequirement":str(d.get("engines",{}).get("node","UNDECLARED"))[:80]
                         if isinstance(d.get("engines"),dict) else "UNDECLARED",
                     "packageExports":sorted(d.get("exports",{}))[:25]
                         if isinstance(d.get("exports"),dict) else []})
    except (UnicodeError,ValueError):pass
    continue
   if not name.endswith((".js",".mjs",".cjs")):continue
   # Inspect named export shapes and imports without emitting private code.
   imp=set()
   for pat in [
    rb"""(?:from|import)\s*["']([^"']{1,150})["']""",
    rb"""import\(["']([^"']{1,150})["']\)""",
   ]:
    imp.update(x.decode("utf-8","replace") for x in re.findall(pat,rawfile))
   exports=set()
   for pattern in [
    rb"\bexport\s+(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_][\w$]{0,90})",
    rb"\bexport\s*\{\s*([^}]{1,800})\s*\}",
   ]:
    for m in re.finditer(pattern,rawfile):
     label=m.group(1).decode("utf-8","replace")
     if "," in label or " as " in label:
      for part in label.split(","):
       exported=part.strip().split(" as ")[-1].strip()
       if re.fullmatch(r"[A-Za-z_][\w$]{0,90}",exported):
        exports.add(exported)
     elif re.fullmatch(r"[A-Za-z_][\w$]{0,90}",label):
      exports.add(label)
   hits={key:sum(token in rawfile for token in vals)
         for key,vals in TOKENS.items()}
   hits={k:v for k,v in hits.items() if v}
   if name.endswith("/lib/index.js") or hits.get("CALL_DISPATCH") or hits.get("TOOL_RESULTS"):
    entries.append({"path":name,"sha12":sha(rawfile)[:12],
                    "bytes":item.size,"exports":sorted(exports)[:55],
                    "imports":sorted(imp)[:35],"markers":hits})
 print("P96_AGENT_ORIGINAL_SOURCE_LOCK=PASS")
 print("P96_AGENT_EVENT_CONTRACT="+json.dumps(entries,ensure_ascii=True,sort_keys=True))
 for e in entries:
  if any("/"+name+"/" in e["path"] for name in
         ("dsh-agent-loop","dsh-agent","dsh-llm-pi-ai",
          "dsh-api-session-controller","dsh-tool","dsh-tools")):
   if "exports" in e or "packageMain" in e:
    print("P96_AGENT_HOOK="+json.dumps({
     "path":e["path"],"exports":e.get("exports",[])[:18],
     "imports":e.get("imports",[])[:18],
     "packageMain":e.get("packageMain"),
     "packageExports":e.get("packageExports",[]),
     "markers":e.get("markers",{})},sort_keys=True))
 for e in entries:
  if e["path"]=="node_modules/@deepseek-ai/dsh-agent-loop/package.json":
   print("P96_ORIGINAL_AGENTLOOP_PACKAGE_NODE_ENGINE="+e.get("nodeEngineRequirement","UNDECLARED"))
 print("P96_AGENT_ORIGINAL_TOOL_DISPATCH_WIRED=NO")
 print("P96_AGENT_SOURCE_MUTATION=NO")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--original",required=True)
 args=p.parse_args();inspect(pathlib.Path(args.original))
