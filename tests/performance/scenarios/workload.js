import http from 'k6/http';
import exec from 'k6/execution';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { SharedArray } from 'k6/data';

const target = required('LAB_TARGET_ORIGIN').replace(/\/$/, '');
const scenarioName = required('LAB_SCENARIO');
const publicOrigin = __ENV.LAB_PUBLIC_ORIGIN || target;
const runId = required('LAB_RUN_ID');
const durationSeconds = intEnv('LAB_DURATION_SECONDS', 30);
const targetRps = numberEnv('LAB_TARGET_RPS', 100);
const retryCount = intEnv('LAB_RETRIES_PER_ACTOR', 0);
const configuredHumans = intEnv('LAB_HUMAN_ACTORS', 0);
const configuredBots = intEnv('LAB_BOT_ACTORS', 0);

const fixture = new SharedArray('private actor-to-credential mapping', () => {
  const parsed = JSON.parse(open(required('LAB_CREDENTIALS_FILE')));
  if (!parsed.drop_id || !Array.isArray(parsed.actors)) {
    throw new Error('credential fixture must contain drop_id and actors');
  }
  return [parsed];
})[0];

const successfulLatency = new Trend('fairdrop_successful_request_latency', true);
const networkErrors = new Counter('fairdrop_network_errors');
const expected429 = new Counter('fairdrop_expected_429');
const expected403 = new Counter('fairdrop_expected_403');
const expected409 = new Counter('fairdrop_expected_409');
const unexpected5xx = new Counter('fairdrop_unexpected_5xx');
const acceptedEntry = new Rate('fairdrop_entry_accepted');

const people = flattenActors(fixture.actors);
const humans = people.filter((person) => person.cohort === 'human').slice(0, configuredHumans);
const bots = people.filter((person) => person.cohort === 'bot').slice(0, configuredBots);
const allPeople = humans.concat(bots);

if (allPeople.length !== configuredHumans + configuredBots) {
  throw new Error('private credential fixture does not satisfy configured cohort counts');
}
if (scenarioName === 'shared_ip' && __ENV.LAB_SHARED_IP_TOPOLOGY !== 'confirmed') {
  throw new Error('shared_ip requires a controlled source-network topology; forwarded headers are not accepted');
}
if (['worker_restart', 'redis_failure'].includes(scenarioName) && __ENV.LAB_FAILURE_INJECTION_CONFIRMED !== 'confirmed') {
  throw new Error(`${scenarioName} requires the allowlisted host-side failure controller`);
}

export const options = optionsFor(scenarioName);

export default function () {
  const person = select(allPeople);
  runPerson(person);
}

export function botWave() {
  runPerson(select(bots));
}

export function humanWave() {
  runPerson(select(humans));
}

function runPerson(person) {
  const session = login(person);
  if (!session) return;

  if (scenarioName === 'retry_flood') {
    const firstKey = uuid();
    for (let attempt = 0; attempt <= retryCount; attempt += 1) {
      enter(session, fixture.drop_id, attempt % 2 === 0 ? firstKey : uuid(), person);
    }
    return;
  }

  if (scenarioName === 'policy_compare') {
    const drops = fixture.policy_drop_ids;
    if (!drops || !drops.fcfs_demo || !drops.lottery) {
      throw new Error('policy_compare requires policy_drop_ids.fcfs_demo and policy_drop_ids.lottery');
    }
    const order = exec.scenario.iterationInTest % 2 === 0
      ? [drops.fcfs_demo, drops.lottery]
      : [drops.lottery, drops.fcfs_demo];
    for (const dropId of order) enter(session, dropId, uuid(), person);
    return;
  }

  const response = enter(session, fixture.drop_id, uuid(), person);
  if (scenarioName === 'reconnect') {
    // Intentionally discard the write response and reconcile from authoritative state.
    getState(session, fixture.drop_id, person);
  } else if (scenarioName === 'expiry_race') {
    confirmAtBoundary(session, response, person);
  } else if (['normal', 'early_bot', 'credential_farm', 'shared_ip', 'worker_restart', 'redis_failure'].includes(scenarioName)) {
    getState(session, fixture.drop_id, person);
  }
}

function login(person) {
  const response = request('POST', '/api/v1/auth/session', JSON.stringify({ access_code: person.access_code }), {
    headers: { 'Content-Type': 'application/json', Origin: publicOrigin },
    tags: tags(person, 'login'),
  });
  if (response.status !== 200) return null;
  const body = safeJson(response);
  if (!body || !body.csrf_token) return null;
  return { csrf: body.csrf_token };
}

function enter(session, dropId, operationKey, person) {
  const response = request('POST', `/api/v1/drops/${dropId}/entries`, '{}', {
    headers: writeHeaders(session.csrf, operationKey),
    tags: { ...tags(person, 'entry'), drop_id: dropId },
  });
  acceptedEntry.add(response.status === 200 || response.status === 201, tags(person, 'entry'));
  return response;
}

