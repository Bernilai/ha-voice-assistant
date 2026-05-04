import type { EventItem } from '../types/api'

type Props = {
  events: EventItem[]
  error: string | null
}

export function EventLogPanel({ events, error }: Props) {
  return (
    <section className="panel" data-testid="event-log" aria-label="Журнал событий">
      <h2>События</h2>
      {error ? (
        <p className="error-text" data-testid="events-error" role="alert">
          {error}
        </p>
      ) : null}
      {events.length === 0 && !error ? <p className="muted">Пока пусто.</p> : null}
      <div data-testid="event-log-list">
        {events.map((ev) => (
          <div key={ev.id} className="event-row" data-testid={`event-row-${ev.id}`}>
            <span className="muted">{ev.timestamp}</span> · <strong>{ev.type}</strong> — {ev.message}
          </div>
        ))}
      </div>
    </section>
  )
}
