import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, qs } from '../api';
import { Donut, IncomeExpenseBars, NetWorthLine, Slice } from '../components/charts';
import { AdviceList, Card, ErrorBox, Kpi, Loading } from '../components/ui';
import { useApi, useApp } from '../context';
import { man, monthLabel, PALETTE, won } from '../format';
import type { Dashboard as DashboardData } from '../types';

function categorySlices(byCat: Record<string, number>, top = 7): Slice[] {
  const entries = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
  const head = entries.slice(0, top);
  const rest = entries.slice(top).reduce((a, [, v]) => a + v, 0);
  if (rest > 0) head.push(['그 외', rest]);
  return head.map(([label, value], i) => ({ label, value, color: PALETTE[i % PALETTE.length] }));
}

function Onboarding() {
  const { refreshMonths, bump, toast } = useApp();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const loadSample = async () => {
    setBusy(true);
    try {
      await api.post('/sample');
      await refreshMonths();
      bump();
      toast('샘플 데이터를 불러왔습니다. 설정에서 언제든 지울 수 있습니다.');
    } catch (e) {
      toast((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <Card className="onboarding">
      <h2>자산 관리를 시작해 볼까요?</h2>
      <ol>
        <li><strong>자산 등록</strong> — 은행 계좌, 간편결제 머니, 포인트, 주식, 대출까지 잔액을 입력합니다.</li>
        <li><strong>거래내역 가져오기</strong> — 은행·카드사·페이 앱에서 내려받은 엑셀/CSV를 올리면 자동으로 분류합니다.</li>
        <li><strong>분석·조언 확인</strong> — 지출 패턴, 정기 결제, 비상금, 저축 계획을 점검합니다.</li>
      </ol>
      <div className="row gap">
        <button className="primary" onClick={() => navigate('/assets')}>자산 등록하기</button>
        <button onClick={() => navigate('/import')}>거래내역 가져오기</button>
        <button className="ghost" onClick={loadSample} disabled={busy}>{busy ? '불러오는 중…' : '샘플 데이터로 둘러보기'}</button>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const { month, version } = useApp();
  const { data, error } = useApi(() => api.get<DashboardData>(`/dashboard${qs({ month })}`), [month, version]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading />;

  const { net_worth: nw, summary: s, prev_summary: prev } = data;
  const empty = nw.assets === 0 && nw.debts === 0 && data.monthly.every((m) => !m.income && !m.expense);
  if (empty) return <Onboarding />;

  const expenseDiff = prev.expense > 0 ? Math.round(((s.expense - prev.expense) / prev.expense) * 100) : null;
  const rateTone = data.savings_rate === null ? '' : data.savings_rate >= data.target_rate ? 'good' : data.savings_rate < 0 ? 'danger' : 'warn';

  return (
    <div className="stack">
      <div className="kpis">
        <Kpi label="순자산" value={man(nw.net)} sub={`자산 ${man(nw.assets)} · 부채 ${man(nw.debts)}`} />
        <Kpi label={`${monthLabel(data.month)} 수입`} value={won(s.income)} />
        <Kpi
          label={`${monthLabel(data.month)} 지출`}
          value={won(s.expense)}
          sub={expenseDiff === null ? undefined : `지난달 대비 ${expenseDiff >= 0 ? '+' : ''}${expenseDiff}%`}
          tone={expenseDiff !== null && expenseDiff > 10 ? 'warn' : ''}
        />
        <Kpi
          label="저축률"
          value={data.savings_rate === null ? '-' : `${data.savings_rate}%`}
          sub={`목표 ${data.target_rate}%`}
          tone={rateTone}
        />
      </div>

      <div className="grid2">
        <Card title="자산 구성">
          <Donut data={data.groups.map((g) => ({ label: g.label, value: g.value, color: g.color }))} center={man(nw.assets)} />
        </Card>
        <Card title={`${monthLabel(data.month)} 지출 분류`}>
          <Donut data={categorySlices(s.by_category)} center={man(s.expense)} />
        </Card>
      </div>

      <Card title="최근 6개월 수입·지출">
        <IncomeExpenseBars data={data.monthly} />
      </Card>

      {data.snapshots.length >= 2 && (
        <Card title="순자산 변화">
          <NetWorthLine data={data.snapshots} />
        </Card>
      )}

      <Card title="핵심 점검 사항" actions={<Link to="/insights">전체 분석 보기 →</Link>}>
        <AdviceList items={data.advice} />
      </Card>
    </div>
  );
}
