import test from 'node:test';
import assert from 'node:assert/strict';
import {readOriginalNodeCapabilities} from './p98_original_node_capabilities.mjs';
const base={nodeVersion:'22.8.1',platform:'android',arch:'arm64',
  withResolvers:true,abortAny:true,structuredCloneAvailable:true};
test('eligible feature set identifies ready for further tests not production',()=>{
 const c=readOriginalNodeCapabilities(base);
 assert.equal(c.originalAgentLoopFeatureGate,'READY_FOR_FURTHER_TEST');
 assert.equal(c.realAndroidEngineManagerVerified,false);
 assert.equal(c.originalAgentLoopTurnTested,false);
 assert.equal(c.source,'current-node-runtime-not-apk-inference');
 console.log('P98_ANDROID_NODE_FEATURE_GATE_NON_PRODUCTION=PASS');
});
test('old Node or missing Promise.withResolvers fails closed',()=>{
 for(const c of [
   {...base,nodeVersion:'20.20.0'},
   {...base,nodeVersion:'18.0.0'},
   {...base,withResolvers:false},
   {...base,abortAny:false},
   {...base,structuredCloneAvailable:false}
 ])assert.equal(readOriginalNodeCapabilities(c).originalAgentLoopFeatureGate,'BLOCKED');
 console.log('P98_OLD_NODE_AND_MISSING_RUNTIME_FEATURE_FAIL_CLOSED=PASS');
});
test('node metadata is small and sanitized with no environment leakage',()=>{
 assert.throws(()=>readOriginalNodeCapabilities({...base,nodeVersion:'bad\nAPI_KEY=secret'}));
 const c=readOriginalNodeCapabilities({...base,platform:'/data/app/secret'});
 assert.equal(c.platform,'unknown');
 assert.ok(!JSON.stringify(c).includes('secret'));
 console.log('P98_NO_NODE_FILES_CREDENTIALS_OR_PATHS=PASS');
});
