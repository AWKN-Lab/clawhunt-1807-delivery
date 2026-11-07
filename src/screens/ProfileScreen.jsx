// src/screens/ProfileScreen.jsx：个人信息自助（查看/更正/下载副本/撤回删除/联系人工）
import { useEffect, useState } from 'react';
import * as api from '../api';
import { clearRegistration } from '../storage';

const JOB_LABELS = { fulltime: '全职', parttime: '兼职', undecided: '待定' };
const STATUS_LABELS = {
  new: '新线索',
  collecting: '收集中',
  complete: '信息完整',
  booked: '已预约',
  interviewed: '已面试',
  hired: '已入职',
  rejected: '未通过',
  handoff: '已转人工',
};

export default function ProfileScreen({ sessionData, onBack, onRevoked }) {
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [confirmRevoke, setConfirmRevoke] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState({ area_text: '', job_type: 'undecided', start_text: '', experience_text: '' });

  async function load() {
    try {
      const data = await api.getCandidate(sessionData.candidate_id, sessionData.token);
      setCandidate(data);
      setForm({
        area_text: data.area_text || '',
        job_type: data.job_type || 'undecided',
        start_text: data.start_text || '',
        experience_text: data.experience_text || '',
      });
    } catch (err) {
      if (err.status === 410) {
        onRevoked('会话已失效，本地缓存已清空。');
        return;
      }
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionData.candidate_id]);

  async function save() {
    setError('');
    try {
      const updated = await api.patchCandidate(
        sessionData.candidate_id,
        {
          area_text: form.area_text,
          job_type: form.job_type,
          start_text: form.start_text,
          experience_text: form.experience_text,
        },
        sessionData.token,
      );
      setCandidate(updated);
      setEditing(false);
      setNotice('信息已更正');
    } catch (err) {
      setError(`更正失败：${err.message}`);
    }
  }

  async function downloadCopy() {
    setError('');
    try {
      const { blob, filename } = await api.downloadCandidateCopy(sessionData.candidate_id, sessionData.token);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setNotice('信息副本已下载');
    } catch (err) {
      setError(`下载失败：${err.message}`);
    }
  }

  async function revoke() {
    setError('');
    try {
      await api.revokeCandidate(sessionData.candidate_id, sessionData.token);
      clearRegistration();
      onRevoked('已撤回授权并删除信息，本地缓存与会话令牌已清空。');
    } catch (err) {
      setError(`撤回失败：${err.message}`);
    }
  }

  if (loading) {
    return (
      <main className="screen profile-screen" data-testid="profile-screen">
        <p className="muted">正在加载我的信息…</p>
      </main>
    );
  }

  return (
    <main className="screen profile-screen" data-testid="profile-screen">
      <h1 className="screen-title">我的信息</h1>
      <button type="button" className="ghost small back" data-testid="profile-back" onClick={onBack}>
        返回
      </button>

      {candidate && (
        <div className="profile-card" data-testid="profile-info">
          <div className="info-row"><span>称呼</span><strong data-testid="profile-name">{candidate.name}</strong></div>
          <div className="info-row"><span>手机号</span><strong data-testid="profile-phone">{candidate.phone}</strong></div>
          <div className="info-row"><span>出生年月</span><strong>{candidate.birth_ym || '未填'}</strong></div>
          <div className="info-row"><span>意向区域</span><strong data-testid="profile-area">{candidate.area_text || '未填'}</strong></div>
          <div className="info-row"><span>岗位意向</span><strong>{JOB_LABELS[candidate.job_type] || '未填'}</strong></div>
          <div className="info-row"><span>到岗时间</span><strong>{candidate.start_text || '未填'}</strong></div>
          <div className="info-row"><span>配送经验</span><strong>{candidate.experience_text || '未填'}</strong></div>
          <div className="info-row"><span>状态</span><strong>{STATUS_LABELS[candidate.status] || candidate.status}</strong></div>
          <div className="info-row"><span>同意版本</span><strong data-testid="profile-consent-version">{candidate.consent_version}</strong></div>
          <div className="info-row"><span>同意时间</span><strong data-testid="profile-consent-at">{candidate.consent_at}</strong></div>
          <div className="info-row"><span>保存至</span><strong>{candidate.retention_until}</strong></div>
        </div>
      )}

      {notice && <p className="notice" data-testid="profile-notice">{notice}</p>}
      {error && <p className="error-text" data-testid="profile-error">{error}</p>}

      {!editing ? (
        <div className="profile-actions">
          <button type="button" className="primary block" data-testid="edit-info" onClick={() => setEditing(true)}>
            更正我的信息
          </button>
          <button type="button" className="ghost block" data-testid="download-copy" onClick={downloadCopy}>
            下载信息副本
          </button>
          <a className="ghost block" data-testid="contact-human" href="tel:4000001807">
            联系人工（400-000-1807）
          </a>
          <button
            type="button"
            className="danger block"
            data-testid="revoke-consent"
            onClick={() => setConfirmRevoke(true)}
          >
            撤回授权并删除
          </button>
        </div>
      ) : (
        <div className="panel" data-testid="edit-panel">
          <h2>更正信息</h2>
          <label>
            意向区域
            <input
              data-testid="edit-area"
              value={form.area_text}
              onChange={(event) => setForm({ ...form, area_text: event.target.value })}
            />
          </label>
          <label>
            岗位意向
            <select
              data-testid="edit-job"
              value={form.job_type}
              onChange={(event) => setForm({ ...form, job_type: event.target.value })}
            >
              <option value="fulltime">全职</option>
              <option value="parttime">兼职</option>
              <option value="undecided">待定</option>
            </select>
          </label>
          <label>
            到岗时间
            <input
              data-testid="edit-start"
              value={form.start_text}
              onChange={(event) => setForm({ ...form, start_text: event.target.value })}
            />
          </label>
          <label>
            配送经验
            <input
              data-testid="edit-experience"
              value={form.experience_text}
              onChange={(event) => setForm({ ...form, experience_text: event.target.value })}
            />
          </label>
          <div className="row">
            <button type="button" className="primary" data-testid="save-edit" onClick={save}>
              保存更正
            </button>
            <button type="button" className="ghost" data-testid="cancel-edit" onClick={() => setEditing(false)}>
              取消
            </button>
          </div>
        </div>
      )}

      {confirmRevoke && (
        <div className="panel danger-panel" data-testid="revoke-confirm-panel">
          <h2>确认撤回授权？</h2>
          <p>撤回后，本服务会立即删除您的报名信息、预约记录，并清空本机会话与进度缓存。</p>
          <button type="button" className="danger block" data-testid="revoke-confirm" onClick={revoke}>
            确认撤回并删除
          </button>
          <button type="button" className="ghost block" data-testid="revoke-cancel" onClick={() => setConfirmRevoke(false)}>
            再想想
          </button>
        </div>
      )}
    </main>
  );
}
