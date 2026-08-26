import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, role?: UserRole, password?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const savedToken = localStorage.getItem('pct_auth_token');
    const savedUser = localStorage.getItem('pct_auth_user');
    if (savedToken && savedUser) {
      setToken(savedToken);
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        console.error('Failed to parse user session', e);
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, role?: UserRole, password?: string) => {
    setIsLoading(true);
    try {
      let pwd = password;
      if (!pwd) {
        if (role === 'COMPANY' || email.includes('placement.edu')) pwd = 'company123';
        else if (role === 'STUDENT' || email.includes('student.edu')) pwd = 'student123';
        else pwd = 'admin123';
      }

      const res = await apiClient.post('/auth/login', {
        email,
        password: pwd,
        role
      });

      const data = res.data;
      setToken(data.access_token);
      const userObj: User = {
        id: data.user_id,
        email: data.email,
        role: data.role as UserRole,
        name: data.name,
        entity_id: data.entity_id,
        is_active: true
      };
      setUser(userObj);
      localStorage.setItem('pct_auth_token', data.access_token);
      localStorage.setItem('pct_auth_user', JSON.stringify(userObj));
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('pct_auth_token');
    localStorage.removeItem('pct_auth_user');
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token && !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
