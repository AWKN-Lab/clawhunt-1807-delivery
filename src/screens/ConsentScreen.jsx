// src/screens/ConsentScreen.jsx：告知同意页（不勾选无法开始；不同意有电话出口）
import { useState } from 'react';
import * as api from '../api';
import { KEYS, writeJSON } from '../storage';

const SECTIONS = [
  {
    title: '我们会收集什么',
    items: [
      '称呼、出生年月、意向区域（到街道级）、岗位意向、车辆情况、到岗时间、配送经验。',
      '联系方式仅用于预约到站与改约通知，不用于营销。',
    ],
  },
  {
    title: '我们不收集什么',
    items: [
      '身份证号、银行卡号、人脸信息、通讯录、精确住址与定位轨迹。',
      '不会把您的信息卖给第三方。',
    ],
  },
  {
    title: '用途',
    items: ['按意向区域匹配就近站点，生成预约，并由站长电话回访。'],
  },
  {
    title: '保存期限',
    items: ['自同意之日起 180 天；到期自动删除。您可随时撤回授权并立即删除。'],
  },
  {
    title: '您的权利',
    items: ['查看、更正、下载信息副本、撤回授权并删除、要求转人工。'],
  },
];

export default function ConsentScreen({ sourceChannel, onDone, notice }) {
  const [checked, setChecked] = useState(false);
  const [showPhone, setShowPhone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function start() {
    if (!checked) return;
    setBusy(true);
    setError('');
    const payload = {
      consent_version: 'v1.0',
      consent_at: new Date().toISOString(),
      source_channel: sourceChannel,
    };
    try {
      const consent = await api.createConsent(payload);
      const session = await api.createSession(consent.candidate_id, sourceChannel);
      const sessionData = {
        session_id: session.session_id,
        token: session.token,
        candidate_id: consent.candidate_id,
        source_channel: sourceChannel,
      };
      writeJSON(KEYS.session, sessionData);
      writeJSON(KEYS.progress, { done: 0, total: 7, fields: [] });
      onDone(sessionData, { done: 0, total: 7, fields: [] });
    } catch (err) {
      setError(err.message || '网络异常，请稍后重试');
      setBusy(false);
    }
  }

  return (
    <main className="screen consent-screen" data-testid="consent-screen">
      <div className="channel-chip" data-testid="channel-chip">
        入口渠道：{sourceChannel}
      </div>
      <h1 className="screen-title">报名前，请先了解这些</h1>
      <p className="screen-subtitle">这是一段由 AI 助手完成的报名信息收集，您可以随时要求转人工。</p>
      {notice && (
        <p className="notice" data-testid="consent-notice">
          {notice}
        </p>
      )}

      <div className="consent-sections">
        {SECTIONS.map((section) => (
          <section className="consent-section" key={section.title}>
            <h2>{section.title}</h2>
            <ul>
              {section.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <label className="consent-check">
        <input
          type="checkbox"
          data-testid="consent-checkbox"
          checked={checked}
          onChange={(event) => setChecked(event.target.checked)}
        />
        <span>我已阅读并同意上述告知内容（同意版本 v1.0）</span>
      </label>

      {error && (
        <p className="error-text" data-testid="consent-error">
          {error}
        </p>
      )}

      <div className="consent-actions">
        <button
          type="button"
          className="primary block"
          data-testid="consent-start"
          disabled={!checked || busy}
          onClick={start}
        >
          {busy ? '正在建立会话…' : '同意并开始'}
        </button>
        <button
          type="button"
          className="ghost block"
          data-testid="consent-reject"
          onClick={() => setShowPhone(true)}
        >
          不同意，电话咨询
        </button>
      </div>

      {showPhone && (
        <div className="phone-panel" data-testid="consent-phone" role="region" aria-label="电话咨询出口">
          <p>您可以不授权，直接电话咨询招募专员：</p>
          <a href="tel:4000001807" className="phone-link">
            拨打 400-000-1807
          </a>
          <p className="muted">不提供信息也可以咨询岗位情况；电话咨询不会自动创建报名记录。</p>
        </div>
      )}
    </main>
  );
}
