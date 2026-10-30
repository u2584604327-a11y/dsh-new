/**
 * Exact original pi-ai openAICompletionsApi().streamSimple() against
 * a strictly synthetic 127.0.0.1 local SSE server. No user model/account,
 * no external network, no real DSH/UI, no SDK mocks.
 */
import {createServer} from 'node:http';
import assert from 'node:assert/strict';
import {openAICompletionsApi} from '@earendil-works/pi-ai/api/openai-completions.lazy';

const testId = 'synthetic-original-pi-ai';
const localOutput = 'synthetic reply';
const counters = {requests:0,posts:0,streams:0,bytes:0};
const chunks = [
  {id:testId,object:'chat.completion.chunk',created:1,model:testId,
    choices:[{index:0,delta:{role:'assistant'},finish_reason:null}]},
  {id:testId,object:'chat.completion.chunk',created:1,model:testId,
    choices:[{index:0,delta:{content:'synthetic '},finish_reason:null}]},
  {id:testId,object:'chat.completion.chunk',created:1,model:testId,
    choices:[{index:0,delta:{content:'reply'},finish_reason:null}]},
  {id:testId,object:'chat.completion.chunk',created:1,model:testId,
    choices:[{index:0,delta:{},finish_reason:'stop'}]}
];
const server=createServer(async (req,res)=>{
  counters.requests++;
  if(req.method!=='POST'||req.url!=='/v1/chat/completions'){
    res.writeHead(404);res.end();return;
  }
  counters.posts++;
  let body='';
  for await(const part of req){
    counters.bytes+=part.length;
    if(counters.bytes>16384){res.writeHead(413);res.end();return;}
    body+=part.toString('utf8');
  }
  let data;
  try{data=JSON.parse(body)}catch{res.writeHead(400);res.end();return;}
  if(data.model!==testId || data.stream!==true ||
      !Array.isArray(data.messages)|| !data.messages.some(x=>x.role==='user')){
    res.writeHead(422);res.end();return;
  }
  counters.streams++;
  res.writeHead(200,{
    'Content-Type':'text/event-stream',
    'Cache-Control':'no-cache',
    'Connection':'keep-alive'
  });
  for(const chunk of chunks){
    res.write('data: '+JSON.stringify(chunk)+'\n\n');
    await new Promise(resolve=>setTimeout(resolve,8));
  }
  res.end('data: [DONE]\n\n');
});
await new Promise((resolve,reject)=>{
  server.once('error',reject);
  server.listen(0,'127.0.0.1',resolve);
});
try {
  const port=server.address().port;
  const model={
    id:testId,provider:'local-fixture',name:testId,
    api:'openai-completions',baseUrl:'http://127.0.0.1:'+port+'/v1',
    reasoning:false,input:['text'],contextWindow:8192,maxTokens:128,
    cost:{input:0,output:0,cacheRead:0,cacheWrite:0}
  };
  const context={
    messages:[{
      role:'user',content:[{type:'text',text:'synthetic prompt'}],
      timestamp:1
    }]
  };
  const api=await openAICompletionsApi();
  assert.equal(typeof api.streamSimple,'function');
  const stream=api.streamSimple(model,context,{
    apiKey:'non-secret-test-placeholder',maxTokens:128
  });
  const types=[];
  let content='';
  for await(const event of stream){
    types.push(event.type??'missing');
    if(event.type==='text_delta'){
      content+=String(event.delta??event.text??'');
    }
  }
  process.stdout.write('P96_ORIGINAL_REAL_PI_AI_STREAM_EVENT_TYPES='+JSON.stringify(types.slice(0,32))+'\n');
  process.stdout.write('P96_ORIGINAL_PI_AI_LOCAL_POST_COUNT='+counters.posts+'\n');
  process.stdout.write('P96_ORIGINAL_PI_AI_LOCAL_STREAM_COUNT='+counters.streams+'\n');
  process.stdout.write('P96_ORIGINAL_PI_AI_TEXT_OUTPUT_LENGTH='+content.length+'\n');
  if(counters.requests!==1 || counters.posts!==1 || counters.streams!==1)
    throw Error('ORIGINAL_API_NOT_ONE_STREAMING_POST');
  if(content!==localOutput)throw Error('ORIGINAL_API_CONTENT_NOT_DELIVERED');
  process.stdout.write('P96_REAL_ORIGINAL_PI_AI_LOCAL_SSE_TO_TEXT=PASS\n');
  process.stdout.write('P96_REAL_DSH_CORDIS_AND_UI_CONTINUATION=NOT_TESTED\n');
} finally {
  await new Promise(resolve=>server.close(resolve));
}
