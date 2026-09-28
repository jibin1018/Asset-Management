import { FormEvent, ReactNode, useEffect, useState } from 'react';
import { won } from '../format';
import type { Advice, Category } from '../types';

export function Loading() {
  return <div className="muted pad">불러오는 중…</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return <div className="error-box">{message}</div>;
}

export function Card({ title, actions, children, className = '' }: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-head">
          {title && <h3>{title}</h3>}
          {actions && <div className="card-actions">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Kpi({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: string }) {
  return (
    <div className={`kpi ${tone ?? ''}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

export function Progress({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const cls = value > max ? 'over' : pct >= 80 ? 'near' : '';
  return (
    <div className={`progress ${cls}`} role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}

const LEVEL_LABEL: Record<Advice['level'], string> = { danger: '위험', warn: '주의', info: '제안', good: '양호' };

export function AdviceList({ items }: { items: Advice[] }) {
  if (!items.length) return <p className="muted">특별히 점검할 항목이 없습니다.</p>;
  return (
    <ul className="advice">
      {items.map((a, i) => (
        <li key={i} className={`lv-${a.level}`}>
          <span className={`badge ${a.level}`}>{LEVEL_LABEL[a.level]}</span>
          <div>
            <strong>{a.title}</strong>
            <p>{a.body}</p>
            {a.saving ? <p className="saving">기대 효과: 연 {won(a.saving)}</p> : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function CategorySelect({ categories, value, onChange, allowAuto, allowAll, className }: {
  categories: Category[];
  value: string;
  onChange: (v: string) => void;
  allowAuto?: boolean;
  allowAll?: boolean;
  className?: string;
}) {
  const groups: [string, Category['kind']][] = [['지출', 'expense'], ['수입', 'income'], ['이체 (통계 제외)', 'transfer']];
  return (
    <select className={className} value={value} onChange={(e) => onChange(e.target.value)}>
      {allowAll && <option value="">전체 분류</option>}
      {allowAuto && <option value="">자동 분류</option>}
      {groups.map(([label, kind]) => (
        <optgroup key={kind} label={label}>
          {categories.filter((c) => c.kind === kind).map((c) => (
            <option key={c.name} value={c.name}>{c.name}</option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

export function Modal({ title, onClose, children, wide }: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon" onClick={onClose} aria-label="닫기">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export interface Field {
  name: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'select';
  options?: [string, string][];
  required?: boolean;
  placeholder?: string;
  step?: string;
  hint?: string;
  show?: (values: Record<string, string>) => boolean;
}

/** 필드 정의로 만드는 입력 모달. show 조건에 맞지 않는 필드는 숨기고 제출 값에서도 뺀다. */
export function FormModal({ title, fields, initial, onSubmit, onClose }: {
  title: string;
  fields: Field[];
  initial: Record<string, string>;
  onSubmit: (values: Record<string, string>) => Promise<void>;
  onClose: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(initial);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const visible = fields.filter((f) => !f.show || f.show(values));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(Object.fromEntries(visible.map((f) => [f.name, values[f.name] ?? ''])));
      onClose();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <Modal title={title} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        {visible.map((f) => (
          <label key={f.name} className="field">
            <span>{f.label}{f.required && ' *'}</span>
            {f.type === 'select' ? (
              <select value={values[f.name] ?? ''} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}>
                {f.options?.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            ) : (
              <input
                type={f.type}
                value={values[f.name] ?? ''}
                required={f.required}
                placeholder={f.placeholder}
                step={f.type === 'number' ? f.step ?? 'any' : undefined}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
              />
            )}
            {f.hint && <small className="muted">{f.hint}</small>}
          </label>
        ))}
        {error && <ErrorBox message={error} />}
        <div className="form-actions">
          <button type="button" className="ghost" onClick={onClose}>취소</button>
          <button type="submit" className="primary" disabled={busy}>{busy ? '저장 중…' : '저장'}</button>
        </div>
      </form>
    </Modal>
  );
}

/** 빈 문자열/미입력은 null, 나머지는 숫자로 */
export const num = (s?: string): number | null => (s === undefined || s.trim() === '' ? null : Number(s));
