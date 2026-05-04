import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { App } from './App'

const sampleHouse = {
  version: 'p3-ha',
  rooms: [
    {
      room_id: 'kitchen',
      name: 'Кухня',
      devices: [
        {
          entity_id: 'light.kitchen_main',
          domain: 'light',
          name: 'Основной свет',
          state: 'off',
          device_class: null,
        },
      ],
      sensors: [],
    },
  ],
}

function jsonResponse(data: unknown, ok = true, status = ok ? 200 : 503): Promise<Response> {
  return Promise.resolve({
    ok,
    status,
    json: async () => data,
  } as Response)
}

function mockDemoResetResponse() {
  return {
    ok: true,
    message: 'House baseline restored.',
    event_log_cleared: true,
    clarification_sessions_cleared: true,
    baseline_strategy: 'mock_reset_to_baseline',
    baseline_semantics: 'Mock baseline shortcut.',
    reset_at: '2026-01-01T00:00:00Z',
  }
}

function mockDemoStatusResponse() {
  return {
    mode: 'simulator',
    mode_semantics: 'Simulator semantics.',
    last_reset_at: null,
    last_reset_ok: null,
    last_reset_baseline_strategy: null,
    last_replay_at: null,
    last_replay_summary: null,
    replay_catalog: [
      {
        id: 'lights_kitchen_cycle',
        title: 'Kitchen cycle',
        steps: 3,
        deterministic: true,
        notes: '',
      },
    ],
    reset_contract: 'POST /api/demo/reset clears events and clarification sessions.',
  }
}

function defaultMocks() {
  return vi.fn(async (input: RequestInfo, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.url
    if (url.includes('/api/health')) {
      return jsonResponse({ ok: true })
    }
    if (url.includes('/api/state/house')) {
      return jsonResponse(sampleHouse)
    }
    if (url.includes('/api/events')) {
      return jsonResponse({
        events: [
          {
            id: '42',
            timestamp: '2026-01-01T00:00:00Z',
            type: 'intent_interpret',
            message: 'Stub',
            metadata: {},
          },
        ],
        order: 'newest_first',
      })
    }
    if (url.includes('/api/demo/status')) {
      return jsonResponse(mockDemoStatusResponse())
    }
    if (url.includes('/api/demo/reset') && init?.method === 'POST') {
      return jsonResponse(mockDemoResetResponse())
    }
    if (url.includes('/api/voice/status')) {
      return jsonResponse({
        integration_kind: 'ha_assist_plus_transcript_bridge',
        bridge_enabled: true,
        transcript_endpoint_available: true,
        ha_assist_local_path: 'HA local.',
        transcript_bridge_path: 'Backend transcript.',
        supported_transcript_phrases_ru: ['включи свет на кухне'],
        intentionally_unsupported_via_transcript: ['clarify'],
        clarification_policy_ru: 'Text only for clarify.',
      })
    }
    return jsonResponse({ error: 'unmocked', url }, false, 500)
  })
}

