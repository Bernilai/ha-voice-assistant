import { useCallback, useEffect, useState } from 'react'

import { fetchDemoStatus, postDemoReplay, postDemoSetMode } from '../api/client'
import type {
  DemoReplayResponse,
  DemoResetResponse,
  DemoStatusResponse,
  IntentExecuteResponse,
  IntentInterpretResponse,
} from '../types/api'

import type { LastResponseSource } from './TraceSummaryCards'
import { TraceSummaryCards } from './TraceSummaryCards'

type Props = {
  interpretClarificationUnsupported: boolean
  lastSentText: string | null
  lastResponseSource: LastResponseSource
  lastInterpret: IntentInterpretResponse | null
  lastExecute: IntentExecuteResponse | null
  onDemoReset: () => void
  onAfterDemoAction: () => Promise<void>
  resetBusy: boolean
  resetError: string | null
  demoResetResult: DemoResetResponse | null
}

export function OperatorDebugPanel({
  interpretClarificationUnsupported,
  lastSentText,
  lastResponseSource,
  lastInterpret,
  lastExecute,
  onDemoReset,
  onAfterDemoAction,
  resetBusy,
  resetError,
  demoResetResult,
}: Props) {
  const [open, setOpen] = useState(false)
  const [demoStatus, setDemoStatus] = useState<DemoStatusResponse | null>(null)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [replayBusy, setReplayBusy] = useState(false)
  const [setModeBusy, setSetModeBusy] = useState(false)
  const [replayLast, setReplayLast] = useState<DemoReplayResponse | null>(null)
  const [replayError, setReplayError] = useState<string | null>(null)
  const [setModeNote, setSetModeNote] = useState<string | null>(null)

  const loadStatus = useCallback(async () => {
    setStatusError(null)
    try {
      const s = await fetchDemoStatus()
      setDemoStatus(s)
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  useEffect(() => {
    if (open) {
      void loadStatus()
    }
  }, [open, loadStatus])

  const runReplay = async (scenarioId: string) => {
    setReplayBusy(true)
    setReplayError(null)
    setReplayLast(null)
    try {
      const r = await postDemoReplay(scenarioId)
      setReplayLast(r)
      if (!r.ok) {
        setReplayError(r.detail)
      }
      await onAfterDemoAction()
      await loadStatus()
    } catch (e) {
      setReplayError(e instanceof Error ? e.message : String(e))
    } finally {
      setReplayBusy(false)
    }
  }

  const runSetMode = async (mode: 'static' | 'live' | 'simulator') => {
    setSetModeBusy(true)
    setSetModeNote(null)
    try {
      const r = await postDemoSetMode(mode)
      setSetModeNote(r.semantics)
      await onAfterDemoAction()
      await loadStatus()
    } catch (e) {
      setSetModeNote(e instanceof Error ? e.message : String(e))
    } finally {
      setSetModeBusy(false)
    }
  }

  return (
    <div className="operator-debug-shell" data-testid="operator-debug-shell">
      <button
        type="button"
        className="operator-debug-toggle"
        data-testid="operator-debug-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        Оператор / отладка {open ? '▼' : '▶'}
      </button>

      {open ? (
        <div className="operator-debug-body" data-testid="operator-debug-panel">
          <h3 className="operator-section-title">Демо-контроль</h3>
          <p className="muted demo-reset-contract" data-testid="demo-reset-contract">
            {demoStatus?.reset_contract ?? 'Загрузка контракта reset…'}
          </p>

          <div className="operator-controls" data-testid="operator-controls">
            <button
              type="button"
              className="operator-reset-btn"
              data-testid="demo-reset-button"
              disabled={resetBusy}
              onClick={onDemoReset}
            >
              {resetBusy ? 'Сброс…' : 'Сброс демо (POST /api/demo/reset)'}
            </button>
            {resetError ? (
              <span className="error-text operator-reset-msg" data-testid="demo-reset-error">
                {resetError}
              </span>
            ) : null}
            {demoResetResult && demoResetResult.ok && !resetError ? (
              <span className="operator-reset-msg muted" data-testid="demo-reset-ok">
                Сброс выполнен ({demoResetResult.baseline_strategy})
              </span>
            ) : null}
          </div>
          {demoResetResult ? (
            <p className="muted demo-reset-semantics" data-testid="demo-reset-semantics">
              {demoResetResult.baseline_semantics}
            </p>
          ) : null}

          <div className="demo-status-block" data-testid="demo-status-block">
            <div className="demo-status-row">
              <span className="muted">Режим (GET /api/demo/status):</span>{' '}
              <strong data-testid="demo-status-mode">{demoStatus?.mode ?? '…'}</strong>
            </div>
            {demoStatus?.last_reset_at ? (
              <p className="muted demo-status-row" data-testid="demo-last-reset-at">
                last_reset_at: {demoStatus.last_reset_at} ({demoStatus.last_reset_ok ? 'ok' : 'fail'})
              </p>
            ) : (
              <p className="muted demo-status-row" data-testid="demo-last-reset-at">
                last_reset_at: —
              </p>
            )}
            {statusError ? (
              <p className="error-text" data-testid="demo-status-error">
                {statusError}
              </p>
            ) : null}
            <p className="muted demo-mode-semantics" data-testid="demo-mode-semantics" style={{ fontSize: '0.75rem' }}>
              {demoStatus?.mode_semantics ?? ''}
            </p>
          </div>

          <div className="demo-set-mode-row" data-testid="demo-set-mode-row">
            <span className="muted">Режим демо:</span>{' '}
            <button
              type="button"
              className="demo-mode-btn"
              data-testid="demo-set-mode-static"
              disabled={setModeBusy}
              onClick={() => void runSetMode('static')}
            >
              static
            </button>
            <button
              type="button"
              className="demo-mode-btn"
              data-testid="demo-set-mode-live"
              disabled={setModeBusy}
              onClick={() => void runSetMode('live')}
            >
              live
            </button>
            <button
              type="button"
              className="demo-mode-btn"
              data-testid="demo-set-mode-simulator"
              disabled={setModeBusy}
              onClick={() => void runSetMode('simulator')}
            >
              simulator
            </button>
          </div>
          {setModeNote ? (
            <p className="muted" data-testid="demo-set-mode-note" style={{ fontSize: '0.75rem' }}>
              {setModeNote}
            </p>
          ) : null}

          <div className="demo-replay-block" data-testid="demo-replay-block">
            <span className="muted">Replay (POST /api/demo/replay):</span>
            <div className="demo-replay-buttons">
              {(demoStatus?.replay_catalog ?? []).map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className="demo-replay-btn"
                  data-testid={`demo-replay-${c.id}`}
                  disabled={replayBusy}
                  onClick={() => void runReplay(c.id)}
                  title={c.notes}
                >
                  {c.id}
                </button>
              ))}
            </div>
            {replayError ? (
              <p className="error-text" data-testid="demo-replay-error">
                {replayError}
              </p>
            ) : null}
            {replayLast ? (
              <p className="muted" data-testid="demo-replay-last" style={{ fontSize: '0.75rem' }}>
                {replayLast.scenario_id}: {replayLast.detail} (ok={String(replayLast.ok)})
              </p>
            ) : null}
          </div>

          <h3 className="operator-section-title">Сводка trace</h3>
          <TraceSummaryCards
            interpretClarificationUnsupported={interpretClarificationUnsupported}
            lastSentText={lastSentText}
            lastResponseSource={lastResponseSource}
            lastInterpret={lastInterpret}
            lastExecute={lastExecute}
          />

          <details className="raw-json-details">
            <summary data-testid="raw-json-summary">Сырой JSON (interpret + execute)</summary>
            <div className="raw-json-grid">
              <div>
                <strong>interpret</strong>
                {lastInterpret ? (
                  <pre data-testid="interpret-trace">{JSON.stringify(lastInterpret, null, 2)}</pre>
                ) : (
                  <p className="muted">—</p>
                )}
              </div>
              <div>
                <strong>execute / clarify</strong>
                {lastExecute ? (
                  <pre data-testid="execute-trace">{JSON.stringify(lastExecute, null, 2)}</pre>
                ) : (
                  <p className="muted">—</p>
                )}
              </div>
            </div>
          </details>
        </div>
      ) : null}
    </div>
  )
}
