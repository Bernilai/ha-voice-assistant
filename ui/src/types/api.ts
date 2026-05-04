/** Mirrors backend JSON contracts (GET/POST responses). */

export interface DeviceState {
  entity_id: string
  domain: string
  name: string
  state: string
  device_class?: string | null
}

export interface SensorState {
  entity_id: string
  kind: string
  name: string
  state: string
  unit?: string | null
}

export interface RoomState {
  room_id: string
  name: string
  devices: DeviceState[]
  sensors: SensorState[]
}

export interface HouseState {
  version: string
  rooms: RoomState[]
}

export interface EventItem {
  id: string
  timestamp: string
  type: string
  message: string
  metadata: Record<string, unknown>
}

export interface EventsListResponse {
  events: EventItem[]
  order: string
}

export interface IntentInterpretResponse {
  raw_text: string
  normalized_text: string
  canonical_intent: string | null
  entities: Record<string, unknown>
  status: 'success' | 'clarification_required' | 'unsupported'
  clarification: Record<string, unknown> | null
}

export interface IntentExecuteResponse {
  status: 'success' | 'error' | 'clarification_required'
  spoken_response: string
  ui_message: string
  affected_entities: string[]
  queried_entities: string[]
  trace: Record<string, unknown>
  error_code: string | null
  error_message: string | null
  clarification: Record<string, unknown> | null
}

export interface InterpretMissingRoomOption {
  label: string
  room: string
}

export interface ExecuteClarificationOption {
  id: string
  label: string
  room_id: string
}

/** POST /api/demo/reset */
export interface DemoResetResponse {
  ok: boolean
  message: string
  event_log_cleared: boolean
  clarification_sessions_cleared: boolean
  baseline_strategy: 'mock_reset_to_baseline' | 'ha_service_sequence'
  baseline_semantics: string
  reset_at: string
}

export interface DemoCatalogEntry {
  id: string
  title: string
  steps: number
  deterministic: boolean
  notes: string
}

/** GET /api/demo/status */
export interface DemoStatusResponse {
  mode: string
  mode_semantics: string
  last_reset_at: string | null
  last_reset_ok: boolean | null
  last_reset_baseline_strategy: string | null
  last_replay_at: string | null
  last_replay_summary: Record<string, unknown> | null
  replay_catalog: DemoCatalogEntry[]
  reset_contract: string
}

/** POST /api/demo/replay */
export interface DemoReplayStepResult {
  index: number
  intent: string
  status: string
  error_code: string | null
}

export interface DemoReplayResponse {
  ok: boolean
  scenario_id: string
  steps_total: number
  steps_run: number
  stopped_early: boolean
  step_results: DemoReplayStepResult[]
  detail: string
  completed_at: string | null
}

/** POST /api/demo/set-mode */
export interface DemoSetModeResponse {
  ok: boolean
  mode: string
  semantics: string
}

/** GET /api/voice/status (P9 optional) */
export interface VoiceStatusResponse {
  integration_kind: 'ha_assist_plus_transcript_bridge'
  bridge_enabled: boolean
  transcript_endpoint_available: boolean
  ha_assist_local_path: string
  transcript_bridge_path: string
  supported_transcript_phrases_ru: string[]
  intentionally_unsupported_via_transcript: string[]
  clarification_policy_ru: string
}

/** POST /api/voice/transcript (P9 optional) */
export interface VoiceProcessResponse {
  outcome: 'executed' | 'fallback_to_text' | 'bridge_disabled'
  execution_claimed: boolean
  transcript: string
  message_ru: string
  voice_path: 'transcript_bridge'
  interpret: IntentInterpretResponse | null
  policy_reason: string | null
  execute: IntentExecuteResponse | null
}