describe('App P6a', () => {
  it('loads house state and renders rooms/devices from GET /api/state/house', async () => {
    vi.stubGlobal('fetch', defaultMocks())
    render(<App />)
    await waitFor(() => {
      expect(screen.getByTestId('house-state')).toBeInTheDocument()
    })
    expect(screen.getByTestId('room-kitchen')).toBeInTheDocument()
    expect(screen.getByTestId('device-light.kitchen_main')).toHaveTextContent('Основной свет')
  })

  it('renders event log from GET /api/events', async () => {
    vi.stubGlobal('fetch', defaultMocks())
    render(<App />)
    await waitFor(() => {
      expect(screen.getByTestId('event-log-list')).toBeInTheDocument()
    })
    expect(screen.getByTestId('event-row-42')).toHaveTextContent('intent_interpret')
  })

  it('shows house error when GET /api/state/house fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo) => {
        const url = typeof input === 'string' ? input : input.url
        if (url.includes('/api/health')) {
          return jsonResponse({})
        }
        if (url.includes('/api/state/house')) {
          return jsonResponse({ detail: { code: 'ha_unreachable', message: 'HA недоступен' } }, false, 503)
        }
        if (url.includes('/api/events')) {
          return jsonResponse({ events: [], order: 'newest_first' })
        }
        return jsonResponse({}, false, 500)
      }),
    )
    render(<App />)
    await waitFor(() => {
      expect(screen.getByTestId('house-error')).toHaveTextContent('HA недоступен')
    })
  })

  it('submits text: interpret success then execute success', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.url
      if (url.includes('/api/health')) {
        return jsonResponse({})
      }
      if (url.includes('/api/state/house')) {
        return jsonResponse(sampleHouse)
      }
      if (url.includes('/api/events')) {
        return jsonResponse({ events: [], order: 'newest_first' })
      }
      if (url.includes('/api/intents/interpret') && init?.method === 'POST') {
        return jsonResponse({
          raw_text: 'включи свет на кухне',
          normalized_text: 'включи свет на кухне',
          canonical_intent: 'turn_on_device',
          entities: { room: 'kitchen', device_type: 'light', target_entity_id: 'light.kitchen_main' },
          status: 'success',
          clarification: null,
        })
      }
      if (url.includes('/api/intents/execute') && init?.method === 'POST') {
        return jsonResponse({
          status: 'success',
          spoken_response: 'Включила.',
          ui_message: 'Свет на кухне включён.',
          affected_entities: ['light.kitchen_main'],
          queried_entities: [],
          trace: { intent: 'turn_on_device' },
          error_code: null,
          error_message: null,
          clarification: null,
        })
      }
      return jsonResponse({}, false, 500)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.type(screen.getByTestId('command-input'), 'включи свет на кухне')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('execute-status')).toHaveTextContent('success')
    })
    expect(screen.getByTestId('execute-ui-message')).toHaveTextContent('Свет на кухне включён.')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/intents/interpret',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/intents/execute',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('renders interpret clarification options for missing_room', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.url
        if (url.includes('/api/health')) {
          return jsonResponse({})
        }
        if (url.includes('/api/state/house')) {
          return jsonResponse(sampleHouse)
        }
        if (url.includes('/api/events')) {
          return jsonResponse({ events: [], order: 'newest_first' })
        }
        if (url.includes('/api/intents/interpret') && init?.method === 'POST') {
          return jsonResponse({
            raw_text: 'выключи свет',
            normalized_text: 'выключи свет',
            canonical_intent: null,
            entities: {},
            status: 'clarification_required',
            clarification: {
              reason: 'missing_room',
              prompt: 'В какой комнате?',
              options: [
                { label: 'Кухня', room: 'kitchen' },
                { label: 'Гостиная', room: 'living_room' },
              ],
            },
          })
        }
        return jsonResponse({}, false, 500)
      }),
    )

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.type(screen.getByTestId('command-input'), 'выключи свет')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('interpret-clarification')).toBeInTheDocument()
    })
    expect(screen.getByTestId('interpret-option-kitchen')).toBeVisible()
  })

  it('shows fallback when interpret returns clarification_required but shape is not supported', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.url
        if (url.includes('/api/health')) {
          return jsonResponse({})
        }
        if (url.includes('/api/state/house')) {
          return jsonResponse(sampleHouse)
        }
        if (url.includes('/api/events')) {
          return jsonResponse({ events: [], order: 'newest_first' })
        }
        if (url.includes('/api/intents/interpret') && init?.method === 'POST') {
          return jsonResponse({
            raw_text: 'нужно уточнение',
            normalized_text: 'нужно уточнение',
            canonical_intent: null,
            entities: {},
            status: 'clarification_required',
            clarification: {
              reason: 'future_stub_kind',
              prompt: 'Выберите вариант',
              options: [{ id: 'a', label: 'A' }],
            },
          })
        }
        return jsonResponse({}, false, 500)
      }),
    )

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.type(screen.getByTestId('command-input'), 'нужно уточнение')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('interpret-clarification-unsupported')).toBeVisible()
    })
    expect(screen.getByTestId('interpret-clarification-unsupported').textContent ?? '').toContain(
      'Это уточнение пока не поддержано в текущем UI',
    )
    expect(screen.queryByTestId('interpret-clarification')).not.toBeInTheDocument()
    await user.click(screen.getByTestId('operator-debug-toggle'))
    await waitFor(() => {
      expect(screen.getByTestId('interpret-trace')).toHaveTextContent('future_stub_kind')
    })
  })

  it('execute clarification_required shows options; clarify posts and shows success', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.url
      const method = init?.method ?? 'GET'
      const body = init?.body ? JSON.parse(String(init.body)) : null

      if (url.includes('/api/health')) {
        return jsonResponse({})
      }
      if (url.includes('/api/state/house')) {
        return jsonResponse(sampleHouse)
      }
      if (url.includes('/api/events')) {
        return jsonResponse({ events: [], order: 'newest_first' })
      }

      if (url.includes('/api/intents/interpret') && method === 'POST') {
        return jsonResponse({
          raw_text: 'test',
          normalized_text: 'test',
          canonical_intent: 'turn_on_device',
          entities: { room: 'kitchen', device_type: 'light' },
          status: 'success',
          clarification: null,
        })
      }

      if (url.includes('/api/intents/execute') && method === 'POST') {
        return jsonResponse({
          status: 'clarification_required',
          spoken_response: 'Уточните.',
          ui_message: 'Несколько светильников',
          affected_entities: [],
          queried_entities: [],
          trace: { execution_engine: 'p5-execute' },
          error_code: null,
          error_message: null,
          clarification: {
            session_id: 'sess-1',
            pending_intent: 'turn_on_device',
            options: [
              { id: 'light.kitchen_main', label: 'Основной', room_id: 'kitchen' },
              { id: 'light.kitchen_accent', label: 'Акцент', room_id: 'kitchen' },
            ],
            expires_in_seconds: 60,
          },
        })
      }

      if (url.includes('/api/intents/clarify') && method === 'POST') {
        expect(body).toEqual({ session_id: 'sess-1', reply: 'light.kitchen_main' })
        return jsonResponse({
          status: 'success',
          spoken_response: 'Готово.',
          ui_message: 'Включено.',
          affected_entities: ['light.kitchen_main'],
          queried_entities: [],
          trace: {},
          error_code: null,
          error_message: null,
          clarification: null,
        })
      }

      return jsonResponse({}, false, 500)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.type(screen.getByTestId('command-input'), 'ambiguous kitchen lights')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('execute-clarification')).toBeInTheDocument()
    })
    expect(screen.getByTestId('execute-clarification-session')).toHaveTextContent('sess-1')
    expect(screen.getByTestId('execute-clarification-pending-intent')).toHaveTextContent('turn_on_device')
    expect(screen.getByTestId('execute-clarification-expires')).toHaveTextContent('60')
    expect(screen.getByTestId('execute-clarification-path')).toHaveTextContent('POST /api/intents/clarify')

    const clarifyBtn = screen.getByTestId('execute-clarify-light_kitchen_main')
    await user.click(clarifyBtn)

    await waitFor(() => {
      expect(screen.getByTestId('execute-status')).toHaveTextContent('success')
    })
    expect(screen.getByTestId('execute-ui-message')).toHaveTextContent('Включено.')
  })

  it('renders execute error summary', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.url
        const method = init?.method ?? 'GET'
        if (url.includes('/api/health')) {
          return jsonResponse({})
        }
        if (url.includes('/api/state/house')) {
          return jsonResponse(sampleHouse)
        }
        if (url.includes('/api/events')) {
          return jsonResponse({ events: [], order: 'newest_first' })
        }
        if (url.includes('/api/intents/interpret') && method === 'POST') {
          return jsonResponse({
            raw_text: 'x',
            normalized_text: 'x',
            canonical_intent: 'turn_on_device',
            entities: { room: 'kitchen', device_type: 'light', target_entity_id: 'light.kitchen_main' },
            status: 'success',
            clarification: null,
          })
        }
        if (url.includes('/api/intents/execute') && method === 'POST') {
          return jsonResponse({
            status: 'error',
            spoken_response: 'Нельзя.',
            ui_message: 'Ошибка выполнения',
            affected_entities: [],
            queried_entities: [],
            trace: { intent: 'turn_on_device' },
            error_code: 'unsupported_target',
            error_message: 'bad',
            clarification: null,
          })
        }
        return jsonResponse({}, false, 500)
      }),
    )

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())
    await user.type(screen.getByTestId('command-input'), 'x')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => {
      const summary = screen.getByTestId('execute-summary')
      expect(within(summary).getByTestId('execute-error')).toHaveTextContent('unsupported_target')
    })
  })
})

