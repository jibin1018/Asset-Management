import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useApp } from '../context';
import { monthLabel, thisMonth } from '../format';

export const NAV = [
  { to: '/', label: '대시보드' },
  { to: '/assets', label: '자산' },
  { to: '/transactions', label: '거래내역' },
  { to: '/import', label: '내역 가져오기' },
  { to: '/insights', label: '분석·조언' },
  { to: '/plan', label: '예산·목표' },
  { to: '/settings', label: '설정' },
];

const MONTH_PAGES = ['/', '/transactions', '/insights', '/plan'];

export default function Layout() {
  const { month, setMonth, months } = useApp();
  const { pathname } = useLocation();
  const title = NAV.find((n) => n.to === pathname)?.label ?? '';
  const options = Array.from(new Set([thisMonth(), ...months])).sort().reverse();

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">내 자산 관리</div>
        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <h1>{title}</h1>
          {MONTH_PAGES.includes(pathname) && (
            <label className="month-select">
              기준 월
              <select value={month} onChange={(e) => setMonth(e.target.value)}>
                {options.map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}
              </select>
            </label>
          )}
        </header>
        <div className="content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
