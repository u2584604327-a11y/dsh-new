/**
 * Exact DSH-v138 original ToolRuntime register → execute → result test.
 *
 * Real original Cordis Context + ToolRuntime. Only test double is a
 * no-op systemPrompt.tools registration function (required dependency).
 * Test tool is pure in-memory, no side effects, filesystem, browser, model.
 */
import assert from 'node:assert/strict';
import {Context} from '@deepseek-ai/cordis';
import {ToolRuntime} from '@deepseek-ai/dsh-tools';

const ctx=new Context();
const logs=[];
let executions=0;
let registration;
try {
  ctx.provide('systemPrompt',{tools(){return ()=>{};}});
  await ctx.plugin(ToolRuntime,{mode:'native',maxParallelSubCalls:1});
  const runtime=ctx.get('tools');
  assert.equal(typeof runtime?.register,'function');
  assert.equal(typeof runtime?.execute,'function');
  ctx.on('tools/result',(exec,result)=>logs.push({exec,result}));
  registration=runtime.register({
    name:'read_synthetic_fixture',
    description:'Returns one fixed in-memory value; never accesses any device.',
    parameters:{
      type:'object',properties:{query:{type:'string'}},
      required:['query'],additionalProperties:false
    },
    output:{
      schema:{
        type:'object',properties:{value:{type:'string'}},
        required:['value'],additionalProperties:false
      },
      render:()=>[{type:'text',text:'fixture-read-success'}]
    },
    async execute(args) {
      executions++;
      return {value:'fixture-read-success'};
    }
  });
  process.stdout.write('P96_REAL_RUNTIME_REGISTRATION_TYPE='+typeof registration+'\n');
  const result=await runtime.execute({
    name:'read_synthetic_fixture',
    callId:'call_fixture12345',
    arguments:{query:'fixture'},
    signal:new AbortController().signal
  });
  process.stdout.write('P96_REAL_RUNTIME_EXECUTION_COUNT='+executions+'\n');
  process.stdout.write('P96_REAL_RUNTIME_RESULT_OBSERVED='+logs.length+'\n');
  process.stdout.write('P96_REAL_RUNTIME_RESULT_IS_ERROR='+Boolean(result?.isError)+'\n');
  process.stdout.write('P96_REAL_RUNTIME_RESULT_KIND='+typeof result+'\n');
  if(result?.isError){
    process.stdout.write('P96_REAL_RUNTIME_TYPED_ERROR='+
      (result?.error?.name||result?.error?.code||'UNKNOWN')+'\n');
    const err=String(result?.error?.message||'').slice(0,190)
      .replace(/\/[A-Za-z0-9._/-]+/g,'<PATH>');
    process.stdout.write('P96_REAL_RUNTIME_ERROR_MESSAGE='+err+'\n');
    process.stdout.write('P96_REAL_RUNTIME_CONTENT_KINDS='+JSON.stringify(
      (result?.content||[]).slice(0,4).map(x=>({
        type:x.type, safeText:x.type==='text'
          ? String(x.text).slice(0,160)
             .replace(/\/[A-Za-z0-9._/-]+/g,'<PATH>') : null
      })))+'\n');
  }
  assert.equal(executions,1,'only one registered tool body may run');
  assert.equal(logs.length,1,'real original tools/result event exactly once');
  assert.equal(logs[0].exec.callId,'call_fixture12345');
  assert.equal(logs[0].result,result);
  assert.notEqual(result?.isError,true,'no synthetic tool error');
  process.stdout.write('P96_ORIGINAL_TOOL_RUNTIME_REGISTER_EXECUTE_NOTIFY=PASS\n');
  process.stdout.write('P96_ANDROID_BROWSER_AND_AGENT_CONTINUATION=NOT_TESTED\n');
} catch(e) {
  process.stdout.write('P96_ORIGINAL_TOOL_RUNTIME_EXECUTION=BLOCKED_'+
    (e?.code||e?.name||'UNKNOWN')+'\n');
  // The thrown message from a synthetic no-secret fixture is bounded,
  // with source paths scrubbed if present; never print the stack.
  const detail=String(e?.message||'').slice(0,180)
    .replace(/\/[a-zA-Z0-9._/-]+/g,'<PATH>');
  process.stdout.write('P96_ORIGINAL_TOOL_RUNTIME_ERROR_DETAIL='+detail+'\n');
  process.exitCode=2;
} finally {
  if(typeof registration==='function')registration();
  if(typeof ctx.dispose==='function')await ctx.dispose();
}
