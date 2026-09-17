import type { ActionResponse, NavigationStatusResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${init?.method ?? 'GET'} ${path} failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  setDestination: (x: number, y: number) =>
    request<ActionResponse>('/navigation/destination', {
      method: 'POST',
      body: JSON.stringify({ x, y }),
    }),

  start: () => request<ActionResponse>('/navigation/start', { method: 'POST' }),
  pause: () => request<ActionResponse>('/navigation/pause', { method: 'POST' }),
  resume: () => request<ActionResponse>('/navigation/resume', { method: 'POST' }),
  stop: () => request<ActionResponse>('/navigation/stop', { method: 'POST' }),
  emergencyStop: () => request<ActionResponse>('/navigation/emergency-stop', { method: 'POST' }),

  navigationStatus: () => request<NavigationStatusResponse>('/navigation/status'),
};
