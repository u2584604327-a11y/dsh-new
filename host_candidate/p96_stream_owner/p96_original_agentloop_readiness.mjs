/**
 * SHA-locked original AgentLoop service readiness probe.
 * No agent sessions created, no model, tool, files or network operations.
 * Only an isolated Cordis Context. Report required original services.
 */
import {Context} from '@deepseek-ai/cordis';
import {AgentLoop} from '@deepseek-ai/dsh-agent-loop';
import {ToolRuntime} from '@deepseek-ai/dsh-tools';

const label=(k,v)=>process.stdout.write('P96_ORIGINAL_AGENTLOOP_'+k+'='+String(v)+'\n');
const ctx=new Context();
const injection=AgentLoop.inject;
label('INJECT_TYPE',Array.isArray(injection)?'array':typeof injection);
if(Array.isArray(injection))label('INJECT_KEYS',injection.slice(0,35).join(','));
else if(injection && typeof injection==='object')label('INJECT_KEYS',Object.keys(injection).slice(0,35).join(','));
const required=(Array.isArray(injection)?injection:Object.keys(injection||{}))
 .filter(x=>typeof x==='string').slice(0,35);
for(const key of required)label('MISSING_'+key.toUpperCase(),ctx.get(key)===undefined?'YES':'NO');
ctx.provide('systemPrompt',{tools(){return ()=>{};}});
await ctx.plugin(ToolRuntime,{mode:'native',maxParallelSubCalls:1});
label('ORIGINAL_TOOL_RUNTIME_READY',typeof ctx.get('tools')?.execute==='function'?'YES':'NO');
let entered=false;
try {
  const f=ctx.plugin(AgentLoop,{});
  const handle=await f;
  entered=true;
  label('PLUGIN_ATTACHED','YES');
  label('PLUGIN_HANDLE_TYPE',typeof handle);
  label('CONTEXT_SERVICE_READY',typeof ctx.get('agentLoop'));
}catch(e){
  label('PLUGIN_ATTACHED','NO');
  label('ERROR_TYPE',e?.code||e?.name||'UNKNOWN');
  const msg=String(e?.message||'').slice(0,170)
    .replace(/\/[a-zA-Z0-9._/-]+/g,'<PATH>')
    .replace(/(?:Bearer |sk-)[a-zA-Z0-9._-]{8,}/g,'<REDACTED>');
  label('BLOCK_REASON',msg);
}
label('REAL_ORIGINAL_AGENT_LOOP_DISPATCH',entered?'NOT_STARTED':'BLOCKED_REQUIRED_SERVICE');
label('ANDROID_ENGINE_MANAGER_CONNECTED','NO');
