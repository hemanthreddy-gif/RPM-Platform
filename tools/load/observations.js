import http from 'k6/http';
import exec from 'k6/execution';
import { check, fail } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const baseUrl = __ENV.RPM_API_BASE_URL || 'http://127.0.0.1:8000';
const tokenFile = __ENV.RPM_LOAD_TOKENS_FILE;
const runId = __ENV.RPM_LOAD_RUN_ID || 'phase10';
if (!tokenFile) fail('RPM_LOAD_TOKENS_FILE must name a JSON file with 1,000 synthetic patient tokens');
const tokens = JSON.parse(open(tokenFile));
if (!Array.isArray(tokens) || tokens.length < 1000) fail('Load test requires at least 1,000 synthetic patient tokens');

export const options = {
  scenarios: { readings: { executor: 'shared-iterations', vus: 5, iterations: 1000, maxDuration: '2m' } },
  thresholds: { http_req_failed: ['rate<0.01'] },
  summaryTrendStats: ['min', 'med', 'avg', 'p(50)', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export const alertCreationLatency = new Trend('alert_creation_latency', true);
export const observationErrors = new Counter('observation_errors');

export default function () {
  const measuredAt = new Date(Date.now() - 60_000).toISOString();
  const response = http.post(`${baseUrl}/api/v1/observations`, JSON.stringify({
    type: 'glucose', value: 105, unit: 'mg/dL', measured_at: measuredAt, context: {}, confirm_unusual: false,
  }), {
    headers: {
      Authorization: `Bearer ${tokens[exec.scenario.iterationInTest]}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': `${runId}-${exec.scenario.iterationInTest}`,
    },
  });
  const accepted = check(response, { 'observation accepted': (item) => item.status === 201 });
  if (!accepted) observationErrors.add(1);
  if (response.status === 201) {
    const alertLatency = response.json('alert_creation_latency_ms');
    if (typeof alertLatency === 'number') alertCreationLatency.add(alertLatency);
  }
}
