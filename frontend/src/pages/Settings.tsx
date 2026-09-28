import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import { api } from '../api';
import { Card, CategorySelect, ErrorBox, Loading } from '../components/ui';
import { useApi, useApp } from '../context';
import type { Rule, Settings as SettingsData } from '../types';

function GeneralSettings() {
  const { toast, bump } = useApp();
  const { data, error } = useApi(() => api.get<SettingsData>('/settings'), []);
  const [form, setForm] = useState<SettingsData | null>(null);
  useEffect(() => setForm(data), [data]);

  if (error) return <ErrorBox message={error} />;
  if (!form) return <Loading />;

  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      setForm(await api.put<SettingsData>('/settings', form));
      toast('설정을 저장했습니다.');
      bump();
    } catch (err) {
      toast((err as Error).message);
    }
  };
  const set = (k: keyof SettingsData, v: string) => setForm({ ...form, [k]: Number(v) });

  return (
    <Card title="저축 기준">
      <form className="form inline-form" onSubmit={save}>
        <label className="field">
          <span>목표 저축률 (%)</span>
          <input type="number" min={0} max={90} value={form.savings_target_rate} onChange={(e) => set('savings_target_rate', e.target.value)} />
          <small className="muted">수입 중 저축할 비율. 일반적으로 20% 이상을 권합니다.</small>
        </label>
        <label className="field">
          <span>비상금 목표 (월 지출의 몇 배)</span>
          <input type="number" min={0} max={36} step={0.5} value={form.emergency_months} onChange={(e) => set('emergency_months', e.target.value)} />
          <small className="muted">보통 3~6개월 치를 권합니다.</small>
        </label>
        <label className="field">
          <span>월 수입 (원, 선택)</span>
          <input type="number" min={0} value={form.monthly_income} onChange={(e) => set('monthly_income', e.target.value)} />
          <small className="muted">급여 내역을 가져오지 않았을 때 계획 계산에 사용합니다.</small>
        </label>
        <div className="form-actions"><button className="primary" type="submit">저장</button></div>
      </form>
    </Card>
  );
}

function Rules() {
  const { meta, toast, version } = useApp();
  const { data: rules, error, reload } = useApi(() => api.get<Rule[]>('/rules'), [version]);
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState(meta.categories[0].name);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!keyword.trim()) return;
    const r = await api.post<{ updated: number }>('/rules', { keyword: keyword.trim(), category, apply: true });
    toast(`규칙을 추가하고 기존 거래 ${r.updated}건을 바꿨습니다.`);
    setKeyword('');
    reload();
  };

  const reapply = async () => {
    const r = await api.post<{ updated: number }>('/rules/reapply');
    toast(`${r.updated}건을 다시 분류했습니다. (직접 바꾼 분류는 유지)`);
  };

  return (
    <Card title="자동 분류 규칙" actions={<button onClick={reapply}>모든 거래 다시 분류</button>}>
      <p className="muted small">
        거래 내용에 키워드가 들어 있으면 지정한 분류로 바꿉니다. 내 규칙이 기본 규칙보다 우선합니다.
        예: 가족에게 보내는 이체의 받는 분 이름 → '내 계좌 이체' 또는 '경조사·선물'.
      </p>
      <form className="row gap" onSubmit={add}>
        <input placeholder="키워드 (예: 홍길동)" value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        <CategorySelect categories={meta.categories} value={category} onChange={setCategory} />
        <button className="primary" type="submit">추가</button>
      </form>
      {error && <ErrorBox message={error} />}
      {rules && rules.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>키워드</th><th>분류</th><th /></tr></thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>{r.keyword}</td>
                  <td>{r.category}</td>
                  <td className="actions">
                    <button className="link danger" onClick={async () => { await api.del(`/rules/${r.id}`); reload(); }}>삭제</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function DataManagement() {
  const { toast, refreshMonths, bump } = useApp();

  const after = async (message: string) => {
    await refreshMonths();
    bump();
    toast(message);
  };

  const download = async () => {
    const data = await api.get<unknown>('/backup');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    a.download = `asset-backup-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };

  const restore = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !confirm('현재 데이터를 모두 지우고 백업 파일로 바꿀까요?')) return;
    try {
      await api.post('/backup/restore', JSON.parse(await file.text()));
      await after('백업을 복원했습니다.');
    } catch (err) {
      toast(`복원 실패: ${(err as Error).message}`);
    }
  };

  const sample = async () => {
    if (!confirm('현재 데이터를 모두 지우고 샘플 데이터를 불러올까요?')) return;
    await api.post('/sample');
    await after('샘플 데이터를 불러왔습니다.');
  };

  const reset = async () => {
    if (!confirm('모든 자산·거래·목표·규칙을 삭제합니다. 계속할까요?')) return;
    if (!confirm('정말 삭제할까요? 백업하지 않았다면 되돌릴 수 없습니다.')) return;
    await api.post('/reset');
    await after('모든 데이터를 삭제했습니다.');
  };

  return (
    <Card title="데이터 관리">
      <p className="muted small">데이터는 이 서버의 SQLite 파일(backend/data/assets.db)에만 저장됩니다. 주기적으로 백업하세요.</p>
      <div className="row gap wrap">
        <button onClick={download}>백업 파일 내려받기</button>
        <label className="button">
          백업에서 복원
          <input type="file" accept=".json,application/json" onChange={restore} hidden />
        </label>
        <button onClick={sample}>샘플 데이터 불러오기</button>
        <button className="danger" onClick={reset}>모든 데이터 삭제</button>
      </div>
    </Card>
  );
}

export default function Settings() {
  return (
    <div className="stack">
      <GeneralSettings />
      <Rules />
      <DataManagement />
    </div>
  );
}
