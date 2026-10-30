/**
 * Generate a minimal original-DSH pi-ai *provider profile*, not a full DSH
 * settings file. The actual target config collection/key must be verified
 * before applying. No network, filesystem or credentials involved.
 *
 * Original source proof: exact signed v138 engine dsh-llm-pi-ai/lib/index.js,
 * with api/openai-completions, baseURL, models and default limits.
 */
import {pathToFileURL} from 'node:url';

const API='openai-completions';
const BASE='http://127.0.0.1:8787/v1';

function validModelId(id) {
  return typeof id==='string' && /^[a-zA-Z0-9._:/+-]{1,128}$/.test(id);
}
function limit(value) {
  return Number.isSafeInteger(value) && value>=1 && value<=1048576;
}
export function makeOriginalDshOmniGateProfile({
  modelId, contextWindow, maxTokens, credentialEnv
}={}) {
  if(!validModelId(modelId)) throw Error('VALID_MODEL_ID_REQUIRED');
  if(!limit(contextWindow) || !limit(maxTokens) || maxTokens>contextWindow)
    throw Error('VERIFIED_MODEL_LIMITS_REQUIRED');
  if(credentialEnv!==undefined &&
      !(typeof credentialEnv==='string' &&
        /^[A-Z][A-Z0-9_]{2,63}$/.test(credentialEnv)))
    throw Error('CREDENTIAL_REFERENCE_NOT_KEY_REQUIRED');
  const profile={
    displayName:'OmniGate Local',
    api:API,
    baseURL:BASE,
    models:[{
      id:modelId,
      name:modelId,
      contextWindow,
      maxTokens,
      input:['text']
    }],
    defaultContextWindow:contextWindow,
    defaultMaxTokens:maxTokens,
    defaultInput:['text']
  };
  if(credentialEnv!==undefined)profile.apiKeyEnv=credentialEnv;
  return profile;
}
export function parseArguments(args) {
  if(args.length % 2 !== 0)throw Error('PAIRED_FLAGS_REQUIRED');
  const values={};
  const allowed=new Map([
    ['--model-id','modelId'],
    ['--context-window','contextWindow'],
    ['--max-tokens','maxTokens'],
    ['--credential-env','credentialEnv']
  ]);
  for(let i=0;i<args.length;i+=2) {
    const dest=allowed.get(args[i]);
    if(!dest || values[dest]!==undefined)throw Error('UNKNOWN_OR_DUPLICATE_FLAG');
    const raw=args[i+1];
    values[dest]=(dest==='contextWindow'||dest==='maxTokens')
      ? Number(raw):raw;
  }
  return values;
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    const config=makeOriginalDshOmniGateProfile(parseArguments(process.argv.slice(2)));
    process.stdout.write(JSON.stringify(config,null,2)+'\n');
  }catch(err) {
    process.stderr.write('DSH_OMNIGATE_PROFILE_BLOCKED='+err.message+'\n');
    process.exitCode=2;
  }
}
