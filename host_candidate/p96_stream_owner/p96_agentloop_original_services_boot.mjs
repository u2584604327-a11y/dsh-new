/**
 * Original DSH service readiness using ONLY SHA-pinned first-party classes.
 * No agent creation, no session, API call, browser, credentials or user data.
 * Do not substitute fake agents/sessions/llm/projections to make CI green.
 */
import {Context} from '@deepseek-ai/cordis';
import {AgentRegistry} from '@deepseek-ai/dsh-agent';
import {SessionStore} from '@deepseek-ai/dsh-session';
import {LlmRuntime} from '@deepseek-ai/dsh-llm';
import {ToolRuntime} from '@deepseek-ai/dsh-tools';
import {SystemPrompt} from '@deepseek-ai/dsh-system-prompt';
import {SessionProjectionRegistry} from '@deepseek-ai/dsh-session-projection';
import {AgentLoop} from '@deepseek-ai/dsh-agent-loop';

const ctx=new Context();
const modules=[
 ['agents',AgentRegistry],
 ['sessions',SessionStore],
 ['llm',LlmRuntime],
 ['systemPrompt',SystemPrompt],
 ['tools',ToolRuntime],
 ['sessionProjections',SessionProjectionRegistry],
 ['agentLoop',AgentLoop]
];
const report=(k,v)=>process.stdout.write('P96_REAL_ORIGINAL_BOOT_'+k+'='+String(v)+'\n');
for(const [name,Class] of modules) {
  const deps=Array.isArray(Class.inject)?Class.inject
    :Class.inject&&typeof Class.inject==='object'?Object.keys(Class.inject):[];
  report(name.toUpperCase()+'_REQUIRED',JSON.stringify(deps.slice(0,20)));
  const options=name==='tools'?{mode:'native',maxParallelSubCalls:1}:{};
  try {
    const handle=await ctx.plugin(Class,options);
    report(name.toUpperCase()+'_PLUGIN','ATTACHED');
    report(name.toUpperCase()+'_SERVICE',typeof ctx.get(name));
  }catch(e) {
    report(name.toUpperCase()+'_PLUGIN','BLOCKED');
    report(name.toUpperCase()+'_ERROR_TYPE',e?.code||e?.name||'UNKNOWN');
    const message=String(e?.message||'').slice(0,150)
      .replace(/\/[a-zA-Z0-9._/-]+/g,'<PATH>')
      .replace(/(?:Bearer |sk-)[a-zA-Z0-9._-]{8,}/g,'<REDACTED>');
    report(name.toUpperCase()+'_ERROR',message);
  }
}
const required=['agents','sessions','llm','tools','systemPrompt','sessionProjections'];
const missing=required.filter(name=>ctx.get(name)===undefined);
report('MISSING_REQUIRED',JSON.stringify(missing));
report('AGENT_LOOP_SERVICE',typeof ctx.get('agentLoop'));
report('ACTUAL_MODEL_TOOL_AUTOCONTINUATION','NOT_TESTED');
report('ANDROID_ENGINE_MANAGER_CONNECTED','NO');
report('ORIGINAL_SERVICE_PROVIDERS_SOURCE_LOCKED','YES');
report('NODE_MAJOR',process.versions.node.split('.')[0]);
report('PROMISE_WITH_RESOLVERS',typeof Promise.withResolvers);
const agent=ctx.get('agentLoop');
if (missing.length!==0 || typeof agent?.create!=='function' ||
    typeof Promise.withResolvers!=='function') {
  report('REAL_AGENTLOOP_SERVICE_READY','FAIL');
  process.exitCode=2;
} else {
  report('REAL_AGENTLOOP_SERVICE_READY','PASS');
}

