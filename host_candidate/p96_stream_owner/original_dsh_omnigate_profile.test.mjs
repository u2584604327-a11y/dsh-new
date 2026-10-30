import test from 'node:test';
import assert from 'node:assert/strict';
import {makeOriginalDshOmniGateProfile,parseArguments} from './original_dsh_omnigate_profile.mjs';

const known={
  modelId:'example-model-from-a-user-verified-list',
  contextWindow:8192,
  maxTokens:1024
};
test('Existing DSH pi-ai OpenAI completions route profile matches source schema',()=>{
  const result=makeOriginalDshOmniGateProfile(known);
  assert.equal(result.api,'openai-completions');
  assert.equal(result.baseURL,'http://127.0.0.1:8787/v1');
  assert.equal(result.models.length,1);
  assert.equal(result.models[0].id,known.modelId);
  assert.equal(result.models[0].contextWindow,known.contextWindow);
  assert.equal(result.models[0].maxTokens,known.maxTokens);
  assert.deepEqual(result.models[0].input,['text']);
  assert.deepEqual(result.defaultInput,['text']);
  assert.equal(result.defaultContextWindow,known.contextWindow);
  assert.equal(result.defaultMaxTokens,known.maxTokens);
  assert.equal('apiKeyEnv' in result,false);
  assert.equal('apiKey' in result,false);
  assert.equal('Authorization' in result,false);
  assert.equal('tools' in result,false);
  console.log('P96_ORIGINAL_PI_AI_PROVIDER_PROFILE=PASS');
});
test('Reference an existing DSH credential name, never embed secret',()=>{
  const p=makeOriginalDshOmniGateProfile({...known,credentialEnv:'OMNIGATE_LOCAL_API_KEY'});
  assert.equal(p.apiKeyEnv,'OMNIGATE_LOCAL_API_KEY');
  assert.ok(!JSON.stringify(p).includes('Bearer '));
  assert.ok(!JSON.stringify(p).includes('"apiKey":'));
  console.log('P96_CREDENTIAL_REFERENCE_NOT_SECRET=PASS');
});
test('Never fabricate model id or context budget',()=>{
  for(const invalid of [
    {},{modelId:'unknown'}, {...known,modelId:''},
    {...known,maxTokens:8193},{...known,contextWindow:0},
    {...known,contextWindow:NaN},{...known,maxTokens:1.5},
    {...known,credentialEnv:'sk-leaked-key'},
    {...known,credentialEnv:'EVIL=secret'},
    {...known,modelId:'../../injection\nAuthorization:'}
  ]) {
    assert.throws(()=>makeOriginalDshOmniGateProfile(invalid));
  }
  console.log('P96_NO_GUESSED_MODELS_OR_CONTEXT_CAPACITY=PASS');
});
test('CLI rejects unknown, duplicate or unpaired flags',()=>{
  assert.deepEqual(parseArguments([
    '--model-id',known.modelId,'--context-window','8192',
    '--max-tokens','1024'
  ]),known);
  assert.throws(()=>parseArguments(['--model-id','abc','--model-id','xyz']));
  assert.throws(()=>parseArguments(['--secret','foo']));
  assert.throws(()=>parseArguments(['--model-id']));
  console.log('P96_NO_UNAUTHORISED_CONFIG_FLAGS=PASS');
});
