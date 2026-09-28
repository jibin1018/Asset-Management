import { useState } from 'react';
import { api } from '../api';
import { Card, ErrorBox, Field, FormModal, Kpi, Loading, num } from '../components/ui';
import { useApi, useApp } from '../context';
import { man, won } from '../format';
import type { Account, Meta } from '../types';

const INVEST = ['stock', 'fund', 'crypto'];

function accountFields(meta: Meta): Field[] {
  return [
    { name: 'name', label: '이름', type: 'text', required: true, placeholder: '예: 주거래 통장, 네이버페이 포인트' },
    {
      name: 'type', label: '유형', type: 'select',
      options: Object.entries(meta.account_types).map(([k, v]): [string, string] => [k, v.label]),
    },
    { name: 'institution', label: '기관', type: 'text', placeholder: '예: 국민은행, 토스, 키움증권' },
    {
      name: 'balance', label: '잔액 · 평가금액 (원)', type: 'number', required: true,
      hint: '신용카드·대출은 앞으로 갚아야 할 금액을 입력하세요.',
    },
    { name: 'principal', label: '투자 원금 (원)', type: 'number', show: (v) => INVEST.includes(v.type), hint: '입력하면 수익률을 계산합니다.' },
    { name: 'interest_rate', label: '연 이율 (%)', type: 'number', step: '0.01', show: (v) => ['bank', 'pay', 'saving', 'loan'].includes(v.type) },
    { name: 'monthly_payment', label: '월 납입·상환액 (원)', type: 'number', show: (v) => ['saving', 'loan'].includes(v.type) },
    { name: 'expire_date', label: '소멸 예정일', type: 'date', show: (v) => v.type === 'point' },
    { name: 'note', label: '메모', type: 'text' },
  ];
}

function toPayload(v: Record<string, string>) {
  return {
    name: v.name.trim(),
    type: v.type,
    institution: v.institution ?? '',
    balance: Math.round(Number(v.balance || 0)),
    principal: num(v.principal),
    interest_rate: num(v.interest_rate),
    monthly_payment: num(v.monthly_payment),
    expire_date: v.expire_date || null,
    note: v.note ?? '',
  };
}

const toForm = (a?: Account): Record<string, string> => ({
  name: a?.name ?? '',
  type: a?.type ?? 'bank',
  institution: a?.institution ?? '',
  balance: a ? String(a.balance) : '',
  principal: a?.principal?.toString() ?? '',
  interest_rate: a?.interest_rate?.toString() ?? '',
  monthly_payment: a?.monthly_payment?.toString() ?? '',
  expire_date: a?.expire_date ?? '',
  note: a?.note ?? '',
});

function extraInfo(a: Account): string {
  const parts: string[] = [];
  if (a.principal) {
    const ret = ((a.balance - a.principal) / a.principal) * 100;
    parts.push(`원금 ${man(a.principal)} · 수익률 ${ret >= 0 ? '+' : ''}${ret.toFixed(1)}%`);
  }
  if (a.interest_rate !== null) parts.push(`연 ${a.interest_rate}%`);
  if (a.monthly_payment) parts.push(`월 ${man(a.monthly_payment)}`);
  if (a.expire_date) parts.push(`${a.expire_date} 소멸`);
  if (a.note) parts.push(a.note);
  return parts.join(' · ');
}

function BalanceInput({ account, onSaved }: { account: Account; onSaved: () => void }) {
  const { toast } = useApp();
  const [value, setValue] = useState(String(account.balance));
  const save = async () => {
    const n = Math.round(Number(value));
    if (Number.isNaN(n) || n === account.balance) return setValue(String(account.balance));
    try {
      await api.patch(`/accounts/${account.id}/balance`, { balance: n });
      toast(`'${account.name}' 잔액을 ${won(n)}으로 바꿨습니다.`);
      onSaved();
    } catch (e) {
      toast((e as Error).message);
    }
  };
  return (
    <input
      className="balance-input"
      type="number"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={save}
      onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
      aria-label={`${account.name} 잔액`}
    />
  );
}

export default function Assets() {
  const { meta, version } = useApp();
  const { data: accounts, error, reload } = useApi(() => api.get<Account[]>('/accounts'), [version]);
  const [editing, setEditing] = useState<Account | 'new' | null>(null);

  if (error) return <ErrorBox message={error} />;
  if (!accounts) return <Loading />;

  const types = meta.account_types;
  const assets = accounts.filter((a) => !types[a.type]?.liability).reduce((s, a) => s + a.balance, 0);
  const debts = accounts.filter((a) => types[a.type]?.liability).reduce((s, a) => s + Math.abs(a.balance), 0);

  const remove = async (a: Account) => {
    if (!confirm(`'${a.name}'을(를) 삭제할까요? 이 자산에 연결된 거래내역도 함께 삭제됩니다.`)) return;
    await api.del(`/accounts/${a.id}`);
    reload();
  };

  const submit = async (v: Record<string, string>) => {
    const payload = toPayload(v);
    if (editing === 'new') await api.post('/accounts', payload);
    else if (editing) await api.put(`/accounts/${editing.id}`, payload);
    reload();
  };

  return (
    <div className="stack">
      <div className="kpis">
        <Kpi label="총자산" value={man(assets)} />
        <Kpi label="총부채" value={man(debts)} tone={debts > 0 ? 'warn' : ''} />
        <Kpi label="순자산" value={man(assets - debts)} />
      </div>

      <div className="row between">
        <p className="muted">잔액 칸을 바로 수정할 수 있습니다. 거래내역을 가져와도 잔액은 자동으로 바뀌지 않으니 주기적으로 맞춰 주세요.</p>
        <button className="primary" onClick={() => setEditing('new')}>+ 자산 추가</button>
      </div>

      {accounts.length === 0 && (
        <Card>
          <p>등록된 자산이 없습니다. 은행 계좌, 간편결제 머니(토스·카카오페이·네이버페이), 포인트, 증권 계좌, 카드, 대출을 하나씩 추가해 보세요.</p>
        </Card>
      )}

      {Object.entries(types).map(([key, t]) => {
        const list = accounts.filter((a) => a.type === key);
        if (!list.length) return null;
        const total = list.reduce((s, a) => s + a.balance, 0);
        return (
          <Card key={key} title={<>{t.label} <span className="muted small">{man(total)}</span></>}>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>이름</th><th>기관</th><th className="num">잔액</th><th>상세</th><th>수정일</th><th /></tr>
                </thead>
                <tbody>
                  {list.map((a) => (
                    <tr key={a.id}>
                      <td>{a.name}</td>
                      <td className="muted">{a.institution}</td>
                      <td className="num"><BalanceInput key={a.balance} account={a} onSaved={reload} /></td>
                      <td className="muted small">{extraInfo(a)}</td>
                      <td className="muted small">{a.updated_at.slice(0, 10)}</td>
                      <td className="actions">
                        <button className="link" onClick={() => setEditing(a)}>수정</button>
                        <button className="link danger" onClick={() => remove(a)}>삭제</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        );
      })}

      {editing && (
        <FormModal
          title={editing === 'new' ? '자산 추가' : '자산 수정'}
          fields={accountFields(meta)}
          initial={toForm(editing === 'new' ? undefined : editing)}
          onSubmit={submit}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}
