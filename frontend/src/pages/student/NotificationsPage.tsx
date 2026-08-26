import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Bell, Clock, ArrowRight } from 'lucide-react';

export const NotificationsPage: React.FC = () => {
  const notifications = [
    {
      id: '1',
      title: 'Interview Rescheduled: TechNova Systems',
      message: 'Due to recruiter flight delay, your interview with TechNova Systems has moved from 10:00 to 12:15 in Room R04 (Panel P2).',
      time: '10 mins ago',
      type: 'SCHEDULE_UPDATE',
    },
    {
      id: '2',
      title: 'Shortlist Confirmed: FinEdge Quant Capital',
      message: 'You have been shortlisted for technical interview round 1.',
      time: '1 hour ago',
      type: 'INFO',
    },
    {
      id: '3',
      title: 'Placement Week Day 1 Kickoff',
      message: 'All campus interview rooms in Block A and Block B are active.',
      time: '08:45 AM',
      type: 'SYSTEM',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <h2 className="text-xl font-bold text-sand-900 tracking-tight">SCHEDULE NOTIFICATIONS & ALERTS</h2>
        <p className="text-xs text-sand-600 mt-1">
          Real-time updates on interview rescheduling, delays, and room assignments
        </p>
      </div>

      <div className="bg-white border border-sand-300 rounded-lg divide-y divide-sand-200">
        {notifications.map((n) => (
          <div key={n.id} className="p-4 hover:bg-sand-50 transition-colors flex items-start gap-4 text-xs">
            <div className="w-8 h-8 rounded-full bg-forest-50 text-forest-700 flex items-center justify-center shrink-0 mt-0.5">
              <Bell className="w-4 h-4" />
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-sand-900 text-sm">{n.title}</h4>
                <span className="text-sand-400 font-mono">{n.time}</span>
              </div>
              <p className="text-sand-700 leading-relaxed">{n.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
