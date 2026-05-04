import type { DemoResetResponse, IntentExecuteResponse, IntentInterpretResponse } from '../types/api'
import { OperatorDebugPanel } from './OperatorDebugPanel'
import type { LastResponseSource } from './TraceSummaryCards'
import { UserFacingResult } from './UserFacingResult'
import { VoiceTranscriptStrip } from './VoiceTranscriptStrip'

export type InterpretRoomOption = { label: string; room: string }

type Props = {
  input: string
  onInputChange: (v: string) => void
  onSubmit: () => void
  busy: boolean
  lastSentText: string | null
  lastResponseSource: LastResponseSource
  lastInterpret: IntentInterpretResponse | null
  lastExecute: IntentExecuteResponse | null
  interpretFollowUp: {
    utterance: string
    normalizedText: string
    prompt: string
    options: InterpretRoomOption[]
  } | null
  interpretClarificationUnsupported: boolean
  onInterpretRoomChoice: (roomId: string) => void
  executeClarification: IntentExecuteResponse | null
  onExecuteClarify: (reply: string) => void
  onDemoReset: () => void
  onAfterDemoAction: () => Promise<void>
  resetBusy: boolean
  resetError: string | null
  demoResetResult: DemoResetResponse | null
}

export function CommandConsole({
  input,
  onInputChange,
  onSubmit,
  busy,
  lastSentText,
  lastResponseSource,
  lastInterpret,
  lastExecute,
  interpretFollowUp,
  interpretClarificationUnsupported,
  onInterpretRoomChoice,
  executeClarification,
  onExecuteClarify,
  onDemoReset,
  onAfterDemoAction,
  resetBusy,
  resetError,
  demoResetResult,
}: Props) {
  const execClar = executeClarification?.clarification
  const execOptions =
    execClar && Array.isArray(execClar.options)
      ? (execClar.options as Array<{ id: string; label: string; room_id: string }>)
      : []
  const execSessionId =
    execClar && typeof execClar === 'object' && typeof execClar.session_id === 'string' ? execClar.session_id : null
  const pendingIntent =
    execClar && typeof execClar === 'object' && typeof execClar.pending_intent === 'string'
      ? execClar.pending_intent
      : null
  const expiresSec =
    execClar && typeof execClar === 'object' && typeof execClar.expires_in_seconds === 'number'
      ? execClar.expires_in_seconds
      : null

  return (
    <section className="panel span-2" data-testid="command-console" aria-label="Команды и ответ">
      <h2>Команда и ответ бэкенда</h2>
      <p className="muted">
        Текст отправляется в POST /api/intents/interpret, затем при успехе — в POST /api/intents/execute. Уточнение после
        execute — POST /api/intents/clarify.
      </p>
      <form
        className="command-form"
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit()
        }}
      >
        <input
          data-testid="command-input"
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="Например: включи свет на кухне"
          disabled={busy}
          aria-label="Текст команды"
        />
        <button type="submit" data-testid="command-submit" disabled={busy}>
          Отправить
        </button>
      </form>

      <VoiceTranscriptStrip onAfterVoice={onAfterDemoAction} />

      {lastSentText ? (
        <p className="muted" style={{ marginTop: '0.75rem' }} data-testid="last-utterance">
          Последняя фраза: «{lastSentText}»
        </p>
      ) : null}

      <div className="command-lifecycle" data-testid="response-panel">
        <h3 className="command-section-title">Результат для пользователя</h3>
        <UserFacingResult
          busy={busy}
          interpretClarificationUnsupported={interpretClarificationUnsupported}
          lastInterpret={lastInterpret}
          lastExecute={lastExecute}
        />

        {interpretFollowUp ? (
          <div style={{ marginTop: '0.75rem' }} data-testid="interpret-clarification">
            <p className="clarification-path muted" data-testid="interpret-clarification-path">
              Путь: interpret — POST /api/intents/interpret (missing_room)
            </p>
            <p>
              <strong>Уточнение (interpret):</strong> {interpretFollowUp.prompt}
            </p>
            <div className="option-list" data-testid="interpret-clarification-options">
              {interpretFollowUp.options.map((o) => (
                <button
                  key={o.room}
                  type="button"
                  data-testid={`interpret-option-${o.room}`}
                  disabled={busy}
                  onClick={() => onInterpretRoomChoice(o.room)}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {executeClarification?.status === 'clarification_required' && execOptions.length ? (
          <div style={{ marginTop: '0.75rem' }} data-testid="execute-clarification">
            <p className="clarification-path muted" data-testid="execute-clarification-path">
              Путь: execute → уточнение — POST /api/intents/clarify с session_id
            </p>
            {execSessionId ? (
              <p className="clarification-meta">
                <span className="muted">session_id:</span>{' '}
                <code data-testid="execute-clarification-session">{execSessionId}</code>
              </p>
            ) : null}
            {pendingIntent ? (
              <p className="clarification-meta" data-testid="execute-clarification-pending-intent">
                <span className="muted">pending_intent:</span> <code>{pendingIntent}</code>
              </p>
            ) : null}
            {expiresSec != null ? (
              <p className="clarification-meta" data-testid="execute-clarification-expires">
                <span className="muted">expires_in_seconds:</span> {expiresSec}
              </p>
            ) : null}
            <p>
              <strong>Уточнение (execute):</strong> {executeClarification.ui_message}
            </p>
            <div className="option-list" data-testid="execute-clarification-options">
              {execOptions.map((o) => (
                <button
                  key={o.id}
                  type="button"
                  data-testid={`execute-clarify-${o.id.replace(/[^a-zA-Z0-9_-]/g, '_')}`}
                  disabled={busy}
                  onClick={() => onExecuteClarify(o.id)}
                >
                  {o.label} <span className="muted">({o.room_id})</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <OperatorDebugPanel
        interpretClarificationUnsupported={interpretClarificationUnsupported}
        lastSentText={lastSentText}
        lastResponseSource={lastResponseSource}
        lastInterpret={lastInterpret}
        lastExecute={lastExecute}
        onDemoReset={onDemoReset}
        onAfterDemoAction={onAfterDemoAction}
        resetBusy={resetBusy}
        resetError={resetError}
        demoResetResult={demoResetResult}
      />
    </section>
  )
}
