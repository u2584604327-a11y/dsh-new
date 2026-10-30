import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { evaluateHealth, probe } from './omnigate_local_preflight.mjs';

function owner(kind='main') {
  return {
    ok:true, listen:'127.0.0.1:8787', upstreamReachable:true,
    verifiedNativeOwner:kind,
    observedRuntimeRoute:kind==='main'
      ? 'main_socket_and_driver_match'
      : 'overlay_socket_and_driver_match'
  };
}
async function serve(handler, action) {
  const server=http.createServer(handler);
  await new Promise((resolve,reject) => {
    server.once('error',reject);
    server.listen(0,'127.0.0.1',resolve);
  });
  try {return await action(server.address().port);}
  finally {await new Promise(resolve => server.close(resolve));}
}
function json(res,obj,status=200) {
  res.writeHead(status,{'Content-Type':'application/json'});
  res.end(JSON.stringify(obj));
}

test('Verified original MainActivity: GET health and models only; no POST or secrets', async () => {
  const calls=[];
  await serve((req,res) => {
    calls.push({method:req.method,path:req.url,
                auth: Boolean(req.headers.authorization)});
    if(req.url==='/health')json(res,owner());
    else if(req.url==='/v1/models')json(res,{data:[{id:'hidden'}]});
    else json(res,{error:'unexpected'},404);
  },async port => {
    const report=await probe({port});
    assert.equal(report.verdict,'READONLY_LOCAL_API_READY_NOT_MODEL_TURN_PROOF');
    assert.equal(report.health.native_owner,'main');
    assert.equal(report.model_count,1);
    assert.equal(report.verified_model_turn,false);
    assert.equal(report.issued_post,false);
  });
  assert.deepEqual(calls,[
    {method:'GET',path:'/health',auth:false},
    {method:'GET',path:'/v1/models',auth:true}
  ]);
  console.log('P96_DSH_TO_OMNIGATE_READONLY_MAIN_PREFLIGHT=PASS');
});

test('Overlay original runtime can be verified without a main-activity takeover',async () => {
  await serve((req,res) => {
    if(req.url==='/health')json(res,owner('overlay'));
    else json(res,{data:[{id:'private-model'}]});
  },async port=>{
    const report=await probe({port});
    assert.equal(report.verdict,'READONLY_LOCAL_API_READY_NOT_MODEL_TURN_PROOF');
    assert.equal(report.health.native_owner,'overlay');
    assert.equal(report.health.advisory_ready,true);
    assert.equal(report.restarted_runtime,false);
  });
  console.log('P96_VERIFIED_OVERLAY_NO_OWNER_HANDOFF=PASS');
});

test('Owner mismatch blocks model probing instead of bypassing 409',async () => {
  let requests=0;
  await serve((req,res)=>{
    requests++;
    json(res,{...owner(),verifiedNativeOwner:'unknown',
      observedRuntimeRoute:'port_not_owned_by_main'});
  },async port=>{
    const report=await probe({port});
    assert.equal(report.verdict,'NATIVE_OWNER_UNVERIFIED_NO_POST');
    assert.equal(report.issued_post,false);
  });
  assert.equal(requests,1);
  assert.equal(evaluateHealth({...owner(),verifiedNativeOwner:'overlay'})
    .advisory_ready,false);
  console.log('P96_409_RUNTIME_OWNER_FAIL_CLOSED=PASS');
});

test('Service or model-list errors do not trigger a POST or a retry',async () => {
  let requests=0;
  await serve((req,res)=>{
    requests++;
    if(req.url==='/health')json(res,owner());
    else json(res,{error:'auth'},401);
  },async port=>{
    const report=await probe({port});
    assert.equal(report.verdict,'MODELS_HTTP_NON200');
    assert.equal(report.models_http,401);
    assert.equal(report.issued_post,false);
  });
  assert.equal(requests,2);
  console.log('P96_MODELS_ERROR_NO_RETRY=PASS');
});

test('200 without a usable model catalog is not a ready provider',async () => {
  await serve((req,res)=>{
    if(req.url==='/health')json(res,owner());
    else json(res,{data:[]});
  },async port=>{
    const report=await probe({port});
    assert.equal(report.verdict,'MODEL_CATALOG_EMPTY_OR_INVALID');
    assert.equal(report.model_count,0);
    assert.equal(report.issued_post,false);
  });
  console.log('P96_NO_FALSE_READY_ON_EMPTY_MODEL_CATALOG=PASS');
});
