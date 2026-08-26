import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../store/authStore';
import {
  LayoutDashboard,
  Calendar,
  Building2,
  Users,
  DoorOpen,
  GitPullRequestDraft,
  ShieldAlert,
  BarChart3,
  ListOrdered,
  FileCheck,
  Bell,
  UploadCloud,
  FileText
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const role = user?.role || 'COORDINATOR';

  const coordinatorLinks = [
    { to: '/coordinator/dashboard', label: 'Control Tower', icon: <LayoutDashboard className="w-4 h-4" /> },
    { to: '/coordinator/schedule', label: 'Live Schedule', icon: <Calendar className="w-4 h-4" /> },
    { to: '/coordinator/import', label: 'Data Import Center', icon: <UploadCloud className="w-4 h-4" /> },
    { to: '/coordinator/replanning', label: 'Replanning Engine', icon: <GitPullRequestDraft className="w-4 h-4" /> },
    { to: '/coordinator/disruptions', label: 'Disruption Log', icon: <ShieldAlert className="w-4 h-4" /> },
    { to: '/coordinator/analytics', label: 'Bottleneck Radar', icon: <BarChart3 className="w-4 h-4" /> },
    { to: '/coordinator/audit', label: 'Audit Log Timeline', icon: <FileText className="w-4 h-4" /> },
    { to: '/coordinator/students', label: 'Students', icon: <Users className="w-4 h-4" /> },
    { to: '/coordinator/companies', label: 'Companies', icon: <Building2 className="w-4 h-4" /> },
    { to: '/coordinator/resources', label: 'Rooms & Panels', icon: <DoorOpen className="w-4 h-4" /> },
  ];

  const companyLinks = [
    { to: '/company/dashboard', label: 'Company Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    { to: '/company/schedule', label: 'Interview Timetable', icon: <Calendar className="w-4 h-4" /> },
    { to: '/company/shortlist', label: 'Candidate Shortlist', icon: <ListOrdered className="w-4 h-4" /> },
    { to: '/company/panels', label: 'Panels & Availability', icon: <DoorOpen className="w-4 h-4" /> },
  ];

  const studentLinks = [
    { to: '/student/dashboard', label: 'My Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { to: '/student/schedule', label: 'My Interviews', icon: <Calendar className="w-4 h-4" /> },
    { to: '/student/notifications', label: 'Schedule Changes', icon: <Bell className="w-4 h-4" /> },
  ];

  const links = role === 'COORDINATOR' ? coordinatorLinks : (role === 'COMPANY' ? companyLinks : studentLinks);

  return (
    <aside className="w-64 bg-sand-50 border-r border-sand-300 flex flex-col justify-between shrink-0 h-[calc(100vh-4rem)] sticky top-16">
      <div className="p-4 space-y-1 overflow-y-auto">
        <div className="px-3 py-2 text-[11px] font-semibold text-sand-500 uppercase tracking-wider font-mono">
          {role} PORTAL
        </div>
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-forest-700 text-white shadow-xs'
                  : 'text-sand-700 hover:bg-sand-200/80 hover:text-sand-950'
              }`
            }
          >
            <span className="shrink-0">{link.icon}</span>
            <span>{link.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="p-4 border-t border-sand-200 text-xs text-sand-500 font-mono">
        <div className="flex items-center justify-between">
          <span>Engine:</span>
          <span className="text-forest-800 font-semibold">OR-Tools CP-SAT</span>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span>AI Copilot:</span>
          <span className="text-amber-700 font-semibold">Groq gpt-oss</span>
        </div>
      </div>
    </aside>
  );
};
