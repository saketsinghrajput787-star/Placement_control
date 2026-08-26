import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './store/authStore';
import { OperationsProvider } from './store/operationsStore';
import { OperationsLayout } from './components/layout/OperationsLayout';
import { LoginPage } from './pages/auth/LoginPage';
import { ControlTowerDashboard } from './pages/coordinator/ControlTowerDashboard';
import { ScheduleManagementPage } from './pages/coordinator/ScheduleManagementPage';
import { DataImportCenter } from './pages/coordinator/DataImportCenter';
import { AuditLogPage } from './pages/coordinator/AuditLogPage';
import { ReplanningPage } from './pages/coordinator/ReplanningPage';
import { DisruptionsPage } from './pages/coordinator/DisruptionsPage';
import { AnalyticsPage } from './pages/coordinator/AnalyticsPage';
import { StudentsPage } from './pages/coordinator/StudentsPage';
import { CompaniesPage } from './pages/coordinator/CompaniesPage';
import { RoomsPanelsPage } from './pages/coordinator/RoomsPanelsPage';
import { CompanyDashboard } from './pages/company/CompanyDashboard';
import { CompanySchedulePage } from './pages/company/CompanySchedulePage';
import { ShortlistPage } from './pages/company/ShortlistPage';
import { StudentDashboard } from './pages/student/StudentDashboard';
import { StudentSchedulePage } from './pages/student/StudentSchedulePage';
import { NotificationsPage } from './pages/student/NotificationsPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode; allowedRole?: string }> = ({
  children,
  allowedRole,
}) => {
  const { isAuthenticated, user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-sand-100 flex items-center justify-center">
        <div className="flex items-center gap-3 text-sand-700 font-semibold text-sm">
          <span className="w-4 h-4 border-2 border-forest-700 border-t-transparent rounded-full animate-spin" />
          Loading Placement Control Tower...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRole && user?.role !== allowedRole) {
    if (user?.role === 'COORDINATOR') return <Navigate to="/coordinator/dashboard" replace />;
    if (user?.role === 'COMPANY') return <Navigate to="/company/dashboard" replace />;
    return <Navigate to="/student/dashboard" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Coordinator Routes */}
      <Route
        path="/coordinator"
        element={
          <ProtectedRoute allowedRole="COORDINATOR">
            <OperationsProvider>
              <OperationsLayout />
            </OperationsProvider>
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/coordinator/dashboard" replace />} />
        <Route path="dashboard" element={<ControlTowerDashboard />} />
        <Route path="schedule" element={<ScheduleManagementPage />} />
        <Route path="import" element={<DataImportCenter />} />
        <Route path="audit" element={<AuditLogPage />} />
        <Route path="replanning" element={<ReplanningPage />} />
        <Route path="disruptions" element={<DisruptionsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="students" element={<StudentsPage />} />
        <Route path="companies" element={<CompaniesPage />} />
        <Route path="resources" element={<RoomsPanelsPage />} />
      </Route>

      {/* Company Routes */}
      <Route
        path="/company"
        element={
          <ProtectedRoute allowedRole="COMPANY">
            <OperationsProvider>
              <OperationsLayout />
            </OperationsProvider>
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/company/dashboard" replace />} />
        <Route path="dashboard" element={<CompanyDashboard />} />
        <Route path="schedule" element={<CompanySchedulePage />} />
        <Route path="shortlist" element={<ShortlistPage />} />
        <Route path="panels" element={<RoomsPanelsPage />} />
      </Route>

      {/* Student Routes */}
      <Route
        path="/student"
        element={
          <ProtectedRoute allowedRole="STUDENT">
            <OperationsProvider>
              <OperationsLayout />
            </OperationsProvider>
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/student/dashboard" replace />} />
        <Route path="dashboard" element={<StudentDashboard />} />
        <Route path="schedule" element={<StudentSchedulePage />} />
        <Route path="notifications" element={<NotificationsPage />} />
      </Route>

      {/* Default fallback */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};