describe('App P6b operator/debug', () => {
  it('operator panel toggle shows trace summary and raw JSON', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', defaultMocks())
    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    expect(screen.queryByTestId('operator-debug-panel')).not.toBeInTheDocument()
    await user.click(screen.getByTestId('operator-debug-toggle'))
    expect(screen.getByTestId('operator-debug-panel')).toBeVisible()
    expect(screen.getByTestId('trace-summary-cards')).toBeInTheDocument()
    expect(screen.getByTestId('raw-json-summary')).toBeInTheDocument()
  })

  it('demo reset calls POST /api/demo/reset and shows success hint', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.url
      const method = init?.method ?? 'GET'
      if (url.includes('/api/health')) {
        return jsonResponse({})
      }
      if (url.includes('/api/state/house')) {
        return jsonResponse(sampleHouse)
      }
      if (url.includes('/api/events')) {
        return jsonResponse({ events: [], order: 'newest_first' })
      }
      if (url.includes('/api/demo/status')) {
        return jsonResponse(mockDemoStatusResponse())
      }
      if (url.includes('/api/demo/reset') && method === 'POST') {
        return jsonResponse(mockDemoResetResponse())
      }
      return jsonResponse({}, false, 500)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.click(screen.getByTestId('operator-debug-toggle'))
    await user.click(screen.getByTestId('demo-reset-button'))

    await waitFor(() => {
      expect(screen.getByTestId('demo-reset-ok')).toBeVisible()
    })
    expect(fetchMock).toHaveBeenCalledWith('/api/demo/reset', expect.objectContaining({ method: 'POST' }))
  })

  it('demo reset shows error when POST fails', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.url
        const method = init?.method ?? 'GET'
        if (url.includes('/api/health')) {
          return jsonResponse({})
        }
        if (url.includes('/api/state/house')) {
          return jsonResponse(sampleHouse)
        }
        if (url.includes('/api/events')) {
          return jsonResponse({ events: [], order: 'newest_first' })
        }
        if (url.includes('/api/demo/status')) {
          return jsonResponse(mockDemoStatusResponse())
        }
        if (url.includes('/api/demo/reset') && method === 'POST') {
          return jsonResponse({}, false, 500)
        }
        return jsonResponse({}, false, 500)
      }),
    )

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.click(screen.getByTestId('operator-debug-toggle'))
    await user.click(screen.getByTestId('demo-reset-button'))

    await waitFor(() => {
      expect(screen.getByTestId('demo-reset-error')).toBeVisible()
    })
  })

  it('failed clarify (HTTP 200 error body) shows failure panel', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.url
        const method = init?.method ?? 'GET'
        const body = init?.body ? JSON.parse(String(init.body)) : null

        if (url.includes('/api/health')) {
          return jsonResponse({})
        }
        if (url.includes('/api/state/house')) {
          return jsonResponse(sampleHouse)
        }
        if (url.includes('/api/events')) {
          return jsonResponse({ events: [], order: 'newest_first' })
        }
        if (url.includes('/api/demo/status')) {
          return jsonResponse(mockDemoStatusResponse())
        }
        if (url.includes('/api/demo/reset') && method === 'POST') {
          return jsonResponse(mockDemoResetResponse())
        }

        if (url.includes('/api/intents/interpret') && method === 'POST') {
          return jsonResponse({
            raw_text: 't',
            normalized_text: 't',
            canonical_intent: 'turn_on_device',
            entities: { room: 'kitchen', device_type: 'light' },
            status: 'success',
            clarification: null,
          })
        }

        if (url.includes('/api/intents/execute') && method === 'POST') {
          return jsonResponse({
            status: 'clarification_required',
            spoken_response: 'Уточните.',
            ui_message: 'Несколько светильников',
            affected_entities: [],
            queried_entities: [],
            trace: { execution_engine: 'p5-execute', phase: 'ambiguity', clarification_session_id: 'sess-x' },
            error_code: null,
            error_message: null,
            clarification: {
              session_id: 'sess-x',
              pending_intent: 'turn_on_device',
              options: [{ id: 'light.kitchen_main', label: 'Основной', room_id: 'kitchen' }],
              expires_in_seconds: 60,
            },
          })
        }

        if (url.includes('/api/intents/clarify') && method === 'POST') {
          expect(body).toEqual({ session_id: 'sess-x', reply: 'light.kitchen_main' })
          return jsonResponse({
            status: 'error',
            spoken_response: 'Не поняла ответ.',
            ui_message: 'Неверный ответ уточнения',
            affected_entities: [],
            queried_entities: [],
            trace: { phase: 'reply_match' },
            error_code: 'clarification_reply_invalid',
            error_message: 'no match',
            clarification: null,
          })
        }

        return jsonResponse({}, false, 500)
      }),
    )

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.type(screen.getByTestId('command-input'), 'x')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => expect(screen.getByTestId('execute-clarification')).toBeInTheDocument())
    await user.click(screen.getByTestId('execute-clarify-light_kitchen_main'))

    await waitFor(() => {
      expect(screen.getByTestId('execute-status')).toHaveTextContent('error')
    })
    expect(screen.getByTestId('user-result-error-code')).toHaveTextContent('clarification_reply_invalid')
  })

  it('trace summary reflects last response source after execute', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.url
      const method = init?.method ?? 'GET'
      if (url.includes('/api/health')) {
        return jsonResponse({})
      }
      if (url.includes('/api/state/house')) {
        return jsonResponse(sampleHouse)
      }
      if (url.includes('/api/events')) {
        return jsonResponse({ events: [], order: 'newest_first' })
      }
      if (url.includes('/api/demo/status')) {
        return jsonResponse(mockDemoStatusResponse())
      }
      if (url.includes('/api/demo/reset') && method === 'POST') {
        return jsonResponse(mockDemoResetResponse())
      }
      if (url.includes('/api/intents/interpret') && method === 'POST') {
        return jsonResponse({
          raw_text: 'включи свет на кухне',
          normalized_text: 'включи свет на кухне',
          canonical_intent: 'turn_on_device',
          entities: { room: 'kitchen', device_type: 'light', target_entity_id: 'light.kitchen_main' },
          status: 'success',
          clarification: null,
        })
      }
      if (url.includes('/api/intents/execute') && method === 'POST') {
        return jsonResponse({
          status: 'success',
          spoken_response: 'Ок.',
          ui_message: 'Ок.',
          affected_entities: ['light.kitchen_main'],
          queried_entities: [],
          trace: { execution_engine: 'p4a-ha', intent: 'turn_on_device' },
          error_code: null,
          error_message: null,
          clarification: null,
        })
      }
      return jsonResponse({}, false, 500)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.type(screen.getByTestId('command-input'), 'включи свет на кухне')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => expect(screen.getByTestId('execute-status')).toHaveTextContent('success'))

    await user.click(screen.getByTestId('operator-debug-toggle'))
    await waitFor(() => {
      expect(screen.getByTestId('trace-response-source')).toHaveTextContent('execute')
    })
    expect(screen.getByTestId('trace-engine')).toHaveTextContent('p4a-ha')
  })

  it('trace engine is neutral when response trace omits execution_engine and status_engine', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.url
      const method = init?.method ?? 'GET'
      if (url.includes('/api/health')) {
        return jsonResponse({})
      }
      if (url.includes('/api/state/house')) {
        return jsonResponse(sampleHouse)
      }
      if (url.includes('/api/events')) {
        return jsonResponse({ events: [], order: 'newest_first' })
      }
      if (url.includes('/api/demo/status')) {
        return jsonResponse(mockDemoStatusResponse())
      }
      if (url.includes('/api/demo/reset') && method === 'POST') {
        return jsonResponse(mockDemoResetResponse())
      }
      if (url.includes('/api/intents/interpret') && method === 'POST') {
        return jsonResponse({
          raw_text: 'q',
          normalized_text: 'q',
          canonical_intent: 'turn_on_device',
          entities: { room: 'kitchen', device_type: 'light', target_entity_id: 'light.kitchen_main' },
          status: 'success',
          clarification: null,
        })
      }
      if (url.includes('/api/intents/execute') && method === 'POST') {
        return jsonResponse({
          status: 'success',
          spoken_response: 'Ок.',
          ui_message: 'Ок.',
          affected_entities: ['light.kitchen_main'],
          queried_entities: [],
          trace: { intent: 'turn_on_device' },
          error_code: null,
          error_message: null,
          clarification: null,
        })
      }
      return jsonResponse({}, false, 500)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.type(screen.getByTestId('command-input'), 'q')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => expect(screen.getByTestId('execute-status')).toHaveTextContent('success'))

    await user.click(screen.getByTestId('operator-debug-toggle'))
    await waitFor(() => expect(screen.getByTestId('trace-engine')).toBeInTheDocument())
    expect(screen.getByTestId('trace-engine')).toHaveTextContent('—')
    expect(screen.getByTestId('trace-engine').textContent ?? '').not.toMatch(/stub/i)
  })

  it('trace clarification pending shows unsupported-in-UI when interpret clarification unsupported', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.url
        const method = init?.method ?? 'GET'
        if (url.includes('/api/health')) {
          return jsonResponse({})
        }
        if (url.includes('/api/state/house')) {
          return jsonResponse(sampleHouse)
        }
        if (url.includes('/api/events')) {
          return jsonResponse({ events: [], order: 'newest_first' })
        }
        if (url.includes('/api/demo/status')) {
          return jsonResponse(mockDemoStatusResponse())
        }
        if (url.includes('/api/demo/reset') && method === 'POST') {
          return jsonResponse(mockDemoResetResponse())
        }
        if (url.includes('/api/intents/interpret') && method === 'POST') {
          return jsonResponse({
            raw_text: 'нужно уточнение',
            normalized_text: 'нужно уточнение',
            canonical_intent: null,
            entities: {},
            status: 'clarification_required',
            clarification: {
              reason: 'future_stub_kind',
              prompt: 'Выберите вариант',
              options: [{ id: 'a', label: 'A' }],
            },
          })
        }
        return jsonResponse({}, false, 500)
      }),
    )

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())

    await user.type(screen.getByTestId('command-input'), 'нужно уточнение')
    await user.click(screen.getByTestId('command-submit'))

    await waitFor(() => expect(screen.getByTestId('interpret-clarification-unsupported')).toBeVisible())

    await user.click(screen.getByTestId('operator-debug-toggle'))
    await waitFor(() => expect(screen.getByTestId('trace-clarification-pending')).toBeVisible())
    expect(screen.getByTestId('trace-clarification-pending')).toHaveTextContent('interpret (не поддержано в UI)')
  })
})

