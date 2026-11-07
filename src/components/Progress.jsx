// src/components/Progress.jsx：进度条 x/7 + 已收集字段
export default function Progress({ progress }) {
  const done = progress?.done || 0;
  const total = progress?.total || 7;
  const fields = progress?.fields || [];
  const percent = Math.round((done / total) * 100);
  return (
    <div className="progress" data-testid="progress">
      <div className="progress-head">
        <span data-testid="progress-text">
          已收集 {done}/{total} 项
        </span>
        <span className="progress-percent">{percent}%</span>
      </div>
      <div className="progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={done}>
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
      {fields.length > 0 && (
        <div className="progress-fields" data-testid="progress-fields">
          {fields.map((field) => (
            <span className="field-chip" key={field}>
              {field}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
