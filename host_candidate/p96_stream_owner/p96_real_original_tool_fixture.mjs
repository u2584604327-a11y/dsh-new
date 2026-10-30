/**
 * Exact original pi-ai two-turn tool-call serialization fixture.
 * 1) synthetic SSE tool_calls emitted by a localhost fake OpenAI endpoint.
 * 2) locally fabricated harmless toolResult is passed to the ORIGINAL
 *    pi-ai client, and the backend must receive role=tool in its context.
 * Never executes tools / browser / Node commands / Bilibili actions.
 * Does NOT prove DSH AgentLoop, Cordis, broker or Android functionality.
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {openAICompletionsApi} from '@earendil-works/pi-ai/api/openai-completions.lazy';

const id='synthetic-provider-model', callId='call_fixture_01';
const events=[];
const observations={requests:0,firstRoles:[],secondRoles:[],toolDefinition:false,
  toolReplyObserved:false};

function chunk(delta,finish_reason=null) {
  return JSON.stringify({
    id:'synthetic-stream',object:'chat.completion.chunk',created:1,
    model:id,choices:[{index:0,delta,finish_reason}]
  });
}
function send(res,frames){
  res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-cache'});
  for(const frame of frames)res.write('data: '+frame+'\n\n');
  res.end('data: [DONE]\n\n');
}
const srv=createServer(async(req,res)=>{
  if(req.method!=='POST'||req.url!=='/v1/chat/completions'){
    res.writeHead(404);res.end();return;
  }
  let raw='';
  for await(const part of req){
    raw+=part.toString('utf8');
    if(raw.length>32768){res.writeHead(413);res.end();return;}
  }
  let reqBody;
  try {reqBody=JSON.parse(raw)}catch{res.writeHead(400);res.end();return;}
  observations.requests++;
  const roles=(reqBody.messages||[]).map(m=>m.role);
  if(!reqBody.stream||reqBody.model!==id) {
    res.writeHead(422);res.end();return;
  }
  if(observations.requests===1){
    observations.firstRoles=roles;
    observations.toolDefinition=Array.isArray(reqBody.tools) &&
      reqBody.tools.some(x=>x.function?.name==='read_fixture_page');
    observations.firstToolCount=Array.isArray(reqBody.tools)?reqBody.tools.length:0;
    observations.firstToolShapes=Array.isArray(reqBody.tools)
      ? reqBody.tools.slice(0,2).map(x=>({
          type:x.type??null,
          fieldNames:Object.keys(x),
          nestedFunctionFields:Object.keys(x.function||{})
        })):[];

    send(res,[
      chunk({role:'assistant'}),
      chunk({tool_calls:[{index:0,id:callId,type:'function',
        function:{name:'read_fixture_page',arguments:''}}]}),
      chunk({tool_calls:[{index:0,function:{arguments:'{"page":"fixture"}'}}]}),
      chunk({},'tool_calls')
    ]);
  }else if(observations.requests===2){
    observations.secondRoles=roles;
    observations.toolReplyObserved=roles.includes('tool');
    send(res,[chunk({role:'assistant'}),chunk({content:'tool received'}),
      chunk({},'stop')]);
  }else{
    res.writeHead(429);res.end();
  }
});
await new Promise((resolve,reject)=>{
  srv.once('error',reject);
  srv.listen(0,'127.0.0.1',resolve);
});
try {
  const model={
    id,provider:'local-original-fixture',name:id,api:'openai-completions',
    baseUrl:'http://127.0.0.1:'+srv.address().port+'/v1',
    reasoning:false,input:['text'],contextWindow:8192,maxTokens:128,
    cost:{input:0,output:0,cacheRead:0,cacheWrite:0}
  };
  const api=await openAICompletionsApi();
  // The exact original pi-ai calls resolveTranscriptTools(context.messages).
  // Tool declarations use system-message toolsAdded (not tools) in the transcript,
  // not a separate, ignored context.tools property.
  const toolDefinition={name:'read_fixture_page',
    description:'Synthetic local read; no external I/O',
    parameters:{type:'object',properties:{page:{type:'string'}},required:['page']}};
  const ctx={messages:[
    {role:'system',content:'Synthetic local test only',
      toolsAdded:[toolDefinition],timestamp:0},
    {role:'user',content:[{type:'text',text:'safe local tool request'}],
      timestamp:1}
  ]};
  const first=api.streamSimple(model,ctx,{apiKey:'test-placeholder',maxTokens:128});
  for await(const e of first)events.push(e.type);
  const assistant=await first.result();
  const tool=(assistant?.content||[]).find(x=>x.type==='toolCall');
  process.stdout.write('P96_ORIGINAL_PROVIDER_SENT_TOOL_COUNT='+observations.firstToolCount+'\n');
  process.stdout.write('P96_ORIGINAL_PROVIDER_TOOL_SHAPES='+JSON.stringify(observations.firstToolShapes)+'\n');
  process.stdout.write('P96_ORIGINAL_TOOL_STREAM_EVENT_TYPES='+JSON.stringify(events)+'\n');
  process.stdout.write('P96_ORIGINAL_TOOL_STREAM_CONTENT_KINDS='+JSON.stringify(
    assistant?.content?.map(x=>x.type)||[])+'\n');
  if(!tool||tool.id!==callId||tool.name!=='read_fixture_page')
    throw Error('ORIGINAL_PROVIDER_TOOLCALL_NOT_ASSEMBLED');
  assert.deepEqual(tool.arguments,{page:'fixture'});
  assert.equal(observations.toolDefinition,true,'original request must advertise a tool');

  const withResult={
    messages:[...ctx.messages,assistant,
      {role:'toolResult',toolCallId:tool.id,toolName:tool.name,
       content:[{type:'text',text:'safe synthetic page data'}],
       isError:false,timestamp:3}]
  };
  const second=api.streamSimple(model,withResult,{
    apiKey:'test-placeholder',maxTokens:128
  });
  let reply='';
  for await(const e of second){
    if(e.type==='text_delta')reply+=String(e.delta||'');
  }
  assert.equal(reply,'tool received','original adapter must complete second turn');
  assert.equal(observations.requests,2,'exactly two user-driven test model calls');
  assert.equal(observations.toolReplyObserved,true,'wire format must contain role=tool');
  process.stdout.write('P96_REAL_ORIGINAL_PI_AI_TOOLCALL_ASSEMBLY=PASS\n');
  process.stdout.write('P96_REAL_ORIGINAL_PI_AI_TOOL_RESULT_WIRE_SERIALIZATION=PASS\n');
  process.stdout.write('P96_REAL_DSH_TOOL_EXECUTOR_AND_AGENT_LOOP=NOT_TESTED\n');
} finally {
  await new Promise(resolve=>srv.close(resolve));
}