describe('App P9 voice transcript strip', () => {
  it('loads voice status and submits transcript via POST /api/voice/transcript', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.url
      const method = init?.method ?? 'GET'
      if (url.includes('/api/health')) {
        return jsonResponse({})
      }
      if (url.includes('/api/state/house')) {
        return jsonResponse(sampleHouse)
      }
      if (url.includes('/api/events')) {
        return jsonResponse({ events: [], order: 'newest_first' })
      }
      if (url.includes('/api/voice/status')) {
        return jsonResponse({
          integration_kind: 'ha_assist_plus_transcript_bridge',
          bridge_enabled: true,
          transcript_endpoint_available: true,
          ha_assist_local_path: 'HA local.',
          transcript_bridge_path: 'Backend transcript.',
          supported_transcript_phrases_ru: ['включи свет на кухне'],
          intentionally_unsupported_via_transcript: [],
          clarification_policy_ru: 'Text.',
        })
      }
      if (url.includes('/api/voice/transcript') && method === 'POST') {
        return jsonResponse({
          outcome: 'executed',
          execution_claimed: true,
          transcript: 'включи свет на кухне',
          message_ru: 'Ок.',
          voice_path: 'transcript_bridge',
          interpret: {
            raw_text: 'включи свет на кухне',
            normalized_text: 'включи свет на кухне',
            canonical_intent: 'turn_on_device',
            entities: { room: 'kitchen', device_type: 'light', target_entity_id: 'light.kitchen_main' },
            status: 'success',
            clarification: null,
          },
          policy_reason: null,
          execute: {
            status: 'success',
            spoken_response: 'Ок.',
            ui_message: 'Ок.',
            affected_entities: ['light.kitchen_main'],
            queried_entities: [],
            trace: {},
            error_code: null,
            error_message: null,
            clarification: null,
          },
        })
      }
      return jsonResponse({}, false, 500)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())
    await waitFor(() => expect(screen.getByTestId('voice-status-line')).toHaveTextContent('Мост: включён'))

    await user.type(screen.getByTestId('voice-transcript-input'), 'включи свет на кухне')
    await user.click(screen.getByTestId('voice-transcript-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('voice-process-outcome')).toHaveTextContent('executed')
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/voice/transcript',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ transcript: 'включи свет на кухне' }),
      }),
    )
  })
})

