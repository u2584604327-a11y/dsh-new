#!/usr/bin/env python3
"""Exact pinned original v138 EngineManager Node-spawn contract, READ ONLY.
No DEX string literals, APK bytes, user files, credentials or command
arguments emitted. Static call graph is not a live DSH call path.
"""
import argparse,collections,hashlib,json,pathlib,re,zipfile
from loguru import logger
logger.disable('androguard')
from androguard.core.dex import DEX

EXPECTED='3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5'
TARGET='Lcom/dsh/android/EngineManager$start$2;->invokeSuspend(Ljava/lang/Object;)'
CODE_OFF=3163260
PC=3912
INVOKE=re.compile(r'(L[^\s,;]+;)->([^\s(,]+)\(([^)]*)\)')
RELATED=re.compile(r'ProcessBuilder|Runtime;|Process;|InputStream|OutputStream|Termux|Node|Engine|exec|waitFor|destroy|start|preflight|probe|shutdown',re.I)

def sha(path):
    digest=hashlib.sha256()
    with open(path,'rb') as source:
        for chunk in iter(lambda:source.read(2<<20),b''):digest.update(chunk)
    return digest.hexdigest()

def method_id(m):
    return m.get_class_name()+'->'+m.get_name()+m.get_descriptor().split(')',1)[0]+')'

def safe(s):
    return (s if len(s)<350 else
            s[:290]+'#sha256:'+hashlib.sha256(s.encode()).hexdigest()[:16])

def inspect(apk):
    if sha(apk)!=EXPECTED:raise ValueError('P35_ORIGINAL_SIGNED_V138_SHA_MISMATCH')
    with zipfile.ZipFile(apk) as z:
        if z.testzip() is not None:raise ValueError('P35_ZIP_CRC_MISMATCH')
        names=sorted(n for n in z.namelist()
            if re.fullmatch(r'classes(?:[2-9][0-9]*)?\.dex',n))
        if 'classes.dex' not in names:raise ValueError('P35_MAIN_DEX_MISSING')
        blobs={name:z.read(name) for name in names}
    found={}
    for name,raw in blobs.items():
        d=DEX(raw)
        for cls in d.get_classes():
            if not cls.get_name().startswith('Lcom/dsh/android/'):continue
            for m in cls.get_methods():
                if m.get_code() is None:continue
                ident=method_id(m)
                if ident==TARGET or ident.startswith((
                    'Lcom/dsh/android/EngineManager;->',
                    'Lcom/dsh/android/termux/TermuxBootstrap;->nodeIsUsable(')):
                    found[ident]=(name,m)
    if TARGET not in found:raise ValueError('P35_ENGINE_COROUTINE_NOT_FOUND')
    primary_dex,m=found[TARGET]
    if primary_dex!='classes.dex' or m.get_code_off()!=CODE_OFF:
        raise ValueError('P35_ENGINE_COROUTINE_CODE_OFFSET_DRIFT')
    calls=[];branches=[]
    for pc,i in m.get_instructions_idx():
        if i.get_name().startswith('invoke-'):
            x=INVOKE.search(i.get_output())
            if x:calls.append({'pc':pc,'op':i.get_name(),'target':safe(x.group(0))})
        elif i.get_name().startswith(('if-','goto','return','throw','packed-switch','sparse-switch')):
            branches.append(i.get_name())
    starts=[x for x in calls if x['target']=='Ljava/lang/ProcessBuilder;->start()']
    if len(starts)!=1 or starts[0]['pc']!=PC:
        raise ValueError('P35_ORIGINAL_ENGINE_START_PC_DRIFT')
    if len(calls)<10 or len(branches)<3:
        raise ValueError('P35_COROUTINE_CODE_IMPLAUSIBLE')
    # Preserve the *real original host* post-launch Process handle,
    # reader thread, startup synchronization and READY state contract.
    # A naive replace-ProcessBuilder-with-Binder patch would violate all.
    must_have={
        3924:'Lcom/dsh/android/EngineManager;->access$setProcess$p(',
        3980:'Lcom/dsh/android/EngineManager$start$2',
        3986:'Ljava/lang/Thread;-><init>(',
        4010:'Ljava/lang/Thread;->start()',
        4026:'Ljava/util/concurrent/CountDownLatch;->await(',
        4674:'Lkotlinx/coroutines/flow/MutableStateFlow;->setValue(',
    }
    by_pc={x['pc']:x['target'] for x in calls}
    for pc,api in must_have.items():
        if not by_pc.get(pc,'').startswith(api):
            raise ValueError('P35_ENGINE_PROCESS_LIFECYCLE_EDGE_DRIFT_'+str(pc))
    lifecycle=[{'pc':pc,'target':by_pc[pc]} for pc in sorted(must_have)]

    near=[x for x in calls if abs(x['pc']-PC)<=900]
    if len(near)>150:raise ValueError('P35_CALLSITES_UNBOUNDED')
    support=[]
    for name,(dex,other) in sorted(found.items()):
        if name==TARGET or not any(key in name for key in (
            'EngineManager;->start(','EngineManager;->stop(',
            'EngineManager;->preflight(','EngineManager;->probeBoot(',
            'EngineManager;->runDumpConfig(','TermuxBootstrap;->nodeIsUsable(')):
            continue
        rel=[]
        for pc,i in other.get_instructions_idx():
            if not i.get_name().startswith('invoke-'):continue
            x=INVOKE.search(i.get_output())
            if x and RELATED.search(x.group(0)):
                rel.append({'pc':pc,'callee':safe(x.group(0))})
        support.append({'method':safe(name),'dex':dex,
                        'code_off':other.get_code_off(),
                        'related_calls':rel[:40]})
    return {
       'gate':'STATIC_EXACT_ORIGINAL_ENGINE_SPAWN_CONTRACT',
       'exact_original_signed_apk_sha256':EXPECTED,
       'method':TARGET,'dex':primary_dex,
       'primary_code_off':m.get_code_off(),'primary_start_pc':PC,
       'primary_start_invokes':starts,
       'primary_total_invokes':len(calls),
       'primary_control_flow_count':len(branches),
       'post_spawn_required_lifecycle_api_edges':lifecycle,
       'original_java_Process_handle_and_daemon_reader_thread':'REQUIRED_BY_ORIGINAL_DEX',
       'countdown_latch_and_ready_state_flow':'REQUIRED_BY_ORIGINAL_DEX',
       'near_start_invocations':near,
       'selected_related_invocations':[x for x in calls if RELATED.search(x['target'])][:100],
       'other_engine_start_stop_probe_callbacks':support[:24],
       'original_DSH_runtime_wiring':'NOT_IMPLEMENTED',
       'P32_grant_broker_connected_to_original_engine':'NO',
       'reflected_jni_js_dynamic_invokes':'NOT_COVERED',
       'original_apk_modified':False,
       'v139_release':'BLOCKED',
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('original_v138')
    p.add_argument('--report',required=True)
    args=p.parse_args()
    result=inspect(args.original_v138)
    pathlib.Path(args.report).write_text(
        json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({
        'P35_EXACT_ORIGINAL_SIGNED_APK':'PASS',
        'P35_EXACT_ENGINE_START_METHOD':'PASS',
        'P35_ENGINE_COROUTINE_CALLS_NEAR_START':result['near_start_invocations'],
        'P35_ENGINE_CONTROL_FLOW_COUNT':result['primary_control_flow_count'],
        'P35_ORIGINAL_ENGINE_CALL_INTERPOSED':'NO',
        'P35_V139_RELEASE':'BLOCKED',
    },ensure_ascii=False,indent=2))

if __name__=='__main__':main()
