// src/App.jsx：入口渠道 → 同意 → 对话 → 预约结果 / 个人信息自助
import { useState } from 'react';
import AiBanner from './components/Banner';
import ConsentScreen from './screens/ConsentScreen';
import ChatScreen from './screens/ChatScreen';
import ResultScreen from './screens/ResultScreen';
import ProfileScreen from './screens/ProfileScreen';
import { KEYS, clearRegistration, readJSON, writeJSON } from './storage';

function entryChannel() {
  const params = new URLSearchParams(window.location.search);
  const channel = params.get('source_channel');
  return channel && channel.trim() ? channel.trim() : 'direct';
}

export default function App() {
  const [sourceChannel] = useState(entryChannel);
  const [sessionData, setSessionData] = useState(() => readJSON(KEYS.session));
  const [progress, setProgress] = useState(
    () => readJSON(KEYS.progress, { done: 0, total: 7, fields: [] }),
  );
  const [screen, setScreen] = useState(() => (readJSON(KEYS.session) ? 'chat' : 'consent'));
  const [prevScreen, setPrevScreen] = useState('chat');
  const [bookingView, setBookingView] = useState(null);
  const [notice, setNotice] = useState('');

  function consentDone(nextSession, nextProgress) {
    setSessionData(nextSession);
    setProgress(nextProgress);
    setNotice('');
    setScreen('chat');
  }

  function progressChanged(nextProgress) {
    setProgress(nextProgress);
    writeJSON(KEYS.progress, nextProgress);
  }

  function booked(view) {
    setBookingView(view);
    setScreen('result');
  }

  function sessionLost(message) {
    clearRegistration();
    setSessionData(null);
    setBookingView(null);
    setNotice(message);
    setScreen('consent');
  }

  function revoked(message) {
    clearRegistration();
    setSessionData(null);
    setBookingView(null);
    setScreen('revoked');
    setNotice(message);
  }

  function openProfile() {
    setPrevScreen(screen);
    setScreen('profile');
  }

  return (
    <div className="app-shell">
      <AiBanner />
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">跑</span>
          <div>
            <strong>骑手报名</strong>
            <p className="muted tiny">渠道：{sourceChannel}</p>
          </div>
        </div>
      </header>

      {screen === 'consent' && (
        <ConsentScreen sourceChannel={sourceChannel} onDone={consentDone} notice={notice} />
      )}

      {screen === 'chat' && sessionData && (
        <ChatScreen
          sessionData={sessionData}
          initialProgress={progress}
          onProgress={progressChanged}
          onBooked={booked}
          onProfile={openProfile}
          onSessionLost={sessionLost}
        />
      )}

      {screen === 'result' && bookingView && sessionData && (
        <ResultScreen
          bookingView={bookingView}
          token={sessionData.token}
          onBack={() => setScreen('chat')}
          onProfile={openProfile}
          onUpdate={setBookingView}
        />
      )}

      {screen === 'profile' && sessionData && (
        <ProfileScreen
          sessionData={sessionData}
          onBack={() => setScreen(prevScreen)}
          onRevoked={revoked}
        />
      )}

      {screen === 'revoked' && (
        <main className="screen revoked-screen" data-testid="revoked-screen">
          <h1 className="screen-title">已撤回授权并删除</h1>
          <p className="muted">{notice || '您的报名信息与预约记录已删除，本机会话缓存已清空。'}</p>
          <button
            type="button"
            className="primary block"
            data-testid="restart-registration"
            onClick={() => setScreen('consent')}
          >
            重新开始
          </button>
        </main>
      )}
    </div>
  );
}
