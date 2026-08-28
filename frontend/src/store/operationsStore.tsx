import React, { createContext, useContext, useState, useEffect } from 'react';
import { ScheduleVersion, ConflictItem, Interview, ReplanningResult, AnalyticsDashboard, NotificationItem } from '../types';
import { apiClient } from '../api/client';
import { useAuth } from './authStore';

interface OperationsContextType {
  scheduleVersion: ScheduleVersion | null;
  analytics: AnalyticsDashboard | null;
  conflicts: ConflictItem[];
  notifications: NotificationItem[];
  selectedInterview: Interview | null;
  isCopilotOpen: boolean;
  isDisruptionModalOpen: boolean;
  isDiffModalOpen: boolean;
  isHistoryDrawerOpen: boolean;
  replanningResult: ReplanningResult | null;
  isLoading: boolean;
  error: string | null;
  isLiveConnected: boolean;
  lastSyncTime: string;
  liveBannerMessage: string | null;
  syncCounter: number;

  triggerSync: () => void;
  loadDashboardData: () => Promise<void>;
  generateSchedule: () => Promise<void>;
  resetSchedule: () => Promise<void>;
  reinstateInterview: (studentId: string, companyId: string) => Promise<void>;
  setSelectedInterview: (interview: Interview | null) => void;
  setIsCopilotOpen: (open: boolean) => void;
  setIsDisruptionModalOpen: (open: boolean) => void;
  setIsDiffModalOpen: (open: boolean) => void;
  setIsHistoryDrawerOpen: (open: boolean) => void;
  setReplanningResult: (result: ReplanningResult | null) => void;
  setLiveBannerMessage: (msg: string | null) => void;
  applyReplanningStrategy: (replanningRunId: string, strategyType: string) => Promise<void>;
  markNotificationAsRead: (id: string) => Promise<void>;
}

const OperationsContext = createContext<OperationsContextType | undefined>(undefined);

