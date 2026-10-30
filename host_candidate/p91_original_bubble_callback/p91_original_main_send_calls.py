#!/usr/bin/env python3
"""P91 exact SHA-locked original MainActivity bubble callback reverse-callgraph.

No source, literals, credentials, user chat content or method names leave runner.
"""
import argparse, collections, hashlib, io, json, pathlib, re, zipfile
EXPECTED_SHA='3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5'
TARGET={'气泡注入结果':'BUBBLE_INJECTION_CALLBACK','气泡发送结果':'BUBBLE_CLICK_CALLBACK'}
APIS={
    'EVALUATE_JS': 'Landroid/webkit/WebView;->evaluateJavascript(',
    'WEBVIEW_LOAD': 'Landroid/webkit/WebView;->loadUrl(',
    'MAIN_POST': 'Landroid/os/Handler;->post(',
    'UI_THREAD': 'Landroid/app/Activity;->runOnUiThread(',
    'WEBVIEW_JS_CALLBACK': 'Landroid/webkit/ValueCallback;->onReceiveValue(',
}
CALL_RE=re.compile(r'Lcom/dsh/android/[^;\s]+;->[^\s(]+\([^)]*\)[^\s,]+')
def h(data):return hashlib.sha256(data).hexdigest()
def classify(calls):
    return {name:sum(pattern in s for s in calls) for name,pattern in APIS.items()
            if any(pattern in s for s in calls)}
def invoke_target(s,known):
    match=CALL_RE.search(s)
    if not match:return None
    key=match.group(0)
    return key if key in known else None

def audit(raw):
    from androguard.core.dex import DEX
    if h(raw)!=EXPECTED_SHA:raise ValueError('P91_UNPINNED_ORIGINAL_APK')
    records={}; original_targets={}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:raise ValueError('P91_BAD_ORIGINAL_ZIP_CRC')
        dexes=[(name,z.read(name)) for name in z.namelist() if re.fullmatch(r'classes\d*\.dex',name)]
    if len(dexes)!=2:raise ValueError('P91_UNEXPECTED_DEX_LAYOUT')
    for dexfile,raw_dex in dexes:
        dex=DEX(raw_dex)
        for cls in dex.get_classes():
            owner=cls.get_name()
            if not owner.startswith('Lcom/dsh/android/'):continue
            for m in cls.get_methods():
                if m.get_code() is None:continue
                key=owner+'->'+m.get_name()+m.get_descriptor()
                labels=set(); calls=[]
                for _,ins in m.get_instructions_idx():
                    if ins.get_name().startswith('const-string'):
                        try:
                            value=str(dex.get_cm_string(ins.get_ref_kind()))
                            labels.update(kind for literal,kind in TARGET.items() if literal in value)
                        except (AttributeError,ValueError,IndexError,TypeError):pass
                    elif ins.get_name().startswith('invoke-'):
                        calls.append(ins.get_output())
                records[key]={'calls':calls,'dex':dexfile,'labels':labels,'main':owner.startswith('Lcom/dsh/android/MainActivity')}
                if labels and owner.startswith('Lcom/dsh/android/MainActivity'):
                    original_targets[key]=sorted(labels)
    incoming=collections.defaultdict(set)
    edge_count=0
    keys=set(records)
    for method,info in records.items():
        for inv in info['calls']:
            callee=invoke_target(inv,keys)
            if callee:
                incoming[callee].add(method)
                edge_count+=1
    output=[]
    for method,labels in sorted(original_targets.items(),key=lambda t:t[1]):
        frontier={method};seen={method};levels=[]
        for depth in range(1,4):
            parents=set().union(*(incoming.get(item,set()) for item in frontier))
            parents.difference_update(seen)
            seen.update(parents)
            levels.append({'depth':depth,'caller_count':len(parents),
                           'caller_api_categories':dict(collections.Counter(
                               name for x in parents for name,count in classify(records[x]['calls']).items()
                               for _ in range(count)))})
            frontier=parents
        output.append({'target_hash12':h(method.encode())[:12],
                       'labels':labels,'dex':'PRIMARY' if records[method]['dex']=='classes.dex' else 'SECONDARY',
                       'direct_api_categories':classify(records[method]['calls']),
                       'reverse_invocation_levels':levels})
    return {'pinned_original':True,'dex_count':len(dexes),'app_method_count':len(records),
            'direct_app_edges_found':edge_count,
            'original_target_log_method_count':len(original_targets),
            'targets':output,'exact_production_send_fix_proven':False}
def selftest():
    known={'Lcom/dsh/android/MainActivity;->send(Ljava/lang/String;)V'}
    assert invoke_target('v0, Lcom/dsh/android/MainActivity;->send(Ljava/lang/String;)V',known)==next(iter(known))
    assert invoke_target('v0, Lcom/dsh/android/MainActivity;->unrelated()V',known) is None
    assert classify(['v0, Landroid/webkit/WebView;->evaluateJavascript(Ljava/lang/String;Landroid/webkit/ValueCallback;)V'])['EVALUATE_JS']==1
    print('P91_SYNTHETIC_EXACT_REVERSE_CALLGRAPH_CLASSIFIER=PASS')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original');p.add_argument('--selftest',action='store_true');a=p.parse_args()
    if a.selftest:selftest()
    else:
        if not a.original:p.error('exact original APK required')
        report=audit(pathlib.Path(a.original).read_bytes())
        print('P91_EXACT_ORIGINAL_CALLGRAPH_CATEGORICAL='+json.dumps(report,sort_keys=True))
        print('P91_ORIGINAL_BUBBLE_CLICK_AND_NEW_USER_TURN_WIRED=NO')
