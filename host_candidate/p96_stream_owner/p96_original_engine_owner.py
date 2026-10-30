#!/usr/bin/env python3
"""P96 read-only source-owner discovery for the exact original DSH web engine.
Only examines SHA-locked archive, prints safe categories + anonymous hashes.
Never executes, extracts, modifies, publishes, signs or starts original code.
"""
import argparse, collections, gzip, hashlib, io, json, pathlib, re, tarfile, zipfile

SOURCE_SHA = "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
SOURCE_BYTES = 147341486
ENGINE_ENTRY = "assets/engine.bin"
EXPECTED_TAR_ENTRIES = 30411
MAX_ANALYZED_FILE = 10 * 1024 * 1024
MAX_ANALYZED_TOTAL = 350 * 1024 * 1024
MAX_RESULT_ROWS = 16
RULES = {
    "OPENAI_STREAM_PROTOCOL": (b"text/event-stream", b"chat.completions", b"[DONE]"),
    "SSE_DELTA_TOOL": (b"tool_calls", b"reasoning_content", b"finish_reason"),
    "STREAMING_READER": (b"getReader(", b"TextDecoder(", b"ReadableStream"),
    "WEB_CHAT_TRANSPORT": (b"WebSocket", b"EventSource", b"fetch("),
    "ORIGINAL_HTTP_CHAT": (b"/v1/chat/completions", b"chat/completions", b"/api/chat"),
    "MESSAGE_STATE": (b"assistant", b"messages", b"conversation"),
}
def require(ok, name):
    if not ok: raise ValueError("P96_BLOCKED_" + name)
def sha(b):return hashlib.sha256(b).hexdigest()
def file_hash(path):
    h=hashlib.sha256()
    with open(path,"rb") as inp:
        for block in iter(lambda:inp.read(1<<20),b""):h.update(block)
    return h.hexdigest()
def category(path):
    low=path.lower()
    # Node dependencies often live at the archive ROOT and contain /dist/.
    # Never mistake third-party SDK builds for our original DSH frontend.
    if low.startswith("node_modules/@deepseek-ai/dsh/") or \
       "/node_modules/@deepseek-ai/dsh/" in low:
        return "ORIGINAL_DSH_NODE_MODULE"
    if low.startswith("node_modules/") or "/node_modules/" in low:
        return "THIRD_PARTY_NODE_MODULE"
    if any(hint in low for hint in ("/frontend/","/web/","/public/","/ui/")):
        return "WEB_OR_FRONTEND_ASSET"
    return "ORIGINAL_OTHER"
def classify(blob):
    found={name:sum(needle in blob for needle in patterns)
           for name,patterns in RULES.items()}
    return {k:v for k,v in found.items() if v>0}
def score(found,owner):
    value=(found.get("OPENAI_STREAM_PROTOCOL",0)*5+
        found.get("SSE_DELTA_TOOL",0)*4+
        found.get("STREAMING_READER",0)*2+
        found.get("ORIGINAL_HTTP_CHAT",0)*3+
        found.get("WEB_CHAT_TRANSPORT",0)+
        found.get("MESSAGE_STATE",0))
    if owner=="ORIGINAL_DSH_NODE_MODULE":value+=3
    elif owner=="THIRD_PARTY_NODE_MODULE":value-=3
    return value
def normalized_name(name):
    if name.startswith("./"):name=name[2:]
    require(bool(name) and not name.startswith("/") and "\\" not in name and
            "\x00" not in name and ".." not in name.split("/") and
            all(segment not in ("",".") for segment in name.split("/")),
            "NONCANONICAL_TAR_NAME")
    return name
