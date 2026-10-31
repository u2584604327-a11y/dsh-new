/**
 * One-shot diagnostic through the original AgentRegistry factory path.
 * No prompt, no model generation, no tool execution, outbound network denied.
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

let networkAttempts=0;
const deny=()=>{networkAttempts++;throw new Error('P98_FACTORY_NETWORK_DENIED');};
globalThis.fetch=deny;
net.Socket.prototype.connect=deny;
net.connect=deny;
net.createConnection=deny;
http.request=deny; http.get=deny;
https.request=deny; https.get=deny;

const log=(k,v)=>process.stdout.write('P98_FACTORY_CREATE_'+k+'='+String(v)+'\n');
const safeName=x=>typeof x==='string'&&/^[A-Za-z0-9_.:/-]{1,100}$/.test(x);
const shape=o=>o&&typeof o==='object'?Object.keys(o)
  .filter(x=>/^[A-Za-z_$][A-Za-z0-9_$]{0,64}$/.test(x)).slice(0,40):[];

const ctx=new Context();
let agent=null;
try{
  for(const [name,cls] of [
    ['agents',AgentRegistry],['sessions',SessionStore],
    ['llm',LlmRuntime],['systemPrompt',SystemPrompt],
    ['tools',ToolRuntime],['sessionProjections',SessionProjectionRegistry],
    ['agentLoop',AgentLoop]
  ]) await ctx.plugin(cls,name==='tools'?{mode:'native',maxParallelSubCalls:1}:{});

  const agents=ctx.get('agents');
  const factoryTarget=agents?.factory?.target;
  log('REGISTRY_CONSTRUCTOR',agents?.constructor?.name||'MISSING');
  log('FACTORY_TARGET_CONSTRUCTOR',factoryTarget?.constructor?.name||'MISSING');
  log('FACTORY_TARGET_IS_CONTEXT_AGENTLOOP',factoryTarget===ctx.get('agentLoop'));

  const sessionId='p98_factory_path_no_prompt';
  const options={
    sessionId,
    agentOptions:{provider:'p98-no-provider',model:'p98-no-model'},
    meta:{cwd:process.cwd(),agentPreset:undefined},
    setup:undefined
  };
  log('OPTIONS_KEYS',JSON.stringify(Object.keys(options)));
  log('AGENT_OPTIONS_KEYS',JSON.stringify(Object.keys(options.agentOptions)));
  log('META_KEYS',JSON.stringify(Object.keys(options.meta)));

  try{
    agent=await Promise.race([
      agents.create(options),
      new Promise((_,reject)=>setTimeout(()=>reject(new Error('P98_FACTORY_CREATE_TIMEOUT')),3500))
    ]);
    log('OUTCOME','CREATED');
    log('RETURN_CONSTRUCTOR',agent?.constructor?.name||'MISSING');
    log('RETURN_KEYS',JSON.stringify(shape(agent)));
    log('RETURN_ID_MATCH',agent?.id===sessionId);
    log('REGISTRY_GET_SAME',agents.get(sessionId)===agent);
    log('SESSION_STORE_PRESENT',Boolean(ctx.get('sessions')?.get(sessionId)));
    const inbox=agent?.inbox?.current?.();
    log('INBOX_CURRENT_TYPE',Array.isArray(inbox)?'array':typeof inbox);
    log('INBOX_CURRENT_KEYS',JSON.stringify(shape(inbox)));
    const session=agent?.session;
    let events=[];
    try{
      const snapshot=session?.snapshotEvents?.();
      if(Array.isArray(snapshot))events=snapshot;
    }catch{}
    const eventTypes=events.map(e=>e?.type??e?.event?.type)
      .filter(safeName).slice(0,40);
    log('SESSION_EVENT_COUNT',events.length);
    log('SESSION_EVENT_TYPES',JSON.stringify(eventTypes));
    const projections=agent?.inbox?.projections;
    if(typeof projections?.stateOf==='function'){
      const state=projections.stateOf(session,'inbox');
      log('INBOX_PROJECTION_KEYS',JSON.stringify(shape(state)));
    }
  }catch(error){
    const msg=String(error?.message||'').slice(0,160)
      .replace(/(?:\/[^\s]+)+/g,'<PATH>');
    log('OUTCOME','BLOCKED');
    log('ERROR_TYPE',String(error?.name||'UNKNOWN').replace(/[^A-Za-z0-9_]/g,''));
    log('ERROR_MESSAGE',msg);
    log('SAFE_STACK',JSON.stringify(String(error?.stack||'').split('\n').slice(1,7)
      .map(x=>x.match(/at\s+([A-Za-z_$][A-Za-z0-9_$.]{0,100})/)?.[1]||'UNKNOWN')));
  }
} finally {
  log('NETWORK_ATTEMPTS',networkAttempts);
  if(agent){
    for(const op of ['close','dispose']){
      if(typeof agent[op]==='function'){try{await agent[op]();}catch{}break;}
    }
  }
  try{await ctx.dispose?.();}catch{}
}
if(networkAttempts!==0)process.exitCode=2;
log('NO_PROMPT','YES');
log('NO_TOOL','YES');
log('MODEL_GENERATION','NOT_REQUESTED');
