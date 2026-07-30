import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import GroupsList from './pages/GroupsList'
import CreateGroup from './pages/CreateGroup'
import GroupDetail from './pages/GroupDetail'
import AddExpense from './pages/AddExpense'
import ShareView from './pages/ShareView'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/share/:token" element={<ShareView />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <GroupsList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/groups/new"
            element={
              <ProtectedRoute>
                <CreateGroup />
              </ProtectedRoute>
            }
          />
          <Route
            path="/groups/:groupId"
            element={
              <ProtectedRoute>
                <GroupDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/groups/:groupId/expenses/new"
            element={
              <ProtectedRoute>
                <AddExpense />
              </ProtectedRoute>
            }
          />
          <Route
            path="/groups/:groupId/expenses/:expenseId/edit"
            element={
              <ProtectedRoute>
                <AddExpense />
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
