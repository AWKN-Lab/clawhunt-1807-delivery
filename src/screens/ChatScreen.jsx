// src/screens/ChatScreen.jsx：对话页（气泡/快捷选项/进度/语音回退/转人工/断网恢复）
import { useEffect, useRef, useState } from 'react';
import * as api from '../api';
import { PolicyCard, StationsCard } from '../components/Cards';
import Progress from '../components/Progress';
import { useOnlineStatus } from '../components/Banner';

function CardRenderer({ card, onBook }) {
  if (!card) return null;
  if (card.type === 'policy') return <PolicyCard card={card} />;
  if (card.type === 'stations') return <StationsCard card={card} onBook={onBook} />;
  return null;
}

export default function ChatScreen({
  sessionData,
  initialProgress,
  onProgress,
  onBooked,
  onProfile,
  onSessionLost,
}) {
  const online = useOnlineStatus();
  const [messages, setMessages] = useState([]);
  const [quickReplies, setQuickReplies] = useState([]);
  const [progress, setProgress] = useState(initialProgress || { done: 0, total: 7, fields: [] });
  const [actions, setActions] = useState([]);
  const [stateName, setStateName] = useState('collecting');
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [voiceHint, setVoiceHint] = useState('');
  const [handoff, setHandoff] = useState(null);
  const [loading, setLoading] = useState(true);
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  function persist(nextProgress) {
    setProgress(nextProgress);
    onProgress(nextProgress);
  }

  async function loadSession() {
    try {
      const data = await api.getSession(sessionData.session_id, sessionData.token);
      setMessages(data.messages || []);
      setQuickReplies(data.quick_replies || []);
      setActions(data.actions || []);
      setStateName(data.state || 'collecting');
      persist(data.progress);
      setError('');
    } catch (err) {
      if (err.status === 410) {
        onSessionLost('会话已失效，请重新阅读告知并同意后开始。');
        return;
      }
      setError(`会话恢复失败：${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionData.session_id]);

  useEffect(() => {
    if (!online) return;
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [online]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length]);

  async function submit(text) {
    const value = String(text || '').trim();
    if (!value || sending) return;
    if (!navigator.onLine) {
      setError('当前已断网，消息未发送；进度已保存在本机，恢复网络后可继续。');
      return;
    }
    setSending(true);
    setError('');
    setQuickReplies([]);
    const userMessage = { role: 'user', text: value };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    try {
      const data = await api.sendMessage(sessionData.session_id, sessionData.token, value);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: data.reply, card: data.card, actions: data.actions },
      ]);
      setQuickReplies(data.quick_replies || []);
      setActions(data.actions || []);
      persist(data.progress);
      if (data.actions?.includes('end_minor')) setStateName('ended');
    } catch (err) {
      if (err.status === 410) {
        onSessionLost('会话已失效，请重新开始。');
        return;
      }
      setError(`发送失败：${err.message}（进度已保存，可重试）`);
    } finally {
      setSending(false);
    }
  }

  async function book(station, slot) {
    const result = await api.createBooking(station.id, slot, sessionData.token);
    onBooked(result);
  }

  async function askHandoff() {
    try {
      const result = await api.requestHandoff(sessionData.session_id, sessionData.token);
      setHandoff(result);
    } catch (err) {
      setError(`转人工失败：${err.message}`);
    }
  }

  function useVoice() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setVoiceHint('当前浏览器不支持语音识别，已回退为文字输入，请直接打字。');
      inputRef.current?.focus();
      return;
    }
    try {
      const recognition = new Recognition();
      recognition.lang = 'zh-CN';
      recognition.interimResults = false;
      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript || '';
        if (transcript) {
          setVoiceHint(`语音已转写：${transcript}`);
          setInput(transcript);
        }
      };
      recognition.onerror = () => {
        setVoiceHint('语音识别失败，已回退为文字输入，请直接打字。');
        inputRef.current?.focus();
      };
      recognition.start();
    } catch {
      setVoiceHint('语音启动失败，已回退为文字输入，请直接打字。');
      inputRef.current?.focus();
    }
  }

  const ended = stateName === 'ended';

  return (
    <main className="screen chat-screen" data-testid="chat-screen">
      <div className="chat-top">
        <Progress progress={progress} />
        <div className="chat-actions">
          <button type="button" className="ghost small" data-testid="open-profile" onClick={onProfile}>
            我的信息
          </button>
          <button type="button" className="ghost small" data-testid="handoff-btn" onClick={askHandoff}>
            转人工
          </button>
        </div>
      </div>

      {!online && (
        <p className="offline-note" data-testid="offline-note">
          当前离线：消息发送已暂停，进度保存在本机。
        </p>
      )}

      {loading && <p className="muted">正在恢复会话…</p>}

      <div className="chat-list" data-testid="chat-list">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`bubble-row ${message.role === 'user' ? 'from-user' : 'from-bot'}`}
          >
            {message.role === 'assistant' && <span className="avatar">AI</span>}
            <div className={`bubble ${message.role === 'user' ? 'user' : 'bot'}`}>
              {message.text && <p>{message.text}</p>}
              <CardRenderer card={message.card} onBook={book} />
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {handoff && (
        <div className="handoff-card" data-testid="handoff-card">
          已转人工：工单 {handoff.ticket_id}，排队第 {handoff.queue_position} 位，也可拨打 {handoff.phone}
        </div>
      )}

      {ended && (
        <div className="end-card" data-testid="end-minor">
          本次收集已结束：未满 18 周岁暂不能报名配送岗位。
        </div>
      )}

      {voiceHint && (
        <p className="voice-hint" data-testid="voice-hint">
          {voiceHint}
        </p>
      )}

      {error && (
        <p className="error-text" data-testid="chat-error">
          {error}
        </p>
      )}

      {quickReplies.length > 0 && (
        <div className="quick-replies" data-testid="quick-replies">
          {quickReplies.map((reply) => (
            <button
              type="button"
              className="quick-chip"
              key={reply}
              data-testid="quick-reply"
              onClick={() => submit(reply)}
              disabled={sending}
            >
              {reply}
            </button>
          ))}
        </div>
      )}

      <div className="composer" data-testid="composer">
        <button type="button" className="icon-btn" data-testid="voice-btn" onClick={useVoice} aria-label="语音输入">
          🎤
        </button>
        <input
          ref={inputRef}
          className="text-input"
          data-testid="message-input"
          value={input}
          maxLength={500}
          placeholder={ended ? '本次收集已结束' : '输入回答，或点上方快捷选项'}
          disabled={ended}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') submit(input);
          }}
        />
        <button
          type="button"
          className="primary"
          data-testid="send-btn"
          onClick={() => submit(input)}
          disabled={sending || ended || !input.trim()}
        >
          {sending ? '发送中' : '发送'}
        </button>
      </div>
      <p className="muted tiny">语音识别不可用时会自动回退为文字输入。</p>
    </main>
  );
}
