#!/usr/bin/env python3
"""Source-locked original provider contract hints; no patch or engine execution.
Reads only four named original source files and prints bounded nearby syntax.
Only original binary's embedded source; no user settings, cookies or tokens.
"""
import argparse, gzip, hashlib, io, pathlib, re, tarfile, zipfile
from p96_original_engine_owner import SOURCE_BYTES, SOURCE_SHA, file_hash, require

SOURCES = {
  "provider": "node_modules/@deepseek-ai/dsh-llm-pi-ai/lib/index.js",
  "settings": "node_modules/@deepseek-ai/dsh-llm/lib/index.js",
  "session": "node_modules/@deepseek-ai/dsh-api-session-controller/lib/client.js",
  "model_ui": "node_modules/@deepseek-ai/dsh-client-ui-settings-models/lib/client.js",
}
TOKENS = {
  "provider": [b"openai-completions",b"baseUrl",b"baseURL",b"streamSimple",
               b"apiKey",b"toolCall",b"tool_calls",
               b"routeAuth", b"defaultContextWindow", b"request.models",
               b"modelOverrides", b"request.provider", b"request.baseURL",
               b"modelProfile", b"modelOverride", b"routeProfile", b"routeConfig",
               b"providerProfile", b"namesCredential", b"model.api", b"source.models"],
  "settings": [b"baseURL",b"openai-completions"],
  "session": [b"session.update",b"onMessage"],
  "model_ui": [b"baseUrl",b"baseURL",b"apiKey",b"provider"],
}
def verify_source(path):
    require(path.stat().st_size==SOURCE_BYTES,"ORIGINAL_SIZE")
    require(file_hash(path)==SOURCE_SHA,"ORIGINAL_SHA")
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None,"ORIGINAL_ZIP")
        payload=z.read("assets/engine.bin")
    wanted=set(SOURCES.values())
    found={}
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as g:
      with tarfile.open(fileobj=g,mode="r|") as archive:
        for item in archive:
            if item.name not in wanted:continue
            require(item.isfile() and 0<=item.size<=256000,"TARGET_BUDGET")
            data=archive.extractfile(item).read(256001)
            require(len(data)==item.size,"TARGET_SHORT_READ")
            found[item.name]=data
    require(set(found)==wanted,"ORIGINAL_EXACT_SOURCE_MISSING")
    return {key:found[path] for key,path in SOURCES.items()}
def scrub(data):
    # Never output model keys or original string contents. Keep keywords and
    # call syntax visible, replace source string/comment payloads entirely.
    s=data.decode("utf-8","replace").replace("\n"," ").replace("\r"," ")
    s=re.sub(r"(?s)/\*.*?\*/", "/*…*/",s)
    s=re.sub(r"//[^\n]*", "//…",s)
    s=re.sub(r"(?<!\\w)(['\`])(?:\\\\.|(?!\\1).)*?\\1", '"…"',s)
    return s
def audit(path):
    modules=verify_source(path)
    print("P96_EXACT_ORIGINAL_MODEL_PROVIDER_PREIMAGE=PASS")
    for key,blob in modules.items():
        print("P96_TARGET_"+key.upper()+"_SIZE="+str(len(blob))+
              "_SHA256="+hashlib.sha256(blob).hexdigest())
        for token in TOKENS[key]:
            positions=[m.start() for m in re.finditer(re.escape(token),blob)]
            if not positions:continue
            print("P96_CONTRACT_ANCHOR="+key+" | "+token.decode()+
                  " | count="+str(len(positions))+" | offsets="+str(positions[:8]))
            for i in positions[:min(3,len(positions))]:
                fragment=blob[max(0,i-160):min(len(blob),i+220)]
                # Context is solely private original package source; fixed max.
                # Explicitly encode single-line and no control characters.
                clean=fragment.decode("utf-8","replace")
                clean=re.sub(r"[\x00-\x1f\x7f]+"," ",clean)
                clean=re.sub(r"https?://[^\s'\"\`]+","<URL>",clean)
                clean=re.sub(r"(?:sk-|Bearer )[a-zA-Z0-9._-]{8,}","<CREDENTIAL>",clean)
                print("P96_ANCHOR_CONTEXT="+key+" | "+token.decode()+
                      " | "+str(i)+" | "+clean[:370])
    print("P96_ORIGINAL_PROVIDER_OR_SESSION_MODIFIED=NO")
    print("P96_ON_DEVICE_MODEL_TO_CHAT_REPLY=NOT_PROVEN")
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--original",required=True)
    arg=parser.parse_args()
    audit(pathlib.Path(arg.original))
