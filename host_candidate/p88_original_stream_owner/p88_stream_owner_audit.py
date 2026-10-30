#!/usr/bin/env python3
"""P88 read-only source-locked original DSH v138 SSE-to-UI surface inventory.

A DEX method mentioning SSE and a UI API is NOT evidence of actual network
data reaching a live chat bubble. Print categories and anonymous method hashes
only; never emit code, original method names, URLs, tokens, cookies or strings.
"""
import argparse,collections,hashlib,io,json,pathlib,re,zipfile
from androguard.core.dex import DEX
SOURCE_SHA="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
STRINGS={
 "text/event-stream":"MIME_SSE",
 "data:":"SSE_DATA_PREFIX",
 "[DONE]":"SSE_DONE",
 "stream":"STREAM_OPTION",
 "choices":"OPENAI_CHOICES",
 "delta":"OPENAI_DELTA",
 "reasoning_content":"OPENAI_REASONING",
 "tool_calls":"OPENAI_TOOL_CALLS",
 "event:":"SSE_EVENT_PREFIX",
}
API={
 "STREAM_READ":("Ljava/io/BufferedReader;->readLine(",
                "Ljava/io/InputStream;->read(",
                "Ljava/io/InputStreamReader;->read("),
 "HTTP_CLIENT":("Lokhttp3/","Ljava/net/HttpURLConnection;",
                "Lretrofit2/","Lcom/squareup/okhttp/"),
 "WEBVIEW_JS":("Landroid/webkit/WebView;->evaluateJavascript(",
               "Landroid/webkit/WebView;->loadUrl("),
 "STATE_FLOW":("Lkotlinx/coroutines/flow/MutableStateFlow;->setValue(",
               "Landroidx/lifecycle/MutableLiveData;->postValue(",
               "Landroidx/lifecycle/MutableLiveData;->setValue("),
 "ANDROID_TEXT":("Landroid/widget/TextView;->setText(",
                 "Landroid/text/Editable;->append("),
 "MAIN_DISPATCH":("Landroid/os/Handler;->post(",
                 "Landroid/app/Activity;->runOnUiThread("),
 "SSE_LIB":("Leventsource/","Lcom/launchdarkly/eventsource/",
            "Lcom/tylerthrailkill/"),
}
def sha(b):return hashlib.sha256(b).hexdigest()
def family(owner):
 if owner.startswith("Lcom/dsh/android/browser/"):return "DSH_BROWSER"
 if owner.startswith("Lcom/dsh/android/MainActivity"):return "DSH_MAIN"
 if "EngineManager" in owner:return "DSH_ENGINE"
 if any(x in owner.lower() for x in ("/chat","/message","/model","/api")):
  return "DSH_CHAT_OR_API_FAMILY"
 if owner.startswith("Lcom/dsh/android/"):return "DSH_OTHER"
 return "THIRD_PARTY"
def classify_outputs(consts,calls):
 strings={STRINGS[x] for x in consts if x in STRINGS}
 apis=collections.Counter()
 for output in calls:
  for key,prefixes in API.items():
   if any(p in output for p in prefixes):apis[key]+=1
 return strings,apis
def method_row(method,dex):
 consts=[];calls=[];count=0
 for _,ins in method.get_instructions_idx():
  count+=1
  if ins.get_name().startswith("const-string"):
   try:
    v=dex.get_cm_string(ins.get_ref_kind())
    if v in STRINGS:consts.append(v)
   except (AttributeError,IndexError,TypeError,ValueError):pass
  if ins.get_name().startswith("invoke-"):
   calls.append(ins.get_output())
 return consts,calls,count
def audit(apk):
 if sha(apk)!=SOURCE_SHA:raise ValueError("P88_UNPINNED_ORIGINAL_APK")
 with zipfile.ZipFile(io.BytesIO(apk)) as z:
  if z.testzip() is not None:raise ValueError("P88_ORIGINAL_CRC_FAILED")
  dexes=[(n,z.read(n)) for n in z.namelist()
         if re.fullmatch(r"classes\d*\.dex",n)]
 rows=[];total=collections.Counter();families=collections.Counter()
 for dexname,contents in dexes:
  d=DEX(contents)
  for cls in d.get_classes():
   owner=cls.get_name()
   if not owner.startswith("Lcom/dsh/android/"):continue
   for method in cls.get_methods():
    if method.get_code() is None:continue
    constants,calls,instructions=method_row(method,d)
    string_categories,api_categories=classify_outputs(constants,calls)
    if not string_categories and not api_categories:continue
    f=family(owner)
    families[f]+=1
    total.update(string_categories)
    total.update(api_categories)
    key=owner+"::"+method.get_name()+method.get_descriptor()
    rows.append({
     "id":sha(key.encode())[:12],
     "family":f,
     "dex":("PRIMARY" if dexname=="classes.dex" else "SECONDARY"),
     "instructions":instructions,
     "literal_categories":sorted(string_categories),
     "api_categories":{k:v for k,v in sorted(api_categories.items())},
     "sse_lit_and_reader_in_same_method":bool(
      ({"MIME_SSE","SSE_DATA_PREFIX","SSE_DONE"}&string_categories)
      and api_categories["STREAM_READ"]),
     "reader_and_ui_in_same_method":bool(
      api_categories["STREAM_READ"] and
      (api_categories["STATE_FLOW"] or api_categories["WEBVIEW_JS"]
       or api_categories["ANDROID_TEXT"]))
    })
 rows.sort(key=lambda r:(-int(r["sse_lit_and_reader_in_same_method"]),
                         -int(r["reader_and_ui_in_same_method"]),
                         -len(r["literal_categories"]),
                         -sum(r["api_categories"].values()),r["id"]))
 return {
  "original_dex_count":len(dexes),
  "candidate_methods_total":len(rows),
  "category_counts":dict(sorted(total.items())),
  "owner_family_method_counts":dict(sorted(families.items())),
  "sse_literal_plus_reader_methods":sum(r["sse_lit_and_reader_in_same_method"] for r in rows),
  "stream_reader_and_ui_methods":sum(r["reader_and_ui_in_same_method"] for r in rows),
  "top_anonymous_categorical_methods":rows[:35],
  "original_http_sse_to_live_chat_ui_proven":False,
  "omnigate_device_streaming_proven":False
 }
def selftest():
 s,a=classify_outputs(["text/event-stream","delta","stream"],
      ["v0, Ljava/io/BufferedReader;->readLine()Ljava/lang/String;",
       "v1, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V"])
 assert s=={"MIME_SSE","OPENAI_DELTA","STREAM_OPTION"}
 assert a["STREAM_READ"]==1 and a["ANDROID_TEXT"]==1
 assert family("Lcom/dsh/android/browser/BrowserBridge;")=="DSH_BROWSER"
 print("P88_SYNTHETIC_ORIGINAL_STREAM_UI_API_CLASSIFIER=PASS")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--original");p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 if a.selftest:selftest()
 else:
  if not a.original:p.error("original APK required")
  result=audit(pathlib.Path(a.original).read_bytes())
  print("P88_PINNED_ORIGINAL_DSH_STREAM_UI_SURFACE_AUDIT=PASS")
  print("P88_CATEGORICAL_ONLY="+json.dumps(result,sort_keys=True))
  print("P88_NO_ORIGINAL_SOURCE_OR_PRIVATE_VALUES_LOGGED=YES")
  print("P88_ORIGINAL_STREAM_RENDER_PATH_PROVEN=NO")
