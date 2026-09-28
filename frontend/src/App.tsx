import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Assets from './pages/Assets';
import Dashboard from './pages/Dashboard';
import Import from './pages/Import';
import Insights from './pages/Insights';
import Plan from './pages/Plan';
import Settings from './pages/Settings';
import Transactions from './pages/Transactions';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="assets" element={<Assets />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="import" element={<Import />} />
        <Route path="insights" element={<Insights />} />
        <Route path="plan" element={<Plan />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
