import type { IntentExecuteResponse, IntentInterpretResponse } from '../types/api'

type Props = {
  busy: boolean
  interpretClarificationUnsupported: boolean
  lastInterpret: IntentInterpretResponse | null
  lastExecute: IntentExecuteResponse | null
}

export function UserFacingResult({ busy, interpretClarificationUnsupported, lastInterpret, lastExecute }: Props) {
  if (interpretClarificationUnsupported) {
    return (
      <div
        className="user-result-panel user-result-unsupported-clarify"
        data-testid="user-result-panel"
        role="alert"
      >
        <p className="error-text" data-testid="interpret-clarification-unsupported">
          Это уточнение пока не поддержано в текущем UI. Откройте панель оператора для полного JSON ответа interpret.
        </p>
      </div>
    )
  }

  const hasActivity = lastInterpret !== null || lastExecute !== null
  if (!hasActivity) {
    return (
      <div className="user-result-panel muted" data-testid="user-result-panel">
        Отправьте команду — здесь появится краткий результат.
      </div>
    )
  }

  if (lastInterpret?.status === 'unsupported') {
    return (
      <div className="user-result-panel user-result-unsupported" data-testid="user-result-panel" role="status">
        <div className="user-result-title" data-testid="user-result-unsupported">
          Интерпретатор не сопоставил фразу (unsupported)
        </div>
        <p className="user-result-body muted">Попробуйте другую формулировку или шаблон из демо-сценария.</p>
      </div>
    )
  }

  if (lastExecute?.status === 'error') {
    const isClient = lastExecute.error_code === 'client'
    return (
      <div
        className={`user-result-panel user-result-error ${isClient ? 'user-result-client-error' : ''}`}
        data-testid="user-result-panel"
        role="alert"
      >
        <div data-testid="execute-summary">
          <div className="user-result-title" data-testid="user-result-error-title">
            {isClient ? 'Сеть или сервер недоступны' : 'Ошибка выполнения'}
          </div>
          <p className="user-result-body">
            <strong>Статус:</strong>{' '}
            <span data-testid="execute-status">{lastExecute.status}</span>
            {' · '}
            <span data-testid="execute-spoken">{lastExecute.spoken_response}</span>
            {' · '}
            <span data-testid="execute-ui-message">{lastExecute.ui_message}</span>
            {lastExecute.error_code ? (
              <span className="error-text" data-testid="execute-error">
                {' '}
                ({lastExecute.error_code})
              </span>
            ) : null}
          </p>
          {lastExecute.error_code ? (
            <p className="error-text user-result-code" data-testid="user-result-error-detail">
              <span data-testid="user-result-error-code">{lastExecute.error_code}</span>
              {lastExecute.error_message ? (
                <>
                  {' '}
                  — <span data-testid="user-result-error-message">{lastExecute.error_message}</span>
                </>
              ) : null}
            </p>
          ) : null}
        </div>
      </div>
    )
  }

  if (lastExecute?.status === 'clarification_required') {
    return (
      <div className="user-result-panel user-result-clarify" data-testid="user-result-panel" role="status">
        <div data-testid="execute-summary">
          <div className="user-result-title" data-testid="user-result-clarify-title">
            Нужно уточнение (execute)
          </div>
          <p className="user-result-body">
            <strong>Статус:</strong> <span data-testid="execute-status">{lastExecute.status}</span>
            {' · '}
            <span data-testid="execute-spoken">{lastExecute.spoken_response}</span>
            {' · '}
            <span data-testid="execute-ui-message">{lastExecute.ui_message}</span>
          </p>
        </div>
      </div>
    )
  }

  if (lastExecute?.status === 'success') {
    return (
      <div className="user-result-panel user-result-success" data-testid="user-result-panel" role="status">
        <div data-testid="execute-summary">
          <div className="user-result-title" data-testid="user-result-success-title">
            Готово
          </div>
          <p className="user-result-body">
            <strong>Статус:</strong> <span data-testid="execute-status">{lastExecute.status}</span>
            {' · '}
            <span data-testid="execute-spoken">{lastExecute.spoken_response}</span>
            {' · '}
            <span data-testid="execute-ui-message">{lastExecute.ui_message}</span>
          </p>
        </div>
      </div>
    )
  }

  if (lastInterpret?.status === 'clarification_required' && !lastExecute) {
    return (
      <div className="user-result-panel user-result-clarify" data-testid="user-result-panel" role="status">
        <div className="user-result-title" data-testid="user-result-interpret-clarify-title">
          Нужно уточнение (interpret)
        </div>
        <p className="user-result-body muted">Выберите вариант ниже или откройте панель оператора для сырого JSON.</p>
      </div>
    )
  }

  if (lastInterpret?.status === 'success' && !lastExecute && busy) {
    return (
      <div className="user-result-panel user-result-loading" data-testid="user-result-panel" role="status">
        <div className="user-result-title" data-testid="user-result-loading">
          Выполняется запрос к execute…
        </div>
      </div>
    )
  }

  return (
    <div className="user-result-panel muted" data-testid="user-result-panel">
      Interpret успешен; ответ execute ещё не получен. Проверьте панель оператора при зависании.
    </div>
  )
}
