// src/screens/ResultScreen.jsx：预约结果页（导航/改约/取消/到站须知/站长虚拟号）
import { useState } from 'react';
import * as api from '../api';

export default function ResultScreen({ bookingView, token, onBack, onProfile, onUpdate }) {
  const [view, setView] = useState(bookingView);
  const [mode, setMode] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const booking = view.booking;
  const cancelled = booking.status === 'cancelled';

  async function doReschedule(slot) {
    setBusy(true);
    setError('');
    try {
      const next = await api.rescheduleBooking(booking.id, slot, token);
      setView(next);
      onUpdate(next);
      setMode(null);
    } catch (err) {
      setError(err.message || '改约失败');
    } finally {
      setBusy(false);
    }
  }

  async function doCancel() {
    setBusy(true);
    setError('');
    try {
      const next = await api.cancelBooking(booking.id, token);
      setView(next);
      onUpdate(next);
      setMode(null);
    } catch (err) {
      setError(err.message || '取消失败');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="screen result-screen" data-testid="result-screen">
      <div className="result-hero">
        <div className={`status-pill ${cancelled ? 'cancelled' : ''}`} data-testid="booking-status">
          {cancelled ? '预约已取消' : '预约成功'}
        </div>
        <h1>{view.station.name}</h1>
        <p className="slot-line" data-testid="booking-slot">
          时段：{booking.slot_start}
        </p>
        <p className="muted">预约号：{booking.id}</p>
      </div>

      <div className="result-actions">
        <a className="primary block" data-testid="nav-link" href={view.navigation.amap_uri} target="_blank" rel="noreferrer">
          {view.navigation.label}
        </a>
        <a className="primary block call" data-testid="call-station-btn" href={view.virtual_phone.tel}>
          拨打站长虚拟号 {view.virtual_phone.display}
        </a>
        <div className="row">
          <button
            type="button"
            className="ghost"
            data-testid="reschedule-btn"
            onClick={() => setMode(mode === 'reschedule' ? null : 'reschedule')}
            disabled={cancelled}
          >
            改约
          </button>
          <button
            type="button"
            className="danger"
            data-testid="cancel-btn"
            onClick={() => setMode(mode === 'cancel' ? null : 'cancel')}
            disabled={cancelled}
          >
            取消预约
          </button>
        </div>
      </div>

      {mode === 'reschedule' && (
        <div className="panel" data-testid="reschedule-panel">
          <h2>选择新时段</h2>
          <div className="slot-grid">
            {view.reschedule_slots.map((slot) => (
              <button
                type="button"
                key={slot}
                className="slot-btn"
                data-testid="reschedule-slot"
                disabled={busy}
                onClick={() => doReschedule(slot)}
              >
                {slot.slice(5)}
              </button>
            ))}
          </div>
        </div>
      )}

      {mode === 'cancel' && (
        <div className="panel" data-testid="cancel-panel">
          <h2>确认取消预约？</h2>
          <p className="muted">取消后名额会释放，您可以回到对话重新选择站点。</p>
          <button type="button" className="danger block" data-testid="cancel-confirm" onClick={doCancel} disabled={busy}>
            {busy ? '处理中…' : '确认取消'}
          </button>
        </div>
      )}

      {error && (
        <p className="error-text" data-testid="result-error">
          {error}
        </p>
      )}

      <section className="arrival" data-testid="arrival-notes">
        <h2>到站须知</h2>
        <ul>
          {view.arrival_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>

      <div className="result-footer">
        <button type="button" className="ghost" data-testid="open-profile" onClick={onProfile}>
          我的信息
        </button>
        <button type="button" className="ghost" data-testid="back-to-chat" onClick={onBack}>
          返回对话
        </button>
      </div>
    </main>
  );
}
