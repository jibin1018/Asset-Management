import { ChangeEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { Card, ErrorBox } from '../components/ui';
import { useApi, useApp } from '../context';
import { won } from '../format';
import type { Account, ImportMapping, ImportResult, ParsedFile } from '../types';

const COLUMN_FIELDS: { key: keyof ImportMapping; label: string; modes: ('split' | 'single')[] }[] = [
  { key: 'date', label: '날짜', modes: ['split', 'single'] },
  { key: 'description', label: '내용 (가맹점·적요)', modes: ['split', 'single'] },
  { key: 'memo', label: '메모 (선택)', modes: ['split', 'single'] },
  { key: 'withdraw', label: '출금액', modes: ['split'] },
  { key: 'deposit', label: '입금액', modes: ['split'] },
  { key: 'amount', label: '금액', modes: ['single'] },
];

const colName = (i: number) => {
  let s = '';
  let n = i + 1;
  while (n > 0) {
    s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
};

export default function Import() {
  const { version, toast, refreshMonths, bump } = useApp();
  const { data: accounts } = useApi(() => api.get<Account[]>('/accounts'), [version]);
  const [parsed, setParsed] = useState<ParsedFile | null>(null);
  const [accountId, setAccountId] = useState<string>('');
  const [pasteText, setPasteText] = useState('');
  const [preview, setPreview] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!accountId && accounts?.length) setAccountId(String(accounts[0].id));
  }, [accounts, accountId]);

  // 매핑이 바뀔 때마다 서버에서 변환 결과 미리보기
  useEffect(() => {
    if (!parsed || !accountId) return;
    const timer = setTimeout(() => {
      api.post<ImportResult>('/import/commit', { ...parsed, account_id: Number(accountId), dry_run: true })
        .then((r) => { setPreview(r); setError(null); })
        .catch((e: Error) => { setPreview(null); setError(e.message); });
    }, 250);
    return () => clearTimeout(timer);
  }, [parsed, accountId]);

  const load = async (promise: Promise<ParsedFile>) => {
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      setParsed(await promise);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    load(api.post<ParsedFile>('/import/parse', fd));
    e.target.value = '';
  };

  const commit = async () => {
    if (!parsed) return;
    setBusy(true);
    try {
      const r = await api.post<ImportResult>('/import/commit', { ...parsed, account_id: Number(accountId), dry_run: false });
      toast(`${r.added}건을 가져왔습니다.${r.duplicates ? ` (중복 ${r.duplicates}건 제외)` : ''}`);
      setParsed(null);
      setPreview(null);
      await refreshMonths();
      bump();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const update = (patch: Partial<ParsedFile>) => parsed && setParsed({ ...parsed, ...patch });
  const setMap = (key: keyof ImportMapping, value: string) =>
    parsed && update({ mapping: { ...parsed.mapping, [key]: value === '' ? null : Number(value) } });

  const header = parsed ? parsed.rows[parsed.header_index] ?? [] : [];
  const width = parsed ? Math.max(0, ...parsed.rows.slice(parsed.header_index, parsed.header_index + 20).map((r) => r.length)) : 0;
  const columnOptions = Array.from({ length: width }, (_, i) => [String(i), `${colName(i)}: ${header[i] || '(빈 칸)'}`]);

  if (accounts && accounts.length === 0) {
    return (
      <Card title="먼저 자산을 등록하세요">
        <p>거래내역은 어느 계좌·카드의 내역인지 지정해서 가져옵니다. <Link to="/assets">자산 화면</Link>에서 계좌나 카드를 먼저 추가해 주세요.</p>
      </Card>
    );
  }

  return (
    <div className="stack">
      <Card title="1. 파일 올리기">
        <div className="grid2">
          <div>
            <label className="field">
              <span>어느 계좌·카드의 내역인가요?</span>
              <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
                {accounts?.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.institution || '기관 미입력'})</option>)}
              </select>
            </label>
            <label className="field">
              <span>거래내역 파일 (CSV, XLSX, XLS)</span>
              <input type="file" accept=".csv,.txt,.xlsx,.xls,.xlsm" onChange={onFile} disabled={busy} />
            </label>
            <details className="guide">
              <summary>내역 파일은 어디서 받나요?</summary>
              <ul>
                <li><strong>은행</strong>: 인터넷뱅킹 → 조회 → 거래내역조회 → 엑셀 저장</li>
                <li><strong>카드사</strong>: 홈페이지 → 이용내역 조회 → 엑셀 다운로드</li>
                <li><strong>간편결제·인터넷은행</strong>: 앱의 거래내역 메뉴에서 내보내기(이메일로 받기 등)를 지원하면 그 파일을 사용하세요.</li>
                <li>메뉴 이름은 기관마다 다릅니다. 파일 형식이 달라도 아래 2단계에서 컬럼을 직접 지정할 수 있습니다.</li>
              </ul>
            </details>
          </div>
          <div>
            <label className="field">
              <span>또는 엑셀에서 표를 복사해 붙여넣기</span>
              <textarea rows={7} value={pasteText} onChange={(e) => setPasteText(e.target.value)} placeholder={'날짜\t내용\t금액\n2026-09-01\t스타벅스\t4500'} />
            </label>
            <button onClick={() => load(api.post<ParsedFile>('/import/paste', { text: pasteText }))} disabled={busy || !pasteText.trim()}>
              붙여넣은 내용 읽기
            </button>
          </div>
        </div>
      </Card>

      {error && <ErrorBox message={error} />}

      {parsed && (
        <Card title={`2. 컬럼 확인 — ${parsed.file_name} (${parsed.rows.length}행)`}>
          <div className="mapping">
            <label className="field">
              <span>머리글 행 번호</span>
              <input
                type="number"
                min={1}
                max={parsed.rows.length}
                value={parsed.header_index + 1}
                onChange={(e) => update({ header_index: Math.max(0, Math.min(parsed.rows.length - 1, Number(e.target.value) - 1)) })}
              />
            </label>
            <label className="field">
              <span>금액 형식</span>
              <select value={parsed.mode} onChange={(e) => update({ mode: e.target.value as ParsedFile['mode'] })}>
                <option value="split">출금·입금 컬럼이 따로 있음 (은행)</option>
                <option value="single">금액 컬럼 하나 (카드·페이)</option>
              </select>
            </label>
            {parsed.mode === 'single' && (
              <label className="field">
                <span>금액 부호</span>
                <select value={parsed.sign} onChange={(e) => update({ sign: e.target.value as ParsedFile['sign'] })}>
                  <option value="positive_expense">양수 = 지출 (카드 이용내역)</option>
                  <option value="negative_expense">음수 = 지출 (입출금 내역)</option>
                </select>
              </label>
            )}
            {COLUMN_FIELDS.filter((f) => f.modes.includes(parsed.mode)).map((f) => (
              <label key={f.key} className="field">
                <span>{f.label}</span>
                <select value={parsed.mapping[f.key] ?? ''} onChange={(e) => setMap(f.key, e.target.value)}>
                  <option value="">(없음)</option>
                  {columnOptions.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            ))}
          </div>

          <h4>원본 (머리글부터 8행)</h4>
          <div className="table-wrap">
            <table className="table raw">
              <tbody>
                {parsed.rows.slice(parsed.header_index, parsed.header_index + 8).map((r, i) => (
                  <tr key={i} className={i === 0 ? 'header-row' : ''}>
                    <td className="muted small">{parsed.header_index + i + 1}</td>
                    {Array.from({ length: width }, (_, c) => <td key={c}>{r[c] ?? ''}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {parsed && preview && (
        <Card
          title="3. 변환 결과 확인"
          actions={
            <button className="primary" onClick={commit} disabled={busy || preview.total - preview.duplicates === 0}>
              {preview.total - preview.duplicates}건 가져오기
            </button>
          }
        >
          <p className="muted">
            인식 {preview.total}건 · 이미 있는 거래 {preview.duplicates}건 · 날짜/금액이 없어 건너뛴 행 {preview.skipped}건.
            분류는 가져온 뒤 거래내역 화면에서 바꿀 수 있습니다.
          </p>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>날짜</th><th>내용</th><th>분류</th><th className="num">금액</th><th /></tr></thead>
              <tbody>
                {preview.preview.map((t, i) => (
                  <tr key={i} className={t.duplicate ? 'dim' : ''}>
                    <td className="nowrap">{t.date}</td>
                    <td>{t.description}</td>
                    <td>{t.category}</td>
                    <td className={`num nowrap ${t.direction > 0 ? 'pos' : 'neg'}`}>{t.direction > 0 ? '+' : '-'}{won(t.amount)}</td>
                    <td className="muted small">{t.duplicate ? '중복' : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