export const OperationsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [syncCounter, setSyncCounter] = useState<number>(0);
  const [scheduleVersion, setScheduleVersion] = useState<ScheduleVersion | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsDashboard | null>(null);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [selectedInterview, setSelectedInterview] = useState<Interview | null>(null);
  const [isCopilotOpen, setIsCopilotOpen] = useState<boolean>(false);
  const [isDisruptionModalOpen, setIsDisruptionModalOpen] = useState<boolean>(false);
  const [isDiffModalOpen, setIsDiffModalOpen] = useState<boolean>(false);
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState<boolean>(false);
  const [replanningResult, setReplanningResult] = useState<ReplanningResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isLiveConnected, setIsLiveConnected] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<string>('just now');
  const [liveBannerMessage, setLiveBannerMessage] = useState<string | null>(null);

  const triggerSync = () => {
    setSyncCounter((prev) => prev + 1);
    loadDashboardData();
  };

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [schedRes, analyticsRes, conflictsRes, notifRes] = await Promise.all([
        apiClient.get('/schedule/latest'),
        apiClient.get('/analytics/dashboard'),
        apiClient.get('/conflicts'),
        apiClient.get('/notifications')
      ]);

      setScheduleVersion(schedRes.data);
      setAnalytics(analyticsRes.data);
      setConflicts(conflictsRes.data.conflicts || []);
      setNotifications(notifRes.data || []);
      setLastSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      setSyncCounter((prev) => prev + 1);
    } catch (err: any) {
      console.error('Failed to load operations data', err);
      setError(err.response?.data?.detail || 'Failed to load control tower data');
    } finally {
      setIsLoading(false);
    }
  };

  const generateSchedule = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await apiClient.post('/schedule/generate', { max_solve_time_seconds: 30 });
      await loadDashboardData();
    } catch (err: any) {
      console.error('Failed to generate schedule', err);
      setError(err.response?.data?.detail || 'Failed to generate schedule');
    } finally {
      setIsLoading(false);
    }
  };

  const resetSchedule = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.post('/schedule/reset');
      setLiveBannerMessage(res.data.message || 'Schedule reset to clean original baseline.');
      await loadDashboardData();
    } catch (err: any) {
      console.error('Failed to reset schedule', err);
      setError(err.response?.data?.detail || 'Failed to reset schedule');
    } finally {
      setIsLoading(false);
    }
  };

  const reinstateInterview = async (studentId: string, companyId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.post('/schedule/reinstate-interview', {
        student_id: studentId,
        company_id: companyId
      });
      setLiveBannerMessage(res.data.message || 'Interview scheduled successfully.');
      await loadDashboardData();
    } catch (err: any) {
      console.error('Failed to schedule/reinstate interview', err);
      setError(err.response?.data?.detail || 'Failed to schedule interview');
    } finally {
      setIsLoading(false);
    }
  };

  const applyReplanningStrategy = async (replanningRunId: string, strategyType: string) => {
    setIsLoading(true);
    try {
      const res = await apiClient.post('/replanning/apply', {
        replanning_run_id: replanningRunId,
        strategy_type: strategyType
      });
      setReplanningResult(null);
      setLiveBannerMessage(`Applied ${strategyType} Recovery Strategy! Created new Schedule Version V${res.data.version_number || ''}.`);
      await loadDashboardData();
    } catch (err: any) {
      console.error('Failed to apply replanning strategy', err);
      setError(err.response?.data?.detail || 'Failed to apply strategy');
    } finally {
      setIsLoading(false);
    }
  };

  const markNotificationAsRead = async (id: string) => {
    try {
      await apiClient.patch(`/notifications/${id}/read`);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      console.error('Failed to mark notification read', err);
    }
  };

  // Setup Real-Time WebSocket Connection
  useEffect(() => {
    loadDashboardData();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? '127.0.0.1:8000' : window.location.host;
    const roleParam = user?.role || 'COORDINATOR';
    const userParam = user?.id || '';
    const wsUrl = `${protocol}//${host}/ws?role=${roleParam}&user_id=${userParam}`;

    let socket: WebSocket | null = null;
    let reconnectTimer: any = null;

    const connectWebSocket = () => {
      try {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
          setIsLiveConnected(true);
          setLastSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.message) {
              setLiveBannerMessage(data.message);
            }
            // Real-time background sync across all views and portals
            loadDashboardData();
            setSyncCounter((prev) => prev + 1);
          } catch (e) {
            console.error('Error parsing WS event', e);
          }
        };

        socket.onclose = () => {
          setIsLiveConnected(false);
          // Try auto-reconnect after 3s
          reconnectTimer = setTimeout(connectWebSocket, 3000);
        };

        socket.onerror = () => {
          setIsLiveConnected(false);
        };
      } catch (err) {
        setIsLiveConnected(false);
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (socket) socket.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [user]);

  return (
    <OperationsContext.Provider
      value={{
        scheduleVersion,
        analytics,
        conflicts,
        notifications,
        selectedInterview,
        isCopilotOpen,
        isDisruptionModalOpen,
        isDiffModalOpen,
        isHistoryDrawerOpen,
        replanningResult,
        isLoading,
        error,
        isLiveConnected,
        lastSyncTime,
        liveBannerMessage,
        syncCounter,
        triggerSync,
        loadDashboardData,
        generateSchedule,
        resetSchedule,
        reinstateInterview,
        setSelectedInterview,
        setIsCopilotOpen,
        setIsDisruptionModalOpen,
        setIsDiffModalOpen,
        setIsHistoryDrawerOpen,
        setReplanningResult,
        setLiveBannerMessage,
        applyReplanningStrategy,
        markNotificationAsRead
      }}
    >
      {children}
    </OperationsContext.Provider>
  );
};

export const useOperations = (): OperationsContextType => {
  const context = useContext(OperationsContext);
  if (!context) {
    throw new Error('useOperations must be used within an OperationsProvider');
  }
  return context;
};
