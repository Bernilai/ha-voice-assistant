import { useCallback, useEffect, useRef, useState } from 'react'

import {
  fetchEvents,
  fetchHealth,
  fetchHouse,
  postClarify,
  postDemoReset,
  postExecute,
  postInterpret,
} from './api/client'
import { CommandConsole } from './components/CommandConsole'
import type { LastResponseSource } from './components/TraceSummaryCards'
import { EventLogPanel } from './components/EventLogPanel'
import { HouseOverview } from './components/HouseOverview'
import type {
  DemoResetResponse,
  EventItem,
  HouseState,
  IntentExecuteResponse,
  IntentInterpretResponse,
} from './types/api'
import { inferLightToggleIntent } from './util/interpretFollowUp'

const POLL_MS = 4000
const EVENT_LIMIT = 50

/** Only `reason: missing_room` with room options is bridged to execute; other interpret clarifications show an explicit UI fallback. */
function parseInterpretMissingRoom(
  clar: Record<string, unknown> | null,
): { prompt: string; options: { label: string; room: string }[] } | null {
  if (!clar || clar.reason !== 'missing_room' || !Array.isArray(clar.options)) {
    return null
  }
  const prompt = typeof clar.prompt === 'string' ? clar.prompt : 'Уточните комнату.'
  const options: { label: string; room: string }[] = []
  for (const row of clar.options) {
    if (row && typeof row === 'object' && 'label' in row && 'room' in row) {
      const label = String((row as { label: unknown }).label)
      const room = String((row as { room: unknown }).room)
      options.push({ label, room })
    }
  }
  return options.length ? { prompt, options } : null
}

