import React, { useState } from 'react';
import { useAuth } from '../../store/authStore';
import { Button } from '../../components/common/Button';
import { UserRole } from '../../types';
import { useNavigate } from 'react-router-dom';
import { Shield, Building2, GraduationCap, Lock, Mail, ArrowRight } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('coordinator@university.edu');
  const [role, setRole] = useState<UserRole>('COORDINATOR');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState<string | null>(null);

  const getErrorMessage = (err: any) => {
    if (!err.response) {
      return 'Unable to connect to backend server. Please verify FastAPI backend is running on http://localhost:8000';
    }
    return err.response?.data?.detail || 'Incorrect email or password';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login(email, role, password);
      if (role === 'COORDINATOR') navigate('/coordinator/dashboard');
      else if (role === 'COMPANY') navigate('/company/dashboard');
      else navigate('/student/dashboard');
    } catch (err: any) {
      setError(getErrorMessage(err));
    }
  };

  const handleRoleSelect = (newRole: UserRole) => {
    setRole(newRole);
    if (newRole === 'COORDINATOR') {
      setEmail('coordinator@university.edu');
      setPassword('admin123');
    } else if (newRole === 'COMPANY') {
      setEmail('technova@placement.edu');
      setPassword('company123');
    } else if (newRole === 'STUDENT') {
      setEmail('s0421@student.edu');
      setPassword('student123');
    }
  };

  const handleQuickLogin = async (demoEmail: string, demoRole: UserRole, demoPwd: string) => {
    setEmail(demoEmail);
    setRole(demoRole);
    setPassword(demoPwd);
    setError(null);
    try {
      await login(demoEmail, demoRole, demoPwd);
      if (demoRole === 'COORDINATOR') navigate('/coordinator/dashboard');
      else if (demoRole === 'COMPANY') navigate('/company/dashboard');
      else navigate('/student/dashboard');
    } catch (err: any) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="min-h-screen bg-sand-100 flex flex-col justify-center items-center p-4">
      <div className="max-w-md w-full space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-lg bg-forest-700 text-white font-bold text-lg flex items-center justify-center mx-auto shadow-md">
            PCT
          </div>
          <h2 className="text-2xl font-bold text-sand-900 tracking-tight">AI-Assisted Placement Control Tower</h2>
          <p className="text-xs text-sand-600">
            University Placement Week Scheduler & Dynamic Replanning System
          </p>
        </div>

        {/* Quick Login Presets */}
        <div className="bg-white border border-sand-300 rounded-lg p-4 shadow-sm space-y-2.5">
          <span className="text-[11px] font-semibold text-sand-500 uppercase tracking-wider block font-mono">
            Demo 1-Click Access Roles
          </span>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => handleQuickLogin('coordinator@university.edu', 'COORDINATOR', 'admin123')}
              className="p-2.5 rounded-md border border-forest-300 bg-forest-50 hover:bg-forest-100 text-forest-900 text-left transition-colors flex flex-col justify-between text-xs"
            >
              <Shield className="w-4 h-4 text-forest-700 mb-1" />
              <div>
                <div className="font-bold">Coordinator</div>
                <div className="text-[10px] text-forest-700 opacity-80">Full Control</div>
              </div>
            </button>

            <button
              onClick={() => handleQuickLogin('technova@placement.edu', 'COMPANY', 'company123')}
              className="p-2.5 rounded-md border border-sand-300 bg-sand-50 hover:bg-sand-100 text-sand-900 text-left transition-colors flex flex-col justify-between text-xs"
            >
              <Building2 className="w-4 h-4 text-amber-600 mb-1" />
              <div>
                <div className="font-bold">TechNova</div>
                <div className="text-[10px] text-sand-500">Recruiter</div>
              </div>
            </button>

            <button
              onClick={() => handleQuickLogin('aarav.sharma@example.com', 'STUDENT', 'student123')}
              className="p-2.5 rounded-md border border-sand-300 bg-sand-50 hover:bg-sand-100 text-sand-900 text-left transition-colors flex flex-col justify-between text-xs"
            >
              <GraduationCap className="w-4 h-4 text-sky-600 mb-1" />
              <div>
                <div className="font-bold">Aarav Sharma</div>
                <div className="text-[10px] text-sand-500 font-mono">S001 (CSE)</div>
              </div>
            </button>
          </div>
        </div>

        {/* Login Card */}
        <div className="bg-white border border-sand-300 rounded-lg p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-md bg-red-50 border border-red-200 text-xs text-status-critical font-medium">
                {error}
              </div>
            )}

            <div>
              <label className="text-xs font-semibold text-sand-700 block mb-1.5">Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-sand-400 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full text-sm bg-sand-50 border border-sand-300 rounded-md py-2 pl-9 pr-3 text-sand-900 focus:outline-none focus:ring-1 focus:ring-forest-600"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-sand-700 block mb-1.5">Portal Role</label>
              <select
                value={role}
                onChange={(e) => handleRoleSelect(e.target.value as UserRole)}
                className="w-full text-sm bg-sand-50 border border-sand-300 rounded-md p-2 text-sand-900 focus:outline-none focus:ring-1 focus:ring-forest-600"
              >
                <option value="COORDINATOR">Placement Coordinator</option>
                <option value="COMPANY">Company Recruiter</option>
                <option value="STUDENT">Student Candidate</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-sand-700 block mb-1.5">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-sand-400 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full text-sm bg-sand-50 border border-sand-300 rounded-md py-2 pl-9 pr-3 text-sand-900 focus:outline-none focus:ring-1 focus:ring-forest-600"
                />
              </div>
              <span className="text-[10px] text-sand-500 mt-1 block">Default passwords pre-loaded for assessment</span>
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full py-2.5"
              icon={<ArrowRight className="w-4 h-4" />}
              isLoading={isLoading}
            >
              Sign In to Operations Center
            </Button>
          </form>
        </div>

        <div className="text-center text-xs text-sand-500 font-mono">
          <span>Constraint Engine: OR-Tools CP-SAT • AI: Groq gpt-oss-120b</span>
        </div>
      </div>
    </div>
  );
};
