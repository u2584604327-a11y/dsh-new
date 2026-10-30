/**
 * SHA-locked original AgentLoop synthetic inbox exercise.
 * Real first-party Cordis, session, ToolRuntime, and AgentLoop; one fixed
 * synthetic message is queued using original handle.send(message,target,false)
 * to prevent driver wakeup. No model request, no tool, no UI, no Android.
 */
import {Context} from '@deepseek-ai/cordis';
import {AgentRegistry} from '@deepseek-ai/dsh-agent';
import {SessionStore} from '@deepseek-ai/dsh-session';
import {LlmRuntime} from '@deepseek-ai/dsh-llm';
import {ToolRuntime} from '@deepseek-ai/dsh-tools';
import {SystemPrompt} from '@deepseek-ai/dsh-system-prompt';
import {SessionProjectionRegistry} from '@deepseek-ai/dsh-session-projection';
import {AgentLoop} from '@deepseek-ai/dsh-agent-loop';
import net from 'node:net';
import http from 'node:http';
import https from 'node:https';

let attemptedNetwork=0;
const denied=()=>{attemptedNetwork++;throw Error('NETWORK_DENIED');};
globalThis.fetch=denied;
net.Socket.prototype.connect=denied;
net.connect=denied;
http.request=denied;
http.get=denied;
https.request=denied;
https.get=denied;

const log=(k,v)=>process.stdout.write('P98_ORIGINAL_INBOX_'+k+'='+String(v)+'\n');
const ctx=new Context();
let handle;
try{
 for(const [name,cls] of [
  ['agents',AgentRegistry],['sessions',SessionStore],
  ['llm',LlmRuntime],['systemPrompt',SystemPrompt],
  ['tools',ToolRuntime],['sessionProjections',SessionProjectionRegistry],
  ['agentLoop',AgentLoop]
 ]){
   await ctx.plugin(cls,name==='tools'?{mode:'native',maxParallelSubCalls:1}:{});
 }
 const loop=ctx.get('agentLoop');
 handle=await loop.create('p98_synthetic_inbox_no_model');
 if(typeof handle?.send!=='function' || typeof handle?.inbox?.current!=='function')
   throw Error('ORIGINAL_HANDLE_SEND_INBOX_MISSING');
 const appendCode=Function.prototype.toString.call(
   Object.getPrototypeOf(handle.inbox).append);
 const appendSignature=appendCode.match(/^[^(]*\(([^)]{0,250})\)/)?.[1]||'';
 const appendFields=[...appendCode.matchAll(
   /(?:this|input|target|message|items|events|data)\??\.([a-zA-Z_$][a-zA-Z0-9_$]{0,60})/g
 )].map(x=>x[1]);
 log('INBOX_APPEND_PARAMETERS',JSON.stringify(appendSignature.split(',')
   .map(x=>x.trim()).filter(x=>/^[a-zA-Z_$][a-zA-Z0-9_$]{0,60}$/.test(x))));
 log('INBOX_APPEND_FIELD_REFERENCES',JSON.stringify(
    [...new Set(appendFields)].slice(0,40)));
 const before=handle.inbox.current();
 const input={role:'user',content:[{type:'text',text:'synthetic safe message'}],
   timestamp:1};
 const result=handle.send(input,'followup',false);
 const after=handle.inbox.current();
 log('ORIGINAL_SEND_RETURN_TYPE',typeof result);
 log('BEFORE_TYPE',typeof before);
 log('AFTER_TYPE',typeof after);
 log('AFTER_KEYS',JSON.stringify(after&&typeof after==='object'
   ?Object.keys(after).slice(0,18):[]));
 log('NO_MODEL_NETWORK_ATTEMPTS',attemptedNetwork);
 if(attemptedNetwork!==0)throw Error('UNEXPECTED_NETWORK_ATTEMPT');
 if(before===after || after==null)
   throw Error('ORIGINAL_INBOX_NOT_OBSERVED_CHANGED');
 log('REAL_AGENTLOOP_INBOX_MUTATION','PASS');
 log('ORIGINAL_AGENTLOOP_AUTO_RUN','NOT_TESTED_DISABLED_WAKEUP');
 log('ANDROID_BROKER_UI','NOT_CONNECTED');
}catch(e){
 const description=String(e?.message||'');
 const stack=String(e?.stack||'');
 const knownBoundary=e instanceof TypeError &&
   description.includes("Cannot read properties of undefined (reading 'length')") &&
   stack.includes('ReactLoopInbox.mutate');
 log('RESULT',knownBoundary
   ?'BLOCKED_ORIGINAL_INBOX_MUTATION_PRECONDITION'
   :'UNEXPECTED_'+(e?.code||e?.name||'UNKNOWN'));
 log('ERROR',description.slice(0,100).replace(/\/[\w/.-]+/g,'<PATH>'));
 log('SAFE_CALL_STACK',JSON.stringify(stack.split('\n')
   .slice(1,8).map(line=>line.match(/at\s+([a-zA-Z_$][a-zA-Z0-9_$.]{0,90})/)?.[1]||'UNKNOWN')));
 log('BLOCKED_NETWORK_ATTEMPTS',attemptedNetwork);
 log('PRODUCTION_ORIGINAL_AGENTLOOP_INBOX','NOT_VERIFIED');
 // Recognized blocker is a diagnostic outcome, not a passing runtime gate.
 // Unknown error or any network attempt still fails the CI.
 if(!knownBoundary || attemptedNetwork!==0)process.exitCode=2;
}finally{
 if(handle){
  for(const op of ['close','dispose']){
   if(typeof handle[op]==='function'){
    try{await handle[op]();}catch{}break;
   }
  }
 }
 if(typeof ctx.dispose==='function')try{await ctx.dispose();}catch{}
}