describe('App P7 demo controls', () => {
  it('operator panel loads demo status and shows mode', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', defaultMocks())
    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())
    await user.click(screen.getByTestId('operator-debug-toggle'))
    await waitFor(() => {
      expect(screen.getByTestId('demo-status-mode')).toHaveTextContent('simulator')
    })
    expect(screen.getByTestId('demo-reset-contract')).toHaveTextContent('POST /api/demo/reset')
  })

  it('demo replay button posts scenario_id to /api/demo/replay', async () => {
    const user = userEvent.setup()
    const replayBody = {
      ok: true,
      scenario_id: 'lights_kitchen_cycle',
      steps_total: 3,
      steps_run: 3,
      stopped_early: false,
      step_results: [],
      detail: 'done',
      completed_at: '2026-01-01T00:00:00Z',
    }
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.url
      const method = init?.method ?? 'GET'
      if (url.includes('/api/health')) {
        return jsonResponse({})
      }
      if (url.includes('/api/state/house')) {
        return jsonResponse(sampleHouse)
      }
      if (url.includes('/api/events')) {
        return jsonResponse({ events: [], order: 'newest_first' })
      }
      if (url.includes('/api/demo/status')) {
        return jsonResponse(mockDemoStatusResponse())
      }
      if (url.includes('/api/demo/reset') && method === 'POST') {
        return jsonResponse(mockDemoResetResponse())
      }
      if (url.includes('/api/demo/replay') && method === 'POST') {
        return jsonResponse(replayBody)
      }
      return jsonResponse({}, false, 500)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await waitFor(() => expect(screen.getByTestId('house-state')).toBeInTheDocument())
    await user.click(screen.getByTestId('operator-debug-toggle'))
    await waitFor(() => expect(screen.getByTestId('demo-replay-lights_kitchen_cycle')).toBeInTheDocument())
    await user.click(screen.getByTestId('demo-replay-lights_kitchen_cycle'))
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/demo/replay',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ scenario_id: 'lights_kitchen_cycle' }),
        }),
      )
    })
  })
})
