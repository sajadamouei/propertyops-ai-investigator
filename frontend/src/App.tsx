import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/common/AppShell'
import { LabPage } from './pages/LabPage'
import { OperationsPage } from './pages/OperationsPage'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/operations" replace />} />
        <Route path="/operations" element={<OperationsPage />} />
        <Route path="/lab" element={<LabPage />} />
        <Route path="*" element={<Navigate to="/operations" replace />} />
      </Routes>
    </AppShell>
  )
}
