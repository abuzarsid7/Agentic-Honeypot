import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SessionProvider } from './SessionContext';
import Layout from './components/Layout';
import Hero from './pages/Hero';
import CommandCenter from './pages/CommandCenter';
import LiveSessions from './pages/LiveSessions';
import Investigation from './pages/Investigation';
import Intelligence from './pages/Intelligence';
import Explainability from './pages/Explainability';
import Telemetry from './pages/Telemetry';
import Admin from './pages/Admin';

function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Hero />} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<CommandCenter />} />
            <Route path="/sessions" element={<LiveSessions />} />
            <Route path="/investigate" element={<Investigation />} />
            <Route path="/intelligence" element={<Intelligence />} />
            <Route path="/explainability" element={<Explainability />} />
            <Route path="/telemetry" element={<Telemetry />} />
            <Route path="/admin" element={<Admin />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SessionProvider>
  );
}

export default App;
