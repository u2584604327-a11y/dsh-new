#!/usr/bin/env python3
"""Inspect ONLY original SHA-pinned DSH first-party Cordis/chat modules.
Static evidence, no executable loading or rewriting. No source text emitted.
"""
import argparse
import collections
import gzip
import io
import json
import pathlib
import re
import tarfile
import zipfile

from p96_original_engine_owner import (
    SOURCE_SHA, SOURCE_BYTES, ENGINE_ENTRY, EXPECTED_TAR_ENTRIES,
    file_hash, normalized_name, require, sha,
)

# Strict token families: an occurrence is a lead, not proven call direction.
SIGNALS = {
    "CORDIS_REGISTER": (b"@deepseek-ai/cordis", b"ctx.on(", b"ctx.emit("),
    "CORDIS_PLUGIN": (b"@deepseek-ai/cordis-plugin-loader", b"ctx.plugin(", b"registerPlugin"),
    "CHAT_STATE": (b"conversationId", b"sessionId", b"messageAdded", b"sendMessage"),
    "ASSISTANT_DELTA": (b"reasoning_content", b"tool_calls", b"onChunk", b"finish_reason"),
    "STREAMING": (b"ReadableStream", b"text/event-stream", b"getReader("),
    "TOOL_HANDOFF": (b"tool_result", b"toolResult", b"toolCall", b"toolCallId"),
    "LOCAL_SERVER": (b"createServer(", b"3080", b"listen("),
    "WEB_SOCKET": (b"WebSocket", b"socket.io", b"socket.on("),
}
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 200 * 1024 * 1024
MAX_CANDIDATES = 24
TARGET_PACKAGE_NAMES = frozenset(("dsh-agent-loop","dsh-llm","dsh-llm-pi-ai",
 "dsh-api-session-controller","dsh-api-settings-controller",
 "dsh-client-ui-chat","dsh-client-ui-conversation",
 "dsh-session-projection","dsh-client-connection"))
CONTRACT_LITERALS = (b"baseUrl", b"baseURL", b"apiKey", b"api_key",
 b"customProvider", b"openai-completions", b"createOpenAI",
 b"streamSimple", b"streamText", b"streamCompletion",
 b"onChunk", b"onMessage", b"assistantMessage",
 b"chat.completions", b"tool_calls", b"session.update",
 b"ctx.on(", b"ctx.emit(", b"subscribe(")
def package(path):
    pieces=path.split("/")
    if len(pieces) >= 4 and pieces[0]=="node_modules" and pieces[1]=="@deepseek-ai":
        return pieces[2]
    return None

def scan(path):
    require(path.stat().st_size==SOURCE_BYTES,"ORIGINAL_LENGTH_DRIFT")
    require(file_hash(path)==SOURCE_SHA,"ORIGINAL_SHA_DRIFT")
    with zipfile.ZipFile(path) as apk:
        require(apk.testzip() is None,"APK_CRC")
        require(apk.namelist().count(ENGINE_ENTRY)==1,"ENGINE_ENTRY_COUNT")
        raw=apk.read(ENGINE_ENTRY)
    require(raw[:2]==b"\x1f\x8b","GZIP_EXPECTED")
    count=0
    package_files=collections.Counter()
    package_hits=collections.defaultdict(collections.Counter)
    candidates=[]
    model_contract=[]
    route_contract=[]
    read_total=0
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:
        with tarfile.open(fileobj=g,mode="r|") as tar:
            for item in tar:
                count+=1
                require(count<=50000,"TAR_TOO_MANY")
                name=normalized_name(item.name.rstrip("/"))
                require(item.isfile() or item.isdir(),"NONREGULAR_MEMBER")
                if not item.isfile():continue
                pkg=package(name)
                if not pkg:continue
                package_files[pkg]+=1
                if not name.endswith((".js",".mjs",".cjs")):continue
                if item.size>MAX_FILE or read_total+item.size>MAX_TOTAL:continue
                f=tar.extractfile(item)
                require(f is not None,"MISSING_BYTES")
                blob=f.read(MAX_FILE+1)
                require(len(blob)==item.size,"SHORT_FILE")
                read_total+=len(blob)
                if name in (
                    "node_modules/@deepseek-ai/dsh-llm-pi-ai/lib/index.js",
                    "node_modules/@deepseek-ai/dsh-llm/lib/index.js",
                    "node_modules/@deepseek-ai/dsh-api-session-controller/lib/client.js",
                    "node_modules/@deepseek-ai/dsh-client-ui-chat/lib/client.js",
                ):
                    labels=(b"baseUrl",b"baseURL",b"apiKey",b"openai-completions",
                            b"streamSimple",b"session.update",b"subscribe(",
                            b"onMessage",b"tool_calls")
                    hits={q.decode("ascii"):blob.find(q) for q in labels if q in blob}
                    route_contract.append({"path":name,"size":len(blob),
                                           "sha12":sha(blob)[:12],"first_offsets":hits})
                if pkg in TARGET_PACKAGE_NAMES and len(model_contract)<90:
                    names=[v.decode("ascii") for v in CONTRACT_LITERALS if v in blob]
                    if names:
                        model_contract.append({"path":name,"hash12":sha(blob)[:12],
                                               "literal_indicators":names})
                hit={key:sum(word in blob for word in pats) for key,pats in SIGNALS.items()}
                hit={k:v for k,v in hit.items() if v}
                for k in hit:package_hits[pkg][k]+=1
                score=(5*hit.get("ASSISTANT_DELTA",0)
                    +4*hit.get("CHAT_STATE",0)
                    +4*hit.get("TOOL_HANDOFF",0)
                    +3*hit.get("CORDIS_REGISTER",0)
                    +2*hit.get("STREAMING",0)
                    +2*hit.get("LOCAL_SERVER",0))
                if score>=7:
                    candidates.append({
                        "path":name, "sha12":sha(blob)[:12],
                        "size":len(blob), "score":score, "signal_counts":hit,
                    })
    require(count==EXPECTED_TAR_ENTRIES,"TAR_MEMBER_DRIFT")
    candidates.sort(key=lambda x:(-x["score"],x["path"]))
    return {
        "exact_original_sha":True,
        "firstparty_package_files":dict(package_files),
        "firstparty_signals":{k:dict(v) for k,v in package_hits.items()},
        "firstparty_source_candidates":candidates[:MAX_CANDIDATES],
        "selected_original_model_provider_contract":model_contract,
        "original_model_to_session_literal_anchors":route_contract,
        "firstparty_js_bytes_read":read_total,
        "original_event_callback_identity_proven":False,
        "original_runtime_tool_return_proven":False,
        "original_package_modified":False,
    }
def selftest():
    assert package("node_modules/@deepseek-ai/dsh-app-boot/lib/index.js")=="dsh-app-boot"
    assert package("node_modules/@deepseek-ai/cordis/lib/index.js")=="cordis"
    assert package("node_modules/@google/genai/lib/index.js") is None
    print("P96_FIRSTPARTY_CORDIS_BOUNDARY_CLASSIFIER=PASS")
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--original");a.add_argument("--selftest",action="store_true")
    args=a.parse_args()
    if args.selftest:selftest()
    else:
        require(bool(args.original),"PINNED_INPUT_REQUIRED")
        result=scan(pathlib.Path(args.original))
        print("P96_FIRSTPARTY_ORIGINAL_PACKAGE_BOUNDARY=PASS")
        print("P96_FIRSTPARTY_CORDIS_CATEGORIES="+json.dumps(result,sort_keys=True))
        print("P96_ORIGINAL_LIVE_REPLY_BRIDGE=NOT_WIRED")