def inventory(original):
    require(original.stat().st_size==SOURCE_BYTES,"APK_LENGTH_CHANGED")
    require(file_hash(original)==SOURCE_SHA,"APK_SHA_CHANGED")
    with zipfile.ZipFile(original) as z:
        require(z.testzip() is None,"APK_ZIP_CRC")
        require(z.namelist().count(ENGINE_ENTRY)==1,"ENGINE_ARCHIVE_MISSING")
        raw=z.read(ENGINE_ENTRY)
    require(raw[:2]==b"\x1f\x8b","NOT_GZIP")
    seen=set(); members=0; add_ons=0; scanned=0; skipped=0; total=0
    owner_categories=collections.Counter()
    original_app_files=0
    original_app_entrypaths=[]
    original_app_static_imports=[]
    original_boot_packages=collections.Counter()
    original_boot_imports=[]
    ranked=[]
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gzip_stream:
        with tarfile.open(fileobj=gzip_stream,mode="r|") as tar:
            for member in tar:
                members+=1
                require(members<=50000,"MEMBER_LIMIT")
                name=normalized_name(member.name.rstrip("/"))
                require(name not in seen,"DUPLICATE_MEMBER")
                seen.add(name)
                require(member.isfile() or member.isdir(),"LINK_OR_SPECIAL_MEMBER")
                if not member.isfile():continue
                require(0<=member.size<=128*1024*1024,"MEMBER_OVERFLOW")
                if name.endswith(".node"):add_ons+=1
                if name.startswith("node_modules/@deepseek-ai/dsh/"):
                    original_app_files+=1
                    if name.endswith((".js",".mjs",".cjs")) and len(original_app_entrypaths)<120:
                        original_app_entrypaths.append(name)
                for prefix in ("node_modules/@deepseek-ai/dsh-app-boot/", "node_modules/@deepseek-ai/dsh-http-proxy/"):
                    if name.startswith(prefix):original_boot_packages[prefix]+=1
                if not name.endswith((".js",".mjs",".cjs",".html")):continue
                if member.size>MAX_ANALYZED_FILE:
                    skipped+=1;continue
                if total+member.size>MAX_ANALYZED_TOTAL:
                    skipped+=1;continue
                reader=tar.extractfile(member)
                require(reader is not None,"NO_MEMBER")
                blob=reader.read(MAX_ANALYZED_FILE+1)
                require(len(blob)==member.size,"SHORT_MEMBER")
                total+=len(blob);scanned+=1
                if name.startswith("node_modules/@deepseek-ai/dsh/"):
                    for hit in re.finditer(rb"(?:\bfrom\s+|\bimport\s*\(|\brequire\s*\()\s*['\"]([^'\"\r\n]{1,128})['\"]",blob):
                        dep=hit.group(1).decode("ascii",errors="ignore")
                        if re.fullmatch(r"[A-Za-z0-9._@/+:-]{1,128}",dep) and not dep.startswith(("http:","https:")):
                            if len(original_app_static_imports)<160:
                                original_app_static_imports.append({"module":name,"import":dep})
                if name.startswith(("node_modules/@deepseek-ai/dsh-app-boot/", "node_modules/@deepseek-ai/dsh-http-proxy/")):
                    if len(original_boot_imports)<120:
                        imports=[]
                        for hit in re.finditer(rb"(?:\bfrom\s+|\bimport\s*\(|\brequire\s*\()\s*['\"]([^'\"\r\n]{1,128})['\"]",blob):
                            dep=hit.group(1).decode("ascii",errors="ignore")
                            if re.fullmatch(r"[A-Za-z0-9._@/+:-]{1,128}",dep) and not dep.startswith(("http:","https:")):
                                imports.append(dep)
                            if len(imports)>=16:break
                        original_boot_imports.append({"path":name,"imports":imports,"signals":classify(blob)})
                found=classify(blob)
                if not found:continue
                owner=category(name)
                owner_categories[owner]+=1
                entry={"path_sha12":sha(name.encode())[:12],
                   "file_sha12":sha(blob)[:12],"owner_family":owner,
                   "bytes":len(blob),"categories":found,"score":score(found,owner)}
                # Private CI only: canonical archive member names are needed
                # to find an actual original patch target. No source content,
                # home paths, credentials or website/account data are emitted.
                if entry["score"]>=14 and owner!="THIRD_PARTY_NODE_MODULE":
                    if len(name)<=180 and re.fullmatch(r"[A-Za-z0-9._@/+-]+",name):
                        entry["source_member"]=name
                ranked.append(entry)
    require(members==EXPECTED_TAR_ENTRIES,"TAR_MEMBER_COUNT_CHANGED")
    require(add_ons==9,"ORIGINAL_NATIVE_ADDON_COUNT_CHANGED")
    ranked.sort(key=lambda x:(-x["score"],x["path_sha12"]))
    return {"exact_original_sha":True,"tar_members":members,"js_html_scanned":scanned,
      "js_html_skipped_bounded":skipped,"scanned_bytes":total,
      "owner_family_matches":dict(owner_categories),
      "exact_logged_original_dsh_npm_package_file_count":original_app_files,
      "original_dsh_npm_js_paths_sample":original_app_entrypaths[:32],
      "original_dsh_npm_static_import_edges":original_app_static_imports[:80],
      "original_boot_package_file_counts":dict(original_boot_packages),
      "original_boot_package_entry_imports":original_boot_imports[:40],
      "top_opaque_candidate_modules":ranked[:MAX_RESULT_ROWS],
      "chat_response_owner_proven":False,
      "original_engine_or_ui_modified":False,
      "android_main_activity_wiring_claimed":False}
def selftest():
    b=b'fetch("chat/completions"); const x="tool_calls"; data: [DONE]'
    c=classify(b)
    assert c["SSE_DELTA_TOOL"]==1 and c["ORIGINAL_HTTP_CHAT"]==1
    assert category("a/node_modules/@deepseek-ai/dsh/lib/index.js")=="ORIGINAL_DSH_NODE_MODULE"
    assert category("a/node_modules/third_party/foo.js")=="THIRD_PARTY_NODE_MODULE"
    assert category("node_modules/@google/genai/dist/web/index.mjs")=="THIRD_PARTY_NODE_MODULE"
    assert category("node_modules/@earendil-works/pi-ai/dist/api/mistral-conversations.js")=="THIRD_PARTY_NODE_MODULE"
    assert normalized_name("./a/ok.js")=="a/ok.js"
    try:normalized_name("../foo.js")
    except ValueError:pass
    else:raise AssertionError("unsafe tar name accepted")
    print("P96_SYNTHETIC_SOURCE_CATEGORY_CLASSIFIER=PASS")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--original");p.add_argument("--selftest",action="store_true")
    args=p.parse_args()
    if args.selftest:selftest()
    else:
        require(bool(args.original),"ORIGINAL_REQUIRED")
        report=inventory(pathlib.Path(args.original))
        print("P96_EXACT_ORIGINAL_NODE_WEB_OWNER_AUDIT=PASS")
        print("P96_SOURCE_OWNER_CATEGORIES="+json.dumps(report,sort_keys=True))
        print("P96_REAL_ORIGINAL_WEB_CHAT_RESPONSE_READ_CALLBACK_WIRED=NO")
