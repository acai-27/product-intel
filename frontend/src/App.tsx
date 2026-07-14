import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { MainLayout } from './layouts/MainLayout';
import { DashboardSkeleton } from './components/ui/Skeleton';
import './App.css';

const DashboardPage = React.lazy(() => import('./pages/DashboardPage'));
const WorkspacePage = React.lazy(() => import('./pages/WorkspacePage'));
const PredictionsPage = React.lazy(() => import('./pages/PredictionsPage'));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage'));

const PageLoader = () => (
  <div style={{ padding: 'var(--space-8)' }}>
    <DashboardSkeleton />
  </div>
);

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="workspace" element={<WorkspacePage />} />
              <Route path="predictions" element={<PredictionsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
