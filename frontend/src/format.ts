export const won = (n: number | null | undefined) => `${Math.round(n ?? 0).toLocaleString('ko-KR')}원`;

/** 큰 금액을 "1,234만원", "3.2억원"처럼 짧게 */
export function man(n: number | null | undefined): string {
  const v = n ?? 0;
  const a = Math.abs(v);
  if (a >= 1e8) return `${(v / 1e8).toFixed(1).replace(/\.0$/, '')}억원`;
  if (a >= 1e4) return `${Math.round(v / 1e4).toLocaleString('ko-KR')}만원`;
  return won(v);
}

export const monthLabel = (ym: string) => `${ym.slice(0, 4)}년 ${Number(ym.slice(5, 7))}월`;

export const thisMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

export const today = () => {
  const d = new Date();
  return `${thisMonth()}-${String(d.getDate()).padStart(2, '0')}`;
};

/** 지점번호 등 숫자·기호를 지운 가맹점 이름 (분류 규칙 키워드 제안용) */
export const merchantKey = (desc: string) =>
  desc.replace(/[0-9*#_/()[\]\-.]+/g, ' ').replace(/\s+/g, ' ').trim();

export const PALETTE = [
  '#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#64748b', '#84cc16',
];
