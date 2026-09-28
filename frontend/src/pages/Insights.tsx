import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { api, qs } from '../api';
import { AdviceList, Card, ErrorBox, Kpi, Loading } from '../components/ui';
import { useApi, useApp } from '../context';
import { man, monthLabel, won } from '../format';
import type { Insights as InsightsData } from '../types';

function AIAdvisor({ month }: { month: string }) {
  const { data: status } = useApi(() => api.get<{ configured: boolean; model: string }>('/insights/ai/status'), []);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const ask = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<{ text: string }>('/insights/ai', { month, question: question.trim() || null });
      setAnswer(r.text);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Claude에게 상담하기" actions={status && <span className="muted small">{status.model}</span>}>
      {status && !status.configured ? (
        <p className="muted">
          서버에 <code>ANTHROPIC_API_KEY</code> 환경변수를 설정하면 Claude가 내 데이터 요약을 보고 맞춤 조언을 해 줍니다.
          README의 'AI 조언 켜기'를 참고하세요.
        </p>
      ) : (
        <>
          <p className="muted small">
            원본 거래내역은 보내지 않고 월별·분류별 합계, 자산 유형별 잔액, 정기 결제 이름 같은 요약만 Anthropic API로 보냅니다.
          </p>
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="비워 두면 이번 달 전체 진단을 받습니다. 예: 1년 안에 1,000만원을 모으려면 어떻게 해야 할까요?"
          />
          <div className="row end">
            <button className="primary" onClick={ask} disabled={busy}>{busy ? '분석 중… (최대 1분)' : '조언 받기'}</button>
          </div>
          {error && <ErrorBox message={error} />}
          {answer && <div className="markdown"><ReactMarkdown>{answer}</ReactMarkdown></div>}
        </>
      )}
    </Card>
  );
}

export default function Insights() {
  const { month, version } = useApp();
  const { data, error } = useApi(() => api.get<InsightsData>(`/insights${qs({ month })}`), [month, version]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading />;
  const { plan, trend } = data;
  const subsTotal = data.subscriptions.reduce((s, x) => s + x.monthly, 0);

  return (
    <div className="stack">
      <Card title={`${monthLabel(data.month)} 진단`}>
        <AdviceList items={data.advice} />
      </Card>

      <Card title="저축 계획">
        {plan.income <= 0 ? (
          <p className="muted">수입 정보가 없어 계획을 세울 수 없습니다. 급여 통장 내역을 가져오거나 설정에서 월 수입을 입력하세요.</p>
        ) : (
          <>
            <p className="muted small">최근 {plan.based_on_months || 1}개월 평균 기준</p>
            <div className="kpis">
              <Kpi label="월 수입" value={man(plan.income)} />
              <Kpi label="월 지출" value={man(plan.expense)} />
              <Kpi label="현재 남는 돈" value={man(plan.surplus)} tone={plan.surplus < plan.target ? 'warn' : 'good'} />
              <Kpi label={`목표 저축 (${plan.target_rate}%)`} value={man(plan.target)} />
            </div>

            {plan.cuts.length > 0 && (
              <>
                <h4>목표를 위해 줄일 지출</h4>
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>분류</th><th className="num">현재 월평균</th><th className="num">절감</th><th className="num">권장 한도</th></tr></thead>
                    <tbody>
                      {plan.cuts.map((c) => (
                        <tr key={c.category}>
                          <td>{c.category}</td>
                          <td className="num">{won(c.current)}</td>
                          <td className="num neg">-{won(c.cut)}</td>
                          <td className="num">{won(c.suggested)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            <h4>매월 {won(plan.monthly_saving)} 저축 배분안</h4>
            {plan.allocation.length === 0 ? (
              <p className="muted">남는 돈이 없습니다. 먼저 지출을 줄여야 합니다.</p>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>어디에</th><th className="num">월 금액</th><th>설명</th></tr></thead>
                  <tbody>
                    {plan.allocation.map((a) => (
                      <tr key={a.name}><td>{a.name}</td><td className="num">{won(a.amount)}</td><td className="muted small">{a.note}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="muted small">
              비상금: 현재 {won(plan.emergency.cash)} / 목표 {won(plan.emergency.target)}.
              이 계획은 일반적인 원칙에 따른 참고용이며 투자 권유가 아닙니다.
            </p>
          </>
        )}
      </Card>

      <Card title={`정기 결제·고정 지출 (월 ${won(subsTotal)})`}>
        {data.subscriptions.length === 0 ? (
          <p className="muted">매달 반복되는 결제를 찾지 못했습니다. 2개월 이상의 내역이 있어야 정확해집니다.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>이름</th><th>분류</th><th className="num">월</th><th className="num">연간</th><th>최근 결제</th></tr></thead>
              <tbody>
                {data.subscriptions.map((s) => (
                  <tr key={s.name + s.category}>
                    <td>{s.name} {s.essential && <span className="tag">필수</span>}</td>
                    <td className="muted">{s.category}</td>
                    <td className="num">{won(s.monthly)}</td>
                    <td className="num">{won(s.annual)}</td>
                    <td className="muted small">{s.last_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="분류별 지출 추이">
        {trend.rows.length === 0 ? <p className="muted">지출 내역이 없습니다.</p> : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>분류</th>{trend.months.map((m) => <th key={m} className="num">{Number(m.slice(5))}월</th>)}<th className="num">변화</th></tr>
              </thead>
              <tbody>
                {trend.rows.map((r) => {
                  const last = r.values[r.values.length - 1];
                  const before = r.values[r.values.length - 2] ?? 0;
                  const diff = last - before;
                  return (
                    <tr key={r.category}>
                      <td>{r.category}</td>
                      {r.values.map((v, i) => <td key={i} className="num">{v ? won(v) : '-'}</td>)}
                      <td className={`num ${diff > 0 ? 'neg' : diff < 0 ? 'pos' : 'muted'}`}>
                        {diff === 0 ? '-' : `${diff > 0 ? '+' : ''}${man(diff)}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <AIAdvisor month={data.month} />
    </div>
  );
}
