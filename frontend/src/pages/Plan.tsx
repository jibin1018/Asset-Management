import { useEffect, useState } from 'react';
import { api, qs } from '../api';
import { Card, ErrorBox, Field, FormModal, Loading, Progress } from '../components/ui';
import { useApi, useApp } from '../context';
import { man, monthLabel, won } from '../format';
import type { Account, BudgetRow, GoalStatus } from '../types';

function Budgets() {
  const { month, version, toast } = useApp();
  const { data, error, reload, setData } = useApi(
    () => api.get<{ month: string; rows: BudgetRow[] }>(`/budgets${qs({ month })}`),
    [month, version],
  );
  const [draft, setDraft] = useState<Record<string, string>>({});

  useEffect(() => {
    if (data) setDraft(Object.fromEntries(data.rows.map((r) => [r.category, r.limit ? String(r.limit) : ''])));
  }, [data]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading />;

  const dirty = data.rows.some((r) => (r.limit ? String(r.limit) : '') !== (draft[r.category] ?? ''));

  const save = async () => {
    const body = Object.fromEntries(data.rows.map((r) => {
      const v = (draft[r.category] ?? '').trim();
      return [r.category, v === '' ? null : Math.round(Number(v))];
    }));
    await api.put('/budgets', body);
    toast('예산을 저장했습니다.');
    reload();
  };

  const suggest = async () => {
    setData(await api.post<{ month: string; rows: BudgetRow[] }>(`/budgets/suggest${qs({ month })}`));
    toast('최근 평균 지출로 예산을 채웠습니다. 선택 지출은 15% 낮게 잡았습니다.');
  };

  const rows = data.rows.filter((r) => r.limit || r.spent || r.average);
  const totalLimit = data.rows.reduce((s, r) => s + (r.limit ?? 0), 0);
  const totalSpent = data.rows.filter((r) => r.limit).reduce((s, r) => s + r.spent, 0);

  return (
    <Card
      title={`${monthLabel(data.month)} 예산`}
      actions={
        <>
          <button onClick={suggest}>평균으로 자동 설정</button>
          <button className="primary" onClick={save} disabled={!dirty}>저장</button>
        </>
      }
    >
      {totalLimit > 0 && (
        <div className="budget-total">
          <span>예산 {won(totalLimit)} 중 {won(totalSpent)} 사용</span>
          <Progress value={totalSpent} max={totalLimit} />
        </div>
      )}
      {rows.length === 0 && <p className="muted">지출 내역이 없습니다. 아래 표에서 직접 예산을 입력할 수도 있습니다.</p>}
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>분류</th><th className="num">3개월 평균</th><th className="num">이번 달</th><th className="num">월 예산</th><th>사용률</th></tr></thead>
          <tbody>
            {(rows.length ? rows : data.rows).map((r) => {
              const limit = Number(draft[r.category] || 0);
              return (
                <tr key={r.category}>
                  <td>{r.category} {r.bucket === 'want' && <span className="tag">선택</span>}</td>
                  <td className="num muted">{r.average ? won(r.average) : '-'}</td>
                  <td className="num">{r.spent ? won(r.spent) : '-'}</td>
                  <td className="num">
                    <input
                      className="budget-input"
                      type="number"
                      min={0}
                      step={10000}
                      value={draft[r.category] ?? ''}
                      placeholder="없음"
                      onChange={(e) => setDraft({ ...draft, [r.category]: e.target.value })}
                    />
                  </td>
                  <td className="progress-cell">{limit > 0 && <Progress value={r.spent} max={limit} />}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Goals() {
  const { version } = useApp();
  const { data: goals, error, reload } = useApi(() => api.get<GoalStatus[]>('/goals'), [version]);
  const { data: accounts } = useApi(() => api.get<Account[]>('/accounts'), [version]);
  const [editing, setEditing] = useState<GoalStatus | 'new' | null>(null);

  if (error) return <ErrorBox message={error} />;
  if (!goals) return <Loading />;

  const fields: Field[] = [
    { name: 'name', label: '목표 이름', type: 'text', required: true, placeholder: '예: 비상금, 전세 보증금, 여행' },
    { name: 'target', label: '목표 금액 (원)', type: 'number', required: true },
    {
      name: 'account_id', label: '연결 계좌', type: 'select',
      options: [['', '연결 안 함'], ...(accounts ?? []).map((a): [string, string] => [String(a.id), `${a.name} (${man(a.balance)})`])],
      hint: '계좌를 연결하면 그 계좌 잔액을 현재 금액으로 사용합니다.',
    },
    { name: 'current', label: '현재 모은 금액 (원)', type: 'number', show: (v) => !v.account_id },
    { name: 'deadline', label: '목표 날짜', type: 'date' },
  ];

  const initial = (g?: GoalStatus): Record<string, string> => ({
    name: g?.name ?? '',
    target: g ? String(g.target) : '',
    account_id: g?.account_id ? String(g.account_id) : '',
    current: g ? String(g.current) : '0',
    deadline: g?.deadline ?? '',
  });

  const submit = async (v: Record<string, string>) => {
    const body = {
      name: v.name.trim(),
      target: Math.round(Number(v.target)),
      current: Math.round(Number(v.current || 0)),
      deadline: v.deadline || null,
      account_id: v.account_id ? Number(v.account_id) : null,
    };
    if (editing === 'new') await api.post('/goals', body);
    else if (editing) await api.put(`/goals/${editing.id}`, body);
    reload();
  };

  const remove = async (g: GoalStatus) => {
    if (!confirm(`'${g.name}' 목표를 삭제할까요?`)) return;
    await api.del(`/goals/${g.id}`);
    reload();
  };

  return (
    <Card title="저축 목표" actions={<button className="primary" onClick={() => setEditing('new')}>+ 목표 추가</button>}>
      {goals.length === 0 && <p className="muted">비상금, 여행, 내 집 마련처럼 모으고 싶은 목표를 추가하면 매달 얼마를 모아야 하는지 계산합니다.</p>}
      <div className="goals">
        {goals.map((g) => (
          <div key={g.id} className="goal">
            <div className="row between">
              <strong>{g.name}</strong>
              <span>
                <button className="link" onClick={() => setEditing(g)}>수정</button>
                <button className="link danger" onClick={() => remove(g)}>삭제</button>
              </span>
            </div>
            <Progress value={g.effective_current} max={g.target} />
            <div className="row between small">
              <span>{man(g.effective_current)} / {man(g.target)} ({g.progress}%)</span>
              <span className="muted">
                {g.monthly_needed !== null
                  ? `${g.deadline}까지 월 ${won(g.monthly_needed)}`
                  : '기한 없음'}
              </span>
            </div>
          </div>
        ))}
      </div>
      {editing && (
        <FormModal
          title={editing === 'new' ? '목표 추가' : '목표 수정'}
          fields={fields}
          initial={initial(editing === 'new' ? undefined : editing)}
          onSubmit={submit}
          onClose={() => setEditing(null)}
        />
      )}
    </Card>
  );
}

export default function Plan() {
  return (
    <div className="stack">
      <Goals />
      <Budgets />
    </div>
  );
}