function getState(_session, dropId, person) {
  return request('GET', `/api/v1/drops/${dropId}/me`, null, { tags: tags(person, 'state') });
}

function confirmAtBoundary(session, entryResponse, person) {
  const body = safeJson(entryResponse);
  const reservation = body && body.reservation;
  if (!reservation || !reservation.id || !reservation.expires_at) return;
  const offset = intEnv('LAB_EXPIRY_OFFSET_MS', 0);
  const waitSeconds = (Date.parse(reservation.expires_at) - Date.now() + offset) / 1000;
  if (waitSeconds > 0) sleep(Math.min(waitSeconds, durationSeconds));
  request('POST', `/api/v1/reservations/${reservation.id}/confirm`, '{}', {
    headers: writeHeaders(session.csrf, uuid()),
    tags: tags(person, 'confirm'),
  });
}

function request(method, path, body, params) {
  const response = http.request(method, `${target}${path}`, body, {
    redirects: 0,
    timeout: '30s',
    ...params,
  });
  const metricTags = (params && params.tags) || {};
  console.log('FD_MEASURE ' + JSON.stringify({ endpoint: metricTags.endpoint || 'unknown',
    status: response.status, latency_ms: response.timings.duration, public_id: metricTags.public_id || '',
    drop_id: metricTags.drop_id || '' }));
  if (response.error_code) networkErrors.add(1, metricTags);
  if (response.status >= 200 && response.status < 400) successfulLatency.add(response.timings.duration, metricTags);
  if (response.status === 429) expected429.add(1, metricTags);
  if (response.status === 403) expected403.add(1, metricTags);
  if (response.status === 409) expected409.add(1, metricTags);
  if (response.status >= 500) unexpected5xx.add(1, metricTags);
  check(response, { 'response is expected class': (res) => res.status < 500 }, metricTags);
  return response;
}

function optionsFor(name) {
  const base = {
    discardResponseBodies: false,
    summaryTrendStats: ['med', 'p(95)', 'p(99)'],
    noConnectionReuse: false,
    thresholds: { fairdrop_unexpected_5xx: ['count==0'] },
  };
  if (name === 'early_bot' || name === 'policy_compare') {
    base.scenarios = {
      bot_wave: arrival('botWave', 0, Math.max(1, Math.round(targetRps * 0.7))),
      human_wave: arrival('humanWave', 2, Math.max(1, Math.round(targetRps * 0.3))),
    };
  } else {
    base.scenarios = { traffic: arrival('default', 0, targetRps) };
  }
  return base;
}

function arrival(execName, startSeconds, targetRequestsPerSecond) {
  const requestsPerIteration = scenarioName === 'retry_flood' ? retryCount + 2 : 3;
  const rate = targetRequestsPerSecond / requestsPerIteration;
  return {
    executor: 'constant-arrival-rate',
    exec: execName,
    rate: Math.max(1, Math.round(rate * 60)),
    timeUnit: '1m',
    duration: `${durationSeconds}s`,
    startTime: `${startSeconds}s`,
    preAllocatedVUs: Math.max(1, Math.ceil(rate / 2)),
    maxVUs: Math.max(10, Math.ceil(rate * 2)),
  };
}

function flattenActors(actors) {
  const flattened = [];
  for (const actor of actors) {
    for (const credential of actor.credentials || []) {
      flattened.push({ actor_id: actor.actor_id, cohort: actor.cohort, access_code: credential.access_code, public_id: credential.public_id });
    }
  }
  return flattened;
}

function select(items) {
  if (!items.length) throw new Error('scenario cohort has no configured credentials');
  return items[exec.scenario.iterationInTest % items.length];
}

function tags(person, endpoint) {
  return { cohort: person.cohort, endpoint, scenario: scenarioName, run_id: runId, public_id: person.public_id };
}

function writeHeaders(csrf, operationKey) {
  return {
    'Content-Type': 'application/json',
    Origin: publicOrigin,
    'X-CSRF-Token': csrf,
    'Idempotency-Key': operationKey,
  };
}

function safeJson(response) {
  try { return response.json(); } catch (_) { return null; }
}

function required(name) {
  if (!__ENV[name]) throw new Error(`${name} is required`);
  return __ENV[name];
}

function intEnv(name, fallback) {
  const value = __ENV[name] === undefined ? fallback : Number.parseInt(__ENV[name], 10);
  if (!Number.isInteger(value)) throw new Error(`${name} must be an integer`);
  return value;
}

function numberEnv(name, fallback) {
  const value = __ENV[name] === undefined ? fallback : Number(__ENV[name]);
  if (!Number.isFinite(value)) throw new Error(`${name} must be finite`);
  return value;
}

function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16);
    const value = char === 'x' ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}
