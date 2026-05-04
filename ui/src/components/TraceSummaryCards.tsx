import type { IntentExecuteResponse, IntentInterpretResponse } from '../types/api'

export type LastResponseSource = 'interpret' | 'execute' | 'clarify' | null

type Props = {
  interpretClarificationUnsupported: boolean
  lastSentText: string | null
  lastResponseSource: LastResponseSource
  lastInterpret: IntentInterpretResponse | null
  lastExecute: IntentExecuteResponse | null
}

function str(v: unknown): string | null {
  if (typeof v === 'string' && v.length) {
    return v
  }
  return null
}

export function TraceSummaryCards({
  interpretClarificationUnsupported,
  lastSentText,
  lastResponseSource,
  lastInterpret,
  lastExecute,
}: Props) {
  const exTrace = lastExecute?.trace ?? {}
  const engine = str(exTrace.execution_engine) ?? str(exTrace.status_engine)
  const phase = str(exTrace.phase)
  const clarSessionTrace = str(exTrace.clarification_session_id)
  const execStatus = lastExecute?.status ?? null
  const interpStatus = lastInterpret?.status ?? null

  const pendingClarifyExecute =
    lastExecute?.status === 'clarification_required' &&
    lastExecute.clarification &&
    typeof lastExecute.clarification === 'object'

  return (
    <div className="trace-summary-grid" data-testid="trace-summary-cards">
      <div className="trace-card">
        <div className="trace-card-label">Последняя фраза</div>
        <div className="trace-card-value" data-testid="trace-last-phrase">
          {lastSentText ? `«${lastSentText}»` : '—'}
        </div>
      </div>
      <div className="trace-card">
        <div className="trace-card-label">Источник ответа</div>
        <div className="trace-card-value" data-testid="trace-response-source">
          {lastResponseSource ?? '—'}
        </div>
      </div>
      <div className="trace-card">
        <div className="trace-card-label">Interpret status</div>
        <div className="trace-card-value" data-testid="trace-interpret-status">
          {lastInterpret ? interpStatus : '—'}
        </div>
      </div>
      <div className="trace-card">
        <div className="trace-card-label">Execute status</div>
        <div className="trace-card-value" data-testid="trace-execute-status">
          {lastExecute ? execStatus : '—'}
        </div>
      </div>
      <div className="trace-card">
        <div className="trace-card-label">Engine (trace)</div>
        <div className="trace-card-value" data-testid="trace-engine">
          {engine ?? '—'}
        </div>
      </div>
      <div className="trace-card">
        <div className="trace-card-label">Phase (trace)</div>
        <div className="trace-card-value" data-testid="trace-phase">
          {phase ?? '—'}
        </div>
      </div>
      <div className="trace-card">
        <div className="trace-card-label">Ошибка</div>
        <div className="trace-card-value" data-testid="trace-error-code">
          {lastExecute?.status === 'error' && lastExecute.error_code ? lastExecute.error_code : '—'}
        </div>
      </div>
      <div className="trace-card">
        <div className="trace-card-label">Clarification pending</div>
        <div className="trace-card-value" data-testid="trace-clarification-pending">
          {interpretClarificationUnsupported
            ? 'interpret (не поддержано в UI)'
            : pendingClarifyExecute
              ? 'execute'
              : lastInterpret?.status === 'clarification_required'
                ? 'interpret'
                : '—'}
        </div>
      </div>
      {clarSessionTrace ? (
        <div className="trace-card span-trace-wide">
          <div className="trace-card-label">clarification_session_id (trace)</div>
          <div className="trace-card-value mono" data-testid="trace-clarification-session-id">
            {clarSessionTrace}
          </div>
        </div>
      ) : null}
    </div>
  )
}
