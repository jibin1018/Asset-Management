import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { man, won } from '../format';

export interface Slice {
  label: string;
  value: number;
  color: string;
}

export function Donut({ data, center }: { data: Slice[]; center?: string }) {
  const total = data.reduce((a, b) => a + b.value, 0);
  if (total <= 0) return <p className="muted">표시할 데이터가 없습니다.</p>;
  return (
    <div className="donut">
      <div className="donut-chart">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="label" innerRadius={62} outerRadius={92} paddingAngle={1} stroke="none">
              {data.map((d) => <Cell key={d.label} fill={d.color} />)}
            </Pie>
            <Tooltip formatter={(v) => won(Number(v))} />
          </PieChart>
        </ResponsiveContainer>
        {center && <div className="donut-center">{center}</div>}
      </div>
      <ul className="legend">
        {data.map((d) => (
          <li key={d.label}>
            <span className="dot" style={{ background: d.color }} />
            <span className="legend-label">{d.label}</span>
            <span className="legend-value">{man(d.value)} · {Math.round((d.value / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const axisStyle = { fontSize: 12, fill: 'var(--muted)' };

export function IncomeExpenseBars({ data }: { data: { month: string; income: number; expense: number }[] }) {
  const rows = data.map((d) => ({ ...d, label: `${Number(d.month.slice(5))}월` }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--line)" />
        <XAxis dataKey="label" tickLine={false} axisLine={false} tick={axisStyle} />
        <YAxis tickFormatter={(v) => man(Number(v))} width={72} tickLine={false} axisLine={false} tick={axisStyle} />
        <Tooltip formatter={(v) => won(Number(v))} />
        <Legend />
        <Bar dataKey="income" name="수입" fill="#10b981" radius={[4, 4, 0, 0]} />
        <Bar dataKey="expense" name="지출" fill="#ef4444" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function NetWorthLine({ data }: { data: { date: string; net: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--line)" />
        <XAxis dataKey="date" tickFormatter={(d) => String(d).slice(5)} tickLine={false} axisLine={false} tick={axisStyle} />
        <YAxis tickFormatter={(v) => man(Number(v))} width={72} tickLine={false} axisLine={false} tick={axisStyle} domain={['auto', 'auto']} />
        <Tooltip formatter={(v) => won(Number(v))} />
        <Line type="monotone" dataKey="net" name="순자산" stroke="#3b82f6" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
