import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { RiskMapPage } from './pages/RiskMapPage'
import { GetHelpPage } from './pages/GetHelpPage'
import { CoordinatorPage } from './pages/CoordinatorPage'
import { AlertsPage } from './pages/AlertsPage'
import { StatusPage } from './pages/StatusPage'
import { LoginPage } from './pages/LoginPage'
import './i18n'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 mins
      retry: 1,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<RiskMapPage />} />
            <Route path="help" element={<GetHelpPage />} />
            <Route path="coordinator" element={<CoordinatorPage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="status" element={<StatusPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
