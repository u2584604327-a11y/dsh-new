/**
 * DSH -> OmniGate read-only loopback preflight.
 * Run under the exact Node runtime intended to call the provider, to detect
 * differences between original Node and an isolated-UID Node.
 *
 * Only GET 127.0.0.1:8787/health and GET /v1/models. Never POSTs, binds,
 * reads cookies/tokens, stops a model, changes browser state or retries.
 * Only fixed-category results are printed; never outputs model names,
 * conversation content, credentials, URLs or any upstream response body.
 */
import http from 'node:http';
import { fileURLToPath } from 'node:url';

const MAX_BYTES = 32768;
const CONNECT_TIMEOUT_MS = 3500;
const READONLY_MARKER = 'Bearer omnigate-local-readonly-compat-check';

const routes = Object.freeze({
  main: 'main_socket_and_driver_match',
  overlay: 'overlay_socket_and_driver_match'
});

function category(error) {
  if (error?.code === 'EACCES' || error?.code === 'EPERM')
    return 'ISOLATED_LOOPBACK_DENIED';
  if (error?.code === 'ECONNREFUSED') return 'LOCAL_LISTENER_MISSING';
  if (error?.code === 'ETIMEDOUT' || error?.code === 'E_TIMEOUT')
    return 'LOCAL_LISTENER_TIMEOUT';
  if (error?.code === 'E_RESPONSE_TOO_LARGE') return 'RESPONSE_SIZE_EXCEEDED';
  if (error?.code === 'E_BAD_JSON') return 'INVALID_LOCAL_JSON';
  return 'LOCAL_TRANSPORT_UNKNOWN';
}

/** GET only, fixed literal local addresses, no redirects, no retries. */
function getJson(port, path, withPlaceholderKey = false) {
  return new Promise((resolve, reject) => {
    const headers = { Accept: 'application/json' };
    if (withPlaceholderKey) headers.Authorization = READONLY_MARKER;
    const req = http.request({
      protocol: 'http:', hostname: '127.0.0.1', port, path,
      method: 'GET', headers, agent: false, timeout: CONNECT_TIMEOUT_MS
    }, (res) => {
      const chunks = [];
      let length = 0;
      res.on('data', chunk => {
        length += chunk.length;
        if (length > MAX_BYTES) {
          req.destroy(Object.assign(new Error('size'), {code:'E_RESPONSE_TOO_LARGE'}));
          return;
        }
        chunks.push(chunk);
      });
      res.on('end', () => {
        if (res.statusCode !== 200) {
          resolve({status: Number(res.statusCode) || 0, json: null});
          return;
        }
        try {
          const json = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          resolve({status:200, json});
        } catch {
          reject(Object.assign(new Error('json'), {code:'E_BAD_JSON'}));
        }
      });
      res.on('error', reject);
    });
    req.on('timeout', () => req.destroy(Object.assign(new Error('timeout'), {code:'E_TIMEOUT'})));
    req.on('error', reject);
    req.end();
  });
}

export function evaluateHealth(h) {
  const verified = h?.ok === true &&
    h.listen === '127.0.0.1:8787' &&
    h.upstreamReachable === true &&
    (h.verifiedNativeOwner === 'main' || h.verifiedNativeOwner === 'overlay') &&
    h.observedRuntimeRoute === routes[h.verifiedNativeOwner];
  const upstream = h?.upstreamReachable === true;
  const owner = h?.verifiedNativeOwner === 'main' || h?.verifiedNativeOwner === 'overlay'
    ? h.verifiedNativeOwner : 'unknown';
  const route = h?.observedRuntimeRoute === routes.main ||
    h?.observedRuntimeRoute === routes.overlay
    ? 'matched' : 'unverified';
  return {
    service_ok: h?.ok === true,
    upstream_reachable: upstream,
    native_owner: owner,
    route_evidence: route,
    advisory_ready: verified,
    status: verified ? 'OWNER_VERIFIED_ADVISORY_ONLY'
      : !upstream ? 'UPSTREAM_UNREACHABLE_OR_UNKNOWN'
      : 'NATIVE_OWNER_UNVERIFIED_NO_POST'
  };
}

/** The port override exists only for isolated unit tests; CLI fixes 8787. */
export async function probe({port = 8787} = {}) {
  if (!Number.isInteger(port) || port < 1 || port > 65535)
    throw new TypeError('Invalid loopback port');
  const result = {
    probe: 'DSH_OMNIGATE_READONLY_V1',
    endpoint: '127.0.0.1:8787',
    issued_post: false,
    sent_user_message: false,
    restarted_runtime: false,
    verified_model_turn: false,
    verdict: 'NOT_CHECKED'
  };
  let health;
  try {health = await getJson(port, '/health');}
  catch (e) {
    result.verdict = category(e);
    return result;
  }
  if (health.status !== 200) {
    result.verdict = 'HEALTH_HTTP_NON200';
    result.health_http = health.status;
    return result;
  }
  const parsed = evaluateHealth(health.json);
  result.health = parsed;
  if (!parsed.advisory_ready) {
    result.verdict = parsed.status;
    return result;
  }
  let models;
  try {
    models = await getJson(port, '/v1/models', true);
  } catch (e) {
    result.verdict = category(e);
    return result;
  }
  result.models_http = models.status;
  if (models.status !== 200) {
    result.verdict = 'MODELS_HTTP_NON200';
    return result;
  }
  const data = models.json?.data;
  result.model_count = Array.isArray(data) && data.length <= 10000
    ? data.length : null;
  if (result.model_count === null || result.model_count === 0) {
    result.verdict = 'MODEL_CATALOG_EMPTY_OR_INVALID';
    return result;
  }
  result.verdict = 'READONLY_LOCAL_API_READY_NOT_MODEL_TURN_PROOF';
  return result;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  probe().then(result => {
    process.stdout.write(JSON.stringify(result) + '\n');
    // Fail closed for scripts using exit code as a gate.
    if (result.verdict !== 'READONLY_LOCAL_API_READY_NOT_MODEL_TURN_PROOF')
      process.exitCode = 2;
  }).catch(() => {
    process.stdout.write(JSON.stringify({
      probe:'DSH_OMNIGATE_READONLY_V1',
      issued_post:false, verdict:'LOCAL_PREFLIGHT_INTERNAL_ERROR'
    }) + '\n');
    process.exitCode = 2;
  });
}
