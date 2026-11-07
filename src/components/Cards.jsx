// src/components/Cards.jsx：政策回答卡 / 站点推荐卡
import { useState } from 'react';

export function PolicyCard({ card }) {
  return (
    <section className="card policy-card" data-testid="policy-card">
      <div className="card-badge">政策回答</div>
      <p className="card-answer">{card.answer}</p>
      <div className="source-list" data-testid="policy-sources">
        {(card.sources || []).map((source) => (
          <span className="source-tag" key={`${source.title}-${source.reference}`}>
            出处：{source.title} {source.reference}
            {source.updated_at ? `（更新 ${source.updated_at}）` : ''}
          </span>
        ))}
      </div>
      <p className="disclaimer" data-testid="policy-disclaimer">
        免责声明：{card.disclaimer}
      </p>
    </section>
  );
}

export function StationsCard({ card, onBook }) {
  const [selection, setSelection] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function confirm() {
    if (!selection) return;
    setBusy(true);
    setError('');
    try {
      await onBook(selection.station, selection.slot);
    } catch (err) {
      setError(err.message || '预约失败，请重试');
      setBusy(false);
    }
  }

  return (
    <section className="card stations-card" data-testid="stations-card">
      <div className="card-badge">站点推荐</div>
      <h3 className="card-title">{card.title || '按距离推荐站点'}</h3>
      {(card.stations || []).map((station) => (
        <article className="station" data-testid="station-card" key={station.id}>
          <div className="station-head">
            <strong>{station.name}</strong>
            <span className="station-distance">{station.distance_km} km</span>
          </div>
          <div className="station-meta">
            在招 {station.open_quota} 人 · 地址坐标 {station.lat.toFixed(2)}, {station.lng.toFixed(2)}
          </div>
          <div className="slot-grid">
            {(station.slots || []).slice(0, 4).map((slot) => {
              const selected = selection && selection.slot === slot && selection.station.id === station.id;
              return (
                <button
                  type="button"
                  key={slot}
                  className={`slot-btn${selected ? ' selected' : ''}`}
                  data-testid="slot-btn"
                  onClick={() => setSelection({ station, slot })}
                >
                  {slot.slice(5)}
                </button>
              );
            })}
          </div>
          {selection && selection.station.id === station.id && (
            <div className="slot-selected">
              已选 {station.name} · {selection.slot}
            </div>
          )}
        </article>
      ))}
      {selection && (
        <div className="booking-bar" data-testid="booking-bar">
          <span>确认预约：{selection.station.name} · {selection.slot}</span>
          <button type="button" className="primary" data-testid="booking-confirm" onClick={confirm} disabled={busy}>
            {busy ? '提交中…' : '预约'}
          </button>
        </div>
      )}
      {error && (
        <p className="error-text" data-testid="booking-error">
          {error}
        </p>
      )}
    </section>
  );
}
