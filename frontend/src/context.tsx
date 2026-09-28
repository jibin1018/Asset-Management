import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { api } from './api';
import { thisMonth } from './format';
import type { Meta } from './types';

interface ToastAction {
  label: string;
  run: () => void;
}

interface Toast {
  id: number;
  message: string;
  action?: ToastAction;
}

interface AppState {
  meta: Meta;
  month: string;
  setMonth: (m: string) => void;
  months: string[];
  refreshMonths: () => Promise<void>;
  /** 데이터가 크게 바뀌었을 때(샘플 로드, 가져오기 등) 모든 화면을 다시 불러오기 위한 버전 */
  version: number;
  bump: () => void;
  toast: (message: string, action?: ToastAction) => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [months, setMonths] = useState<string[]>([]);
  const [month, setMonth] = useState<string>(thisMonth());
  const [version, setVersion] = useState(0);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [error, setError] = useState<string | null>(null);
  const toastId = useRef(0);

  const refreshMonths = useCallback(async () => {
    const list = await api.get<string[]>('/months');
    setMonths(list);
    // 선택한 달에 데이터가 없으면 가장 최근 달로 이동
    setMonth((cur) => (list.length && !list.includes(cur) ? list[0] : cur));
  }, []);

  useEffect(() => {
    Promise.all([api.get<Meta>('/meta'), refreshMonths()])
      .then(([m]) => setMeta(m))
      .catch((e: Error) => setError(e.message));
  }, [refreshMonths]);

  const toast = useCallback((message: string, action?: ToastAction) => {
    const id = ++toastId.current;
    setToasts((t) => [...t, { id, message, action }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), action ? 9000 : 3500);
  }, []);

  const bump = useCallback(() => setVersion((v) => v + 1), []);

  if (error) {
    return (
      <div className="boot-error">
        <h2>서버에 연결할 수 없습니다</h2>
        <p>{error}</p>
        <p className="muted">백엔드가 실행 중인지 확인하세요: <code>uvicorn app.main:app --reload</code></p>
      </div>
    );
  }
  if (!meta) return <div className="boot">불러오는 중…</div>;

  return (
    <AppContext.Provider value={{ meta, month, setMonth, months, refreshMonths, version, bump, toast }}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="toast">
            <span>{t.message}</span>
            {t.action && (
              <button
                onClick={() => {
                  setToasts((all) => all.filter((x) => x.id !== t.id));
                  t.action!.run();
                }}
              >
                {t.action.label}
              </button>
            )}
          </div>
        ))}
      </div>
    </AppContext.Provider>
  );
}

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('AppProvider 밖에서 useApp을 사용했습니다.');
  return ctx;
}

/** 비동기 API 호출 결과를 상태로 관리. deps가 바뀌거나 reload()를 호출하면 다시 불러온다. */
export function useApi<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fn()
      .then((d) => {
        if (alive) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}
