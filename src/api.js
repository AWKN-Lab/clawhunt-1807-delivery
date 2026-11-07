// src/api.js：只走相对路径 /api/v1（dev 由 Vite proxy 转发到 127.0.0.1:8001）
const BASE = (import.meta.env.VITE_API_BASE || '') + '/api/v1';

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(path, { method = 'GET', body, token, headers = {} } = {}) {
  const options = { method, headers: { ...headers } };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  if (token) options.headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new ApiError(
      response.status,
      payload?.code || 'http_error',
      payload?.message || `请求失败（HTTP ${response.status}）`,
    );
  }
  if (response.status === 204) return null;
  return response.json();
}

export function createConsent(payload) {
  return request('/consents', { method: 'POST', body: payload });
}

export function createSession(candidateId, sourceChannel) {
  return request('/agent/sessions', {
    method: 'POST',
    body: { candidate_id: candidateId, source_channel: sourceChannel },
  });
}

export function getSession(sessionId, token) {
  return request(`/agent/sessions/${sessionId}`, { token });
}

export function sendMessage(sessionId, token, text) {
  return request(`/agent/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: { text },
    token,
  });
}

export function requestHandoff(sessionId, token, reason = 'user_requested') {
  return request('/handoff', { method: 'POST', body: { session_id: sessionId, reason }, token });
}

export function createBooking(stationId, slotStart, token) {
  return request('/bookings', {
    method: 'POST',
    body: { station_id: stationId, slot_start: slotStart },
    token,
  });
}

export function rescheduleBooking(bookingId, slotStart, token) {
  return request(`/bookings/${bookingId}/reschedule`, {
    method: 'POST',
    body: { slot_start: slotStart },
    token,
  });
}

export function cancelBooking(bookingId, token) {
  return request(`/bookings/${bookingId}/cancel`, { method: 'POST', token });
}

export function getCandidate(candidateId, token) {
  return request(`/candidates/${candidateId}`, { token });
}

export function patchCandidate(candidateId, payload, token) {
  return request(`/candidates/${candidateId}`, { method: 'PATCH', body: payload, token });
}

export async function downloadCandidateCopy(candidateId, token) {
  const response = await fetch(`${BASE}/candidates/${candidateId}/export`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new ApiError(response.status, payload?.code || 'http_error', payload?.message || '下载失败');
  }
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^";]+)"?/);
  return { blob: await response.blob(), filename: match ? match[1] : 'candidate-copy.json' };
}

export function revokeCandidate(candidateId, token) {
  return request(`/candidates/${candidateId}`, { method: 'DELETE', token });
}
