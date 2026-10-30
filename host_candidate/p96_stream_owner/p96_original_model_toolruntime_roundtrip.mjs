/**
 * SHA-locked REAL DSH-v138 pi-ai model → REAL ToolRuntime.execute →
 * REAL Cordis tools/result → REAL pi-ai toolResult continuation.
 * Only the HTTP server is synthetic (127.0.0.1); registered tool is
 * pure fixed-memory data. No original Android engine/AgentLoop execution.
 */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {Context} from '@deepseek-ai/cordis';
import {ToolRuntime} from '@deepseek-ai/dsh-tools';
import {openAICompletionsApi} from '@earendil-works/pi-ai/api/openai-completions.lazy';

const modelId='fixture-model-local',toolId='call_fixture_0001';
const toolName='read_synthetic_fixture';
let posts=0,executions=0,notified=0;
let toolAdvertised=false,toolWireObserved=false;
const data=delta=>({id:'fixture-stream',object:'chat.completion.chunk',
 created:1,model:modelId,choices:[{index:0,delta,finish_reason:null}]});
const server=createServer(async(req,res)=>{
 if(req.url!=='/v1/chat/completions'||req.method!=='POST'){
   res.writeHead(404);res.end();return;
 }
 let raw='';
 for await(const part of req){
   raw+=part.toString('utf8');
   if(raw.length>16384){res.writeHead(413);res.end();return;}
 }
 let body;
 try{body=JSON.parse(raw)}catch{res.writeHead(400);res.end();return;}
 if(body.model!==modelId || body.stream!==true){
   res.writeHead(422);res.end();return;
 }
 posts++;
 let frames;
 if(posts===1){
   toolAdvertised=Array.isArray(body.tools)&&
     body.tools.some(x=>x.function?.name===toolName);
   frames=[
     data({role:'assistant'}),
     data({tool_calls:[{index:0,id:toolId,type:'function',
       function:{name:toolName,arguments:''}}]}),
     data({tool_calls:[{index:0,function:{arguments:'{"query":"fixture"}'}}]}),
     {...data({}),choices:[{index:0,delta:{},finish_reason:'tool_calls'}]}
   ];
 } else if(posts===2) {
   const toolMessages=(body.messages||[]).filter(x=>x.role==='tool');
   toolWireObserved=toolMessages.length===1 &&
     toolMessages[0].tool_call_id===toolId &&
     String(toolMessages[0].content).includes('fixture-read-success');
   frames=[
     data({role:'assistant'}),
     data({content:'synthetic continuation complete'}),
     {...data({}),choices:[{index:0,delta:{},finish_reason:'stop'}]}
   ];
 } else {res.writeHead(429);res.end();return;}
 res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-cache'});
 for(const frame of frames)res.write('data: '+JSON.stringify(frame)+'\n\n');
 res.end('data: [DONE]\n\n');
});
const cordis=new Context();
let unreg;
await new Promise((resolve,reject)=>{
 server.once('error',reject);
 server.listen(0,'127.0.0.1',resolve);
});
try{
 cordis.provide('systemPrompt',{tools(){return ()=>{};}});
 await cordis.plugin(ToolRuntime,{mode:'native',maxParallelSubCalls:1});
 const tools=cordis.get('tools');
 assert.equal(typeof tools?.execute,'function');
 cordis.on('tools/result',(exec,result)=>{
   notified++;
   assert.equal(exec.callId,toolId);
 });
 unreg=tools.register({
   name:toolName,
   description:'Read constant in-memory text only.',
   parameters:{type:'object',properties:{query:{type:'string'}},
     required:['query'],additionalProperties:false},
   output:{
     schema:{type:'object',properties:{value:{type:'string'}},
       required:['value'],additionalProperties:false},
     render:()=>[{type:'text',text:'fixture-read-success'}]
   },
   async execute(){ executions++;return {value:'fixture-read-success'}; }
 });
 const model={id:modelId,provider:'fixture',name:modelId,
   api:'openai-completions',baseUrl:'http://127.0.0.1:'+server.address().port+'/v1',
   reasoning:false,input:['text'],contextWindow:8192,maxTokens:128,
   cost:{input:0,output:0,cacheRead:0,cacheWrite:0}};
 const definition={name:toolName,description:'Read constant in-memory text only.',
   parameters:{type:'object',properties:{query:{type:'string'}},
     required:['query'],additionalProperties:false}};
 const messages=[
   {role:'system',content:'Synthetic test only',toolsAdded:[definition],timestamp:0},
   {role:'user',content:[{type:'text',text:'test local fixture'}],timestamp:1}
 ];
 const api=await openAICompletionsApi();
 const first=api.streamSimple(model,{messages},{
   apiKey:'synthetic-nonsecret',maxTokens:128
 });
 for await(const _event of first){}
 const assistant=await first.result();
 const calls=assistant.content.filter(x=>x.type==='toolCall');
 assert.equal(calls.length,1);
 assert.equal(calls[0].id,toolId);
 assert.equal(calls[0].name,toolName);
 assert.deepEqual(calls[0].arguments,{query:'fixture'});
 assert.equal(toolAdvertised,true,'first post must advertise actual tool');

 const result=await tools.execute({
   name:toolName,callId:calls[0].id,
   arguments:calls[0].arguments,signal:new AbortController().signal
 });
 assert.equal(result?.isError,false,'real ToolRuntime must accept original output');
 assert.equal(executions,1);
 assert.equal(notified,1);
 assert.ok(Array.isArray(result.content));
 const second=api.streamSimple(model,{
   messages:[...messages,assistant,{
     role:'toolResult',toolCallId:calls[0].id,toolName,
     content:result.content,isError:result.isError,timestamp:3
   }]
 },{apiKey:'synthetic-nonsecret',maxTokens:128});
 let reply='';
 for await(const event of second){
   if(event.type==='text_delta')reply+=String(event.delta||'');
 }
 assert.equal(reply,'synthetic continuation complete');
 assert.equal(posts,2,'exactly 2 model turns');
 assert.equal(toolWireObserved,true,'original tool result must appear in second request');
 assert.equal(executions,1);
 assert.equal(notified,1);
 process.stdout.write('P96_ORIGINAL_PI_AI_TOOLRUNTIME_TWO_TURN_ROUNDTRIP=PASS\n');
 process.stdout.write('P96_ORIGINAL_TOOL_RUNTIME_EXECUTIONS=1\n');
 process.stdout.write('P96_ORIGINAL_TOOL_RESULT_NOTIFICATIONS=1\n');
 process.stdout.write('P96_ORIGINAL_ANDROID_ENGINE_AGENT_LOOP=NOT_TESTED\n');
}catch(e){
 process.stdout.write('P96_ORIGINAL_PI_AI_TOOLRUNTIME_ROUNDTRIP=BLOCKED_'+
   (e?.code||e?.name||'UNKNOWN')+'\n');
 process.stdout.write('P96_FIXTURE_ERROR='+String(e?.message||'').slice(0,160)
   .replace(/\/[A-Za-z0-9._/-]+/g,'<PATH>')+'\n');
 process.exitCode=2;
}finally{
 if(typeof unreg==='function')unreg();
 await new Promise(resolve=>server.close(resolve));
 if(typeof cordis.dispose==='function')await cordis.dispose();
}
