import type {
  DemoReplayResponse,
  DemoResetResponse,
  DemoSetModeResponse,
  DemoStatusResponse,
  EventsListResponse,
  HouseState,
  IntentExecuteResponse,
  IntentInterpretResponse,
  VoiceProcessResponse,
  VoiceStatusResponse,
} from '../types/api'

const JSON_HEADERS = { 'Content-Type': 'application/json' }

async function parseJson<T>(r: Response): Promise<T> {
  return r.json() as Promise<T>
}

export type HouseFetchResult =
  | { ok: true; data: HouseState }
  | { ok: false; status: number; message: string }

export async function fetchHouse(): Promise<HouseFetchResult> {
  const r = await fetch('/api/state/house')
  if (r.ok) {
    return { ok: true, data: await parseJson<HouseState>(r) }
  }
  let message = `HTTP ${r.status}`
  try {
    const body = (await r.json()) as { detail?: { message?: string; code?: string } }
    if (body?.detail?.message) {
      message = body.detail.message
    } else if (typeof body?.detail === 'string') {
      message = body.detail
    }
  } catch {
    /* ignore */
  }
  return { ok: false, status: r.status, message }
}

export async function fetchEvents(limit = 50): Promise<EventsListResponse> {
  const r = await fetch(`/api/events?limit=${encodeURIComponent(String(limit))}`)
  if (!r.ok) {
    throw new Error(`events: HTTP ${r.status}`)
  }
  return parseJson<EventsListResponse>(r)
}

export async function postInterpret(text: string): Promise<IntentInterpretResponse> {
  const r = await fetch('/api/intents/interpret', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ text }),
  })
  if (!r.ok) {
    throw new Error(`interpret: HTTP ${r.status}`)
  }
  return parseJson<IntentInterpretResponse>(r)
}

export async function postExecute(body: Record<string, unknown>): Promise<IntentExecuteResponse> {
  const r = await fetch('/api/intents/execute', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  })
  if (!r.ok) {
    throw new Error(`execute: HTTP ${r.status}`)
  }
  return parseJson<IntentExecuteResponse>(r)
}

export async function postClarify(sessionId: string, reply: string): Promise<IntentExecuteResponse> {
  const r = await fetch('/api/intents/clarify', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ session_id: sessionId, reply }),
  })
  if (!r.ok) {
    throw new Error(`clarify: HTTP ${r.status}`)
  }
  return parseJson<IntentExecuteResponse>(r)
}

export async function fetchHealth(): Promise<unknown> {
  const r = await fetch('/api/health')
  if (!r.ok) {
    throw new Error(`health: HTTP ${r.status}`)
  }
  return parseJson(r)
}

export async function postDemoReset(): Promise<DemoResetResponse> {
  const r = await fetch('/api/demo/reset', { method: 'POST' })
  const data = await parseJson<DemoResetResponse>(r)
  if (!r.ok) {
    throw new Error(`demo reset: HTTP ${r.status}`)
  }
  return data
}

export async function fetchDemoStatus(): Promise<DemoStatusResponse> {
  const r = await fetch('/api/demo/status')
  if (!r.ok) {
    throw new Error(`demo status: HTTP ${r.status}`)
  }
  return parseJson<DemoStatusResponse>(r)
}

export async function postDemoReplay(scenarioId?: string): Promise<DemoReplayResponse> {
  const r = await fetch('/api/demo/replay', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(scenarioId ? { scenario_id: scenarioId } : {}),
  })
  const data = await parseJson<DemoReplayResponse>(r)
  if (!r.ok) {
    throw new Error(`demo replay: HTTP ${r.status}`)
  }
  return data
}

export async function postDemoSetMode(mode: 'static' | 'live' | 'simulator'): Promise<DemoSetModeResponse> {
  const r = await fetch('/api/demo/set-mode', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ mode }),
  })
  const data = await parseJson<DemoSetModeResponse>(r)
  if (!r.ok) {
    throw new Error(`demo set-mode: HTTP ${r.status}`)
  }
  return data
}

export async function fetchVoiceStatus(): Promise<VoiceStatusResponse> {
  const r = await fetch('/api/voice/status')
  if (!r.ok) {
    throw new Error(`voice status: HTTP ${r.status}`)
  }
  return parseJson<VoiceStatusResponse>(r)
}

export async function postVoiceTranscript(transcript: string): Promise<VoiceProcessResponse> {
  const r = await fetch('/api/voice/transcript', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ transcript }),
  })
  if (!r.ok) {
    throw new Error(`voice transcript: HTTP ${r.status}`)
  }
  return parseJson<VoiceProcessResponse>(r)
}
