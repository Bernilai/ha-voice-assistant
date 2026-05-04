import type { HouseState } from '../types/api'

type Props = {
  house: HouseState | null
  error: string | null
  loading: boolean
}

export function HouseOverview({ house, error, loading }: Props) {
  return (
    <section className="panel" data-testid="house-overview" aria-label="Состояние дома">
      <h2>Дом и комнаты</h2>
      {loading && !house ? <p className="muted">Загрузка…</p> : null}
      {error ? (
        <p className="error-text" data-testid="house-error" role="alert">
          {error}
        </p>
      ) : null}
      {house ? (
        <div data-testid="house-state">
          {house.rooms.map((room) => (
            <div key={room.room_id} className="room-block" data-testid={`room-${room.room_id}`}>
              <div className="room-title">
                {room.name}{' '}
                <span className="muted">({room.room_id})</span>
              </div>
              {room.devices.length ? (
                <div data-testid={`room-${room.room_id}-devices`}>
                  {room.devices.map((d) => (
                    <div key={d.entity_id} className="device-row" data-testid={`device-${d.entity_id}`}>
                      <strong>{d.name}</strong> — {d.state}
                      <span className="muted"> · {d.entity_id}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">Нет устройств в выборке.</p>
              )}
              {room.sensors.length ? (
                <div data-testid={`room-${room.room_id}-sensors`}>
                  {room.sensors.map((s) => (
                    <div key={s.entity_id} className="sensor-row" data-testid={`sensor-${s.entity_id}`}>
                      {s.name} ({s.kind}): {s.state}
                      {s.unit ? ` ${s.unit}` : ''}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : !error && !loading ? (
        <p className="muted">Нет данных.</p>
      ) : null}
    </section>
  )
}
