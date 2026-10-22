import type {
  ApplyRequest,
  ApplyResponse,
  LmStudioStatus,
  PlanDetail,
  PlanResponse,
  ScanResponse,
  ScanStatus,
  ScannedFile,
} from './types';

const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

// ---------------------------------------------------------------------------
// Generic helpers
// ---------------------------------------------------------------------------

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`PATCH ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// LM Studio
// ---------------------------------------------------------------------------

export const getLmStudioStatus = (): Promise<LmStudioStatus> =>
  get('/api/lm-studio/status');

// ---------------------------------------------------------------------------
// Scan
// ---------------------------------------------------------------------------

export const startScan = (folder: string): Promise<ScanResponse> =>
  post('/api/scan', { folder });

export const getScan = (scanId: string): Promise<ScanStatus> =>
  get(`/api/scans/${scanId}`);

export const getScanFiles = (scanId: string): Promise<ScannedFile[]> =>
  get(`/api/scans/${scanId}/files`);

// ---------------------------------------------------------------------------
// Plan
// ---------------------------------------------------------------------------

export const createPlan = (scanId: string): Promise<PlanResponse> =>
  post(`/api/scans/${scanId}/plan`);

export const getPlan = (planId: string): Promise<PlanDetail> =>
  get(`/api/plans/${planId}`);

export const updateItemApproval = (
  planId: string,
  itemId: string,
  approved: boolean,
) => patch(`/api/plans/${planId}/items/${itemId}`, { approved });

// ---------------------------------------------------------------------------
// Apply
// ---------------------------------------------------------------------------

export const applyPlan = (
  planId: string,
  body: ApplyRequest,
): Promise<ApplyResponse> => post(`/api/plans/${planId}/apply`, body);

// ---------------------------------------------------------------------------
// WebSocket helper
// ---------------------------------------------------------------------------

export function openScanSocket(scanId: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = import.meta.env.VITE_API_BASE_URL
    ? new URL(import.meta.env.VITE_API_BASE_URL as string).host
    : window.location.host;
  return new WebSocket(`${protocol}://${host}/ws/scan/${scanId}`);
}
