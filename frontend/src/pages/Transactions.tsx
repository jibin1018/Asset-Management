import { FormEvent, useState } from 'react';
import { api, qs } from '../api';
import { Card, CategorySelect, ErrorBox, Field, FormModal, Loading } from '../components/ui';
import { useApi, useApp } from '../context';
import { merchantKey, monthLabel, today, won } from '../format';
import type { Account, Transaction, TransactionList } from '../types';

interface Filters {
  allPeriods: boolean;
  account_id: string;
  category: string;
  kind: string;
  q: string;
}

const KIND_LABEL: Record<string, string> = { expense: '지출', income: '수입', transfer: '이체' };

export default function Transactions() {
  const { meta, month, version, toast, refreshMonths } = useApp();
  const [filters, setFilters] = useState<Filters>({ allPeriods: false, account_id: '', category: '', kind: '', q: '' });
  const [search, setSearch] = useState('');
  const [adding, setAdding] = useState(false);

  const { data: accounts } = useApi(() => api.get<Account[]>('/accounts'), [version]);
  const { data, error, reload } = useApi(
    () => api.get<TransactionList>(`/transactions${qs({
      month: filters.allPeriods ? undefined : month,
      account_id: filters.account_id,
      category: filters.category,
      kind: filters.kind,
      q: filters.q,
      limit: 1000,
    })}`),
    [month, version, filters],
  );

  const accountName = (id: number) => accounts?.find((a) => a.id === id)?.name ?? '-';
  const set = (patch: Partial<Filters>) => setFilters((f) => ({ ...f, ...patch }));

  const changeCategory = async (tx: Transaction, category: string) => {
    try {
      await api.patch(`/transactions/${tx.id}`, { category });
      reload();
      const keyword = merchantKey(tx.description);
      if (!keyword) return;
      toast(`'${category}'(으)로 바꿨습니다.`, {
        label: '비슷한 내역도 모두',
        run: async () => {
          const kw = window.prompt(`이 키워드가 들어간 거래를 앞으로도 '${category}'(으)로 분류합니다.`, keyword);
          if (!kw?.trim()) return;
          const res = await api.post<{ updated: number }>('/rules', { keyword: kw.trim(), category, apply: true });
          toast(`규칙을 저장하고 기존 거래 ${res.updated}건을 바꿨습니다.`);
          reload();
        },
      });
    } catch (e) {
      toast((e as Error).message);
    }
  };

  const remove = async (tx: Transaction) => {
    if (!confirm(`${tx.date} ${tx.description} ${won(tx.amount)} 거래를 삭제할까요?`)) return;
    await api.del(`/transactions/${tx.id}`);
    reload();
  };

  const removeFiltered = async () => {
    if (!data?.items.length) return;
    if (!confirm(`지금 보이는 거래 ${data.items.length}건을 모두 삭제할까요? 되돌릴 수 없습니다.`)) return;
    await api.post('/transactions/bulk-delete', { ids: data.items.map((t) => t.id) });
    toast(`${data.items.length}건을 삭제했습니다.`);
    await refreshMonths();
    reload();
  };

  const addFields: Field[] = [
    { name: 'date', label: '날짜', type: 'date', required: true },
    { name: 'account_id', label: '계좌', type: 'select', options: (accounts ?? []).map((a): [string, string] => [String(a.id), a.name]) },
    { name: 'direction', label: '구분', type: 'select', options: [['-1', '출금 (지출·이체)'], ['1', '입금 (수입)']] },
    { name: 'amount', label: '금액 (원)', type: 'number', required: true },
    { name: 'description', label: '내용', type: 'text', placeholder: '예: 스타벅스 역삼점' },
    {
      name: 'category', label: '분류', type: 'select',
      options: [['', '자동 분류'], ...meta.categories.map((c) => [c.name, `${c.name} (${KIND_LABEL[c.kind]})`] as [string, string])],
    },
  ];

  const submitAdd = async (v: Record<string, string>) => {
    await api.post('/transactions', {
      date: v.date,
      account_id: Number(v.account_id),
      direction: Number(v.direction),
      amount: Math.round(Number(v.amount)),
      description: v.description,
      category: v.category || null,
    });
    await refreshMonths();
    reload();
  };

  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    set({ q: search.trim() });
  };

  return (
    <div className="stack">
      <Card>
        <div className="filters">
          <label className="check">
            <input type="checkbox" checked={filters.allPeriods} onChange={(e) => set({ allPeriods: e.target.checked })} />
            전체 기간
          </label>
          <select value={filters.account_id} onChange={(e) => set({ account_id: e.target.value })}>
            <option value="">전체 계좌</option>
            {accounts?.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
          <CategorySelect categories={meta.categories} value={filters.category} onChange={(category) => set({ category })} allowAll />
          <select value={filters.kind} onChange={(e) => set({ kind: e.target.value })}>
            <option value="">수입·지출·이체</option>
            <option value="expense">지출</option>
            <option value="income">수입</option>
            <option value="transfer">이체</option>
          </select>
          <form onSubmit={onSearch} className="search">
            <input type="search" placeholder="내용 검색" value={search} onChange={(e) => setSearch(e.target.value)} />
          </form>
          <div className="spacer" />
          <button className="primary" onClick={() => setAdding(true)} disabled={!accounts?.length}>+ 직접 입력</button>
        </div>
      </Card>

      {error && <ErrorBox message={error} />}
      {!data ? <Loading /> : (
        <Card
          title={`${filters.allPeriods ? '전체 기간' : monthLabel(month)} · ${data.total.toLocaleString()}건`}
          actions={
            <div className="sums">
              <span className="pos">수입 {won(data.income)}</span>
              <span className="neg">지출 {won(data.expense)}</span>
              <span className="muted">이체 {won(data.transfer)}</span>
            </div>
          }
        >
          {data.items.length === 0 ? (
            <p className="muted">거래가 없습니다. '내역 가져오기'에서 은행·카드 내역 파일을 올려 보세요.</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>날짜</th><th>계좌</th><th>내용</th><th>분류</th><th className="num">금액</th><th /></tr>
                </thead>
                <tbody>
                  {data.items.map((t) => (
                    <tr key={t.id} className={t.kind === 'transfer' ? 'dim' : ''}>
                      <td className="nowrap">{t.date}</td>
                      <td className="muted small">{accountName(t.account_id)}</td>
                      <td>{t.description}</td>
                      <td>
                        <CategorySelect
                          className="compact"
                          categories={meta.categories}
                          value={t.category}
                          onChange={(c) => changeCategory(t, c)}
                        />
                      </td>
                      <td className={`num nowrap ${t.direction > 0 ? 'pos' : 'neg'}`}>
                        {t.direction > 0 ? '+' : '-'}{won(t.amount)}
                      </td>
                      <td className="actions"><button className="link danger" onClick={() => remove(t)}>삭제</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {data.total > data.items.length && (
                <p className="muted small">최근 {data.items.length}건만 표시합니다. 필터로 범위를 좁혀 보세요.</p>
              )}
            </div>
          )}
          {data.items.length > 0 && (
            <div className="row end">
              <button className="link danger" onClick={removeFiltered}>보이는 내역 모두 삭제</button>
            </div>
          )}
        </Card>
      )}

      {adding && (
        <FormModal
          title="거래 직접 입력"
          fields={addFields}
          initial={{ date: today(), account_id: String(accounts?.[0]?.id ?? ''), direction: '-1', amount: '', description: '', category: '' }}
          onSubmit={submitAdd}
          onClose={() => setAdding(false)}
        />
      )}
    </div>
  );
}