export function App() {
  const [house, setHouse] = useState<HouseState | null>(null)
  const [houseError, setHouseError] = useState<string | null>(null)
  const [houseLoading, setHouseLoading] = useState(true)

  const [events, setEvents] = useState<EventItem[]>([])
  const [eventsError, setEventsError] = useState<string | null>(null)

  const [healthOk, setHealthOk] = useState<boolean | null>(null)

  const [commandInput, setCommandInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [lastSentText, setLastSentText] = useState<string | null>(null)
  const [lastInterpret, setLastInterpret] = useState<IntentInterpretResponse | null>(null)
  const [lastExecute, setLastExecute] = useState<IntentExecuteResponse | null>(null)
  const [interpretFollowUp, setInterpretFollowUp] = useState<{
    utterance: string
    normalizedText: string
    prompt: string
    options: { label: string; room: string }[]
  } | null>(null)
  const [interpretClarificationUnsupported, setInterpretClarificationUnsupported] = useState(false)

  const [lastResponseSource, setLastResponseSource] = useState<LastResponseSource>(null)
  const [resetBusy, setResetBusy] = useState(false)
  const [resetError, setResetError] = useState<string | null>(null)
  const [demoResetResult, setDemoResetResult] = useState<DemoResetResponse | null>(null)

  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const refreshHouseAndEvents = useCallback(async () => {
    try {
      const hr = await fetchHouse()
      if (!mounted.current) {
        return
      }
      if (hr.ok) {
        setHouse(hr.data)
        setHouseError(null)
      } else {
        setHouse(null)
        setHouseError(hr.message)
      }
    } catch (e) {
      if (!mounted.current) {
        return
      }
      setHouse(null)
      setHouseError(e instanceof Error ? e.message : 'house fetch failed')
    }

    try {
      const ev = await fetchEvents(EVENT_LIMIT)
      if (!mounted.current) {
        return
      }
      setEvents(ev.events)
      setEventsError(null)
    } catch (e) {
      if (!mounted.current) {
        return
      }
      setEventsError(e instanceof Error ? e.message : 'events fetch failed')
    } finally {
      if (mounted.current) {
        setHouseLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    void fetchHealth()
      .then(() => {
        if (mounted.current) {
          setHealthOk(true)
        }
      })
      .catch(() => {
        if (mounted.current) {
          setHealthOk(false)
        }
      })
    void refreshHouseAndEvents()
  }, [refreshHouseAndEvents])

  useEffect(() => {
    const id = window.setInterval(() => {
      void refreshHouseAndEvents()
    }, POLL_MS)
    return () => window.clearInterval(id)
  }, [refreshHouseAndEvents])

  const runExecuteFromInterpret = useCallback(
    async (utterance: string, interp: IntentInterpretResponse) => {
      if (!interp.canonical_intent) {
        return
      }
      const body = {
        intent: interp.canonical_intent,
        source: 'text',
        utterance,
        entities: interp.entities,
        confidence: 1.0,
        requires_clarification: false,
        meta: { language: 'ru' },
      }
      const ex = await postExecute(body)
      if (!mounted.current) {
        return
      }
      setLastResponseSource('execute')
      setLastExecute(ex)
      setInterpretFollowUp(null)
      await refreshHouseAndEvents()
    },
    [refreshHouseAndEvents],
  )

  const onSubmitCommand = useCallback(async () => {
    const text = commandInput.trim()
    if (!text || busy) {
      return
    }
    setBusy(true)
    setLastSentText(text)
    setCommandInput('')
    setLastInterpret(null)
    setLastExecute(null)
    setInterpretFollowUp(null)
    setInterpretClarificationUnsupported(false)
    setLastResponseSource(null)
    setDemoResetResult(null)

    let reachedExecute = false
    try {
      const interp = await postInterpret(text)
      if (!mounted.current) {
        return
      }
      setLastInterpret(interp)
      setLastResponseSource('interpret')

      if (interp.status === 'unsupported') {
        return
      }

      if (interp.status === 'clarification_required') {
        const missing = parseInterpretMissingRoom(interp.clarification)
        if (missing) {
          setInterpretFollowUp({
            utterance: interp.raw_text,
            normalizedText: interp.normalized_text,
            prompt: missing.prompt,
            options: missing.options,
          })
        } else {
          setInterpretClarificationUnsupported(true)
        }
        return
      }

      if (interp.status === 'success' && interp.canonical_intent) {
        reachedExecute = true
        await runExecuteFromInterpret(interp.raw_text, interp)
      }
    } catch (e) {
      if (!mounted.current) {
        return
      }
      setLastResponseSource(reachedExecute ? 'execute' : 'interpret')
      setLastExecute({
        status: 'error',
        spoken_response: 'Ошибка сети или сервера.',
        ui_message: e instanceof Error ? e.message : 'Request failed',
        affected_entities: [],
        queried_entities: [],
        trace: {},
        error_code: 'client',
        error_message: e instanceof Error ? e.message : String(e),
        clarification: null,
      })
    } finally {
      if (mounted.current) {
        setBusy(false)
      }
    }
  }, [busy, commandInput, runExecuteFromInterpret])

  const onInterpretRoomChoice = useCallback(
    async (roomId: string) => {
      if (!interpretFollowUp || busy) {
        return
      }
      const intent = inferLightToggleIntent(interpretFollowUp.normalizedText)
      if (!intent) {
        setLastResponseSource('interpret')
        setLastExecute({
          status: 'error',
          spoken_response: 'Не удалось определить действие.',
          ui_message: 'Для этого уточнения нужна фраза с «включи» или «выключи».',
          affected_entities: [],
          queried_entities: [],
          trace: {},
          error_code: 'client',
          error_message: 'intent_inference_failed',
          clarification: null,
        })
        setInterpretFollowUp(null)
        return
      }

      setBusy(true)
      try {
        const ex = await postExecute({
          intent,
          source: 'text',
          utterance: interpretFollowUp.utterance,
          entities: { room: roomId, device_type: 'light' },
          confidence: 1.0,
          requires_clarification: false,
          meta: { language: 'ru', follow_up: 'interpret_missing_room' },
        })
        if (!mounted.current) {
          return
        }
        setLastResponseSource('execute')
        setLastExecute(ex)
        setInterpretFollowUp(null)
        await refreshHouseAndEvents()
      } catch (e) {
        if (!mounted.current) {
          return
        }
        setLastResponseSource('execute')
        setLastExecute({
          status: 'error',
          spoken_response: 'Ошибка сети или сервера.',
          ui_message: e instanceof Error ? e.message : 'Request failed',
          affected_entities: [],
          queried_entities: [],
          trace: {},
          error_code: 'client',
          error_message: e instanceof Error ? e.message : String(e),
          clarification: null,
        })
      } finally {
        if (mounted.current) {
          setBusy(false)
        }
      }
    },
    [busy, interpretFollowUp, refreshHouseAndEvents],
  )

  const executeClarification =
    lastExecute?.status === 'clarification_required' ? lastExecute : null

  const onExecuteClarify = useCallback(
    async (reply: string) => {
      const clar = lastExecute?.clarification
      const sessionId =
        clar && typeof clar === 'object' && typeof clar.session_id === 'string' ? clar.session_id : null
      if (!sessionId || busy) {
        return
      }
      setBusy(true)
      try {
        const ex = await postClarify(sessionId, reply)
        if (!mounted.current) {
          return
        }
        setLastResponseSource('clarify')
        setLastExecute(ex)
        await refreshHouseAndEvents()
      } catch (e) {
        if (!mounted.current) {
          return
        }
        setLastResponseSource('clarify')
        setLastExecute({
          status: 'error',
          spoken_response: 'Ошибка сети или сервера.',
          ui_message: e instanceof Error ? e.message : 'Request failed',
          affected_entities: [],
          queried_entities: [],
          trace: {},
          error_code: 'client',
          error_message: e instanceof Error ? e.message : String(e),
          clarification: null,
        })
      } finally {
        if (mounted.current) {
          setBusy(false)
        }
      }
    },
    [busy, lastExecute, refreshHouseAndEvents],
  )

  const onDemoReset = useCallback(() => {
    setResetBusy(true)
    setResetError(null)
    setDemoResetResult(null)
    void (async () => {
      try {
        const data = await postDemoReset()
        if (!mounted.current) {
          return
        }
        setDemoResetResult(data)
        if (!data.ok) {
          setResetError(data.message)
        }
        await refreshHouseAndEvents()
      } catch (e) {
        if (!mounted.current) {
          return
        }
        setResetError(e instanceof Error ? e.message : String(e))
      } finally {
        if (mounted.current) {
          setResetBusy(false)
        }
      }
    })()
  }, [refreshHouseAndEvents])

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Умный дом — демо-панель (MVP)</h1>
        <p className="muted" data-testid="health-strip">
          API: {healthOk === null ? '…' : healthOk ? 'доступен' : 'недоступен'}
        </p>
      </header>

      <div className="app-grid">
        <HouseOverview house={house} error={houseError} loading={houseLoading} />
        <EventLogPanel events={events} error={eventsError} />
        <CommandConsole
          input={commandInput}
          onInputChange={setCommandInput}
          onSubmit={() => void onSubmitCommand()}
          busy={busy}
          lastSentText={lastSentText}
          lastResponseSource={lastResponseSource}
          lastInterpret={lastInterpret}
          lastExecute={lastExecute}
          interpretFollowUp={interpretFollowUp}
          interpretClarificationUnsupported={interpretClarificationUnsupported}
          onInterpretRoomChoice={(room) => void onInterpretRoomChoice(room)}
          executeClarification={executeClarification}
          onExecuteClarify={(reply) => void onExecuteClarify(reply)}
          onDemoReset={onDemoReset}
          onAfterDemoAction={refreshHouseAndEvents}
          resetBusy={resetBusy}
          resetError={resetError}
          demoResetResult={demoResetResult}
        />
      </div>
    </div>
  )
}
