import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { AppShell } from './components/layout/AppShell';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { FleetDashboardPage } from './pages/FleetDashboardPage';
import { AircraftDetailPage } from './pages/AircraftDetailPage';
import { ComponentHealthPage } from './pages/ComponentHealthPage';
import { PredictiveQueuePage } from './pages/PredictiveQueuePage';
import { PlanningPage } from './pages/PlanningPage';
import { SparesPage } from './pages/SparesPage';
import { SimulatorPage } from './pages/SimulatorPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30_000,
    },
  },
});

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Telemetry Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 bg-white border border-[#E6E2F0] rounded-[20px] shadow-ap-floating max-w-xl mx-auto my-12 text-center space-y-4 font-sans">
          <div className="inline-flex p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-[12px] text-[#DC2626]">
            <span className="text-2xl">⚠️</span>
          </div>
          <h2 className="text-lg font-bold text-[#3B1D5E]">Telemetry Stream Notice</h2>
          <p className="text-xs text-[#6B5B84]">
            {this.state.error?.message || 'An unexpected state occurred while processing telemetry.'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="px-4 py-2 bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] font-bold rounded-[10px] text-xs transition shadow-ap-mint"
          >
            Reload Cockpit
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const ProtectedLayout: React.FC = () => {
  const { user, token, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#FAFAFE] flex flex-col justify-center items-center font-sans text-[#6B5B84]">
        <div className="h-8 w-8 border-2 border-[#1DE9C0] border-t-transparent rounded-full animate-spin mb-3" />
        <span className="text-xs font-semibold text-[#3B1D5E]">Initializing AeroPulse Session...</span>
      </div>
    );
  }

  // If unauthenticated, redirect to login
  if (!user && !token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <ErrorBoundary>
      <AppShell />
    </ErrorBoundary>
  );
};

export default function App(): React.JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/landing" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />

            <Route path="/" element={<ProtectedLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<FleetDashboardPage />} />
              <Route path="aircraft" element={<AircraftDetailPage />} />
              <Route path="components" element={<ComponentHealthPage />} />
              <Route path="components/:id" element={<ComponentHealthPage />} />
              <Route path="advisories" element={<PredictiveQueuePage />} />
              <Route path="planning" element={<PlanningPage />} />
              <Route path="spares" element={<SparesPage />} />
              <Route path="scenarios" element={<SimulatorPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
