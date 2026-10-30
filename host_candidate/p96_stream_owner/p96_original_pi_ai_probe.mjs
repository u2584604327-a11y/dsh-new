/**
 * Exact-original DSH pi-ai lazy API factory runtime probe.
 * Runs without browser, credentials or non-loopback requests.
 */
import * as pi from '@earendil-works/pi-ai';
import {openAICompletionsApi} from '@earendil-works/pi-ai/api/openai-completions.lazy';

if(!Object.keys(pi).length || typeof openAICompletionsApi!=='function') {
  process.stdout.write('P96_ORIGINAL_COMPLETIONS_FACTORY=UNAVAILABLE\n');
  process.exitCode=2;
} else {
  process.stdout.write('P96_ORIGINAL_COMPLETIONS_FACTORY_IMPORTED=PASS\n');
  const api=await openAICompletionsApi();
  process.stdout.write('P96_ORIGINAL_COMPLETIONS_FACTORY_RESULT_TYPE='+typeof api+'\n');
  const methods=api==null?[]:Object.keys(api).filter(k=>/stream|api|request/i.test(k));
  process.stdout.write('P96_ORIGINAL_COMPLETIONS_RUNTIME_METHODS='+JSON.stringify(methods)+'\n');
  if(typeof api?.stream==='function' && typeof api?.streamSimple==='function') {
    process.stdout.write('P96_ORIGINAL_COMPLETIONS_REAL_STREAM_METHODS=PASS\n');
  } else {
    process.stdout.write('P96_ORIGINAL_COMPLETIONS_REAL_STREAM_METHODS=NOT_PROVEN\n');
    process.exitCode=2;
  }
}
process.stdout.write('P96_REAL_ORIGINAL_STREAM_CALL_TO_LOCAL_FIXTURE=NOT_TESTED\n');
