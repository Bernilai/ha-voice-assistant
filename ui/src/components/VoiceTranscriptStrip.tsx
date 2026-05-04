import { useCallback, useEffect, useState } from 'react'

import { fetchVoiceStatus, postVoiceTranscript } from '../api/client'
import type { VoiceProcessResponse, VoiceStatusResponse } from '../types/api'

type Props = {
  /** Refresh house/events after a voice transcript round-trip (same as demo actions). */
  onAfterVoice: () => Promise<void>
}

export function VoiceTranscriptStrip({ onAfterVoice }: Props) {
  const [status, setStatus] = useState<VoiceStatusResponse | null>(null)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [last, setLast] = useState<VoiceProcessResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const s = await fetchVoiceStatus()
        if (!cancelled) {
          setStatus(s)
          setStatusError(null)
        }
      } catch (e) {
        if (!cancelled) {
          setStatus(null)
          setStatusError(e instanceof Error ? e.message : 'voice status failed')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const onSubmit = useCallback(async () => {
    const t = input.trim()
    if (!t || busy) {
      return
    }
    setBusy(true)
    setLast(null)
    try {
      const res = await postVoiceTranscript(t)
      setLast(res)
      setInput('')
      await onAfterVoice()
    } catch (e) {
      setLast({
        outcome: 'fallback_to_text',
        execution_claimed: false,
        transcript: t,
        message_ru: e instanceof Error ? e.message : 'Ошибка запроса',
        voice_path: 'transcript_bridge',
        interpret: null,
        policy_reason: 'client_error',
        execute: null,
      })
    } finally {
      setBusy(false)
    }
  }, [busy, input, onAfterVoice])

  return (
    <div
      className="voice-transcript-strip"
      data-testid="voice-transcript-strip"
      style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border, #2a2a2a)' }}
    >
      <h3 className="command-section-title">Голос (опционально, P9)</h3>
      <p className="muted" style={{ marginBottom: '0.5rem' }}>
        Транскрипт-мост: тот же interpret → execute, что и текст, но с узким allowlist. Реальный Assist в HA — отдельный
        локальный путь (custom_sentences → intent_script); см. GET /api/voice/status.
      </p>
      {statusError ? (
        <p className="muted" data-testid="voice-status-error">
          Статус голоса: {statusError}
        </p>
      ) : status ? (
        <p className="muted" data-testid="voice-status-line">
          Мост: {status.bridge_enabled ? 'включён' : 'выключен'} · transcript endpoint:{' '}
          {status.transcript_endpoint_available ? 'доступен' : 'недоступен'}
        </p>
      ) : (
        <p className="muted" data-testid="voice-status-loading">
          Загрузка статуса…
        </p>
      )}

      <div className="command-form" style={{ marginTop: '0.5rem' }}>
        <input
          data-testid="voice-transcript-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Транскрипт (например: включи свет на кухне)"
          disabled={busy || status?.transcript_endpoint_available === false}
          aria-label="Транскрипт голоса"
        />
        <button
          type="button"
          data-testid="voice-transcript-submit"
          disabled={busy || status?.transcript_endpoint_available === false}
          onClick={() => void onSubmit()}
        >
          Обработать транскрипт
        </button>
      </div>

      {last ? (
        <div style={{ marginTop: '0.75rem' }} data-testid="voice-process-result">
          <p className="muted" data-testid="voice-process-outcome">
            Итог: <strong>{last.outcome}</strong>
            {last.execution_claimed ? ' · выполнение бэкенда' : ' · выполнение не заявлено'}
            {last.policy_reason ? (
              <>
                {' '}
                · <code>{last.policy_reason}</code>
              </>
            ) : null}
          </p>
          <p data-testid="voice-process-message">{last.message_ru}</p>
          <p className="muted" data-testid="voice-process-transcript-echo">
            Транскрипт: «{last.transcript}»
          </p>
        </div>
      ) : null}
    </div>
  )
}
