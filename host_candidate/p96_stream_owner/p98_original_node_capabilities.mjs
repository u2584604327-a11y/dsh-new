/**
 * Read-only capability check for the *actual* DSH original Node process.
 * It is not a Node installer, polyfill or bootstrap override.
 * Never reads env, files, process arguments, network, tokens or user data.
 * Standalone CLI may be invoked ONLY through an already trusted original
 * DSH diagnostic channel. CI results describe the runner, not the phone.
 */
import {pathToFileURL} from 'node:url';

export function readOriginalNodeCapabilities(
  {nodeVersion=process.versions.node,
   platform=process.platform,
   arch=process.arch,
   withResolvers=typeof Promise.withResolvers==='function',
   abortAny=typeof AbortSignal.any==='function',
   structuredCloneAvailable=typeof structuredClone==='function'}={}
) {
  const v=String(nodeVersion);
  if(!/^\d{1,3}\.\d{1,3}\.\d{1,3}(?:[-+][A-Za-z0-9.-]{1,64})?$/.test(v))
    throw Error('NODE_VERSION_NOT_SAFE');
  const major=Number(v.split('.')[0]);
  const ready=major>=22 && withResolvers && abortAny && structuredCloneAvailable;
  return Object.freeze({
    source:'current-node-runtime-not-apk-inference',
    nodeVersion:v,
    platform:/^[A-Za-z0-9_-]{1,25}$/.test(platform)?platform:'unknown',
    arch:/^[A-Za-z0-9_-]{1,25}$/.test(arch)?arch:'unknown',
    promiseWithResolvers:withResolvers,
    abortSignalAny:abortAny,
    structuredClone:structuredCloneAvailable,
    originalAgentLoopFeatureGate:ready?'READY_FOR_FURTHER_TEST':'BLOCKED',
    realAndroidEngineManagerVerified:false,
    originalAgentLoopTurnTested:false
  });
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href){
  try {
    const status=readOriginalNodeCapabilities();
    process.stdout.write('P98_ORIGINAL_NODE_CAPABILITIES='+JSON.stringify(status)+'\n');
    process.exitCode=status.originalAgentLoopFeatureGate==='READY_FOR_FURTHER_TEST'?0:2;
  }catch {
    process.stdout.write('P98_ORIGINAL_NODE_CAPABILITIES=UNAVAILABLE\n');
    process.exitCode=2;
  }
}
