import React, { useEffect, useState } from 'react';
import { useAuth } from '../../store/authStore';
import { useOperations } from '../../store/operationsStore';
import { apiClient } from '../../api/client';
import { Company, Interview } from '../../types';
import { MetricCard } from '../../components/common/MetricCard';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Building2, Users, CalendarCheck, DoorOpen, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ReportDelayModal } from '../../components/company/ReportDelayModal';

export const CompanyDashboard: React.FC = () => {
  const { user } = useAuth();
  const { scheduleVersion, syncCounter, setIsDiffModalOpen } = useOperations();
  const navigate = useNavigate();
  const [company, setCompany] = useState<Company | null>(null);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [isDelayModalOpen, setIsDelayModalOpen] = useState<boolean>(false);
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'SCHEDULED' | 'CANCELLED' | 'RESCHEDULED'>('ALL');

  const fetchCompanyData = () => {
    apiClient.get('/companies/me/profile').then((res) => {
      setCompany(res.data);
      return apiClient.get(`/schedule/interviews?company_id=${res.data.id}`);
    }).then((res) => {
      if (res) setInterviews(res.data);
    }).catch(console.error);
  };

  useEffect(() => {
    fetchCompanyData();
  }, [scheduleVersion, syncCounter]);

  const cancelledCount = interviews.filter(i => i.status === 'CANCELLED').length;
  const rescheduledCount = interviews.filter(i => i.status === 'RESCHEDULED' || i.status === 'REPLACEMENT').length;
  const scheduledCount = interviews.filter(i => i.status === 'SCHEDULED').length;

  const filteredInterviews = interviews.filter((iv) => {
    if (statusFilter === 'CANCELLED' && iv.status !== 'CANCELLED') return false;
    if (statusFilter === 'SCHEDULED' && iv.status !== 'SCHEDULED') return false;
    if (statusFilter === 'RESCHEDULED' && iv.status !== 'RESCHEDULED' && iv.status !== 'REPLACEMENT') return false;

    if (search) {
      const q = search.toLowerCase();
      return (
        iv.student_name.toLowerCase().includes(q) ||
        iv.student_code.toLowerCase().includes(q) ||
        iv.room_code.toLowerCase().includes(q) ||
        iv.panel_code.toLowerCase().includes(q) ||
        iv.status.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="bg-white p-5 rounded-lg border border-sand-300 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-sand-900 tracking-tight">{company?.name || 'Recruiter Portal'}</h2>
            <Badge variant="accent" size="sm">
              Tier {company?.priority_tier || 1} Recruiter
            </Badge>
          </div>
          <p className="text-xs text-sand-600 mt-1">
            Interview schedule, candidate shortlist evaluation, and live operational control
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            icon={<ShieldAlert className="w-4 h-4 text-amber-600" />}
            onClick={() => setIsDelayModalOpen(true)}
          >
            [ REPORT DELAY ]
          </Button>

          <Button
            variant="primary"
            size="sm"
            icon={<CalendarCheck className="w-4 h-4" />}
            onClick={() => navigate('/company/schedule')}
          >
            View Full Timetable
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Shortlisted Candidates"
          value={company?.shortlisted_count || 0}
          icon={<Users className="w-4 h-4" />}
          status="primary"
        />
        <MetricCard
          label="Scheduled Interviews"
          value={interviews.length}
          icon={<CalendarCheck className="w-4 h-4" />}
          status="healthy"
        />
        <MetricCard
          label="Active Interview Panels"
          value={company?.panels_count || 0}
          icon={<DoorOpen className="w-4 h-4" />}
          status="primary"
        />
        <MetricCard
          label="Min CGPA Cutoff"
          value={company?.requirements?.min_cgpa.toFixed(1) || '7.5'}
          icon={<Building2 className="w-4 h-4" />}
          status="info"
        />
      </div>

      {/* Today's Schedule Overview */}
      <Card
        title="TODAY'S SCHEDULED INTERVIEW SLOTS"
        subtitle="Live corporate interview lineup sorted chronologically"
        action={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsDiffModalOpen(true)}>
              [ View Changes ]
            </Button>
            <Button variant="ghost" size="sm" onClick={() => navigate('/company/schedule')}>
              Open Table
            </Button>
          </div>
        }
      >
        <div className="p-3 bg-sand-50 border-b border-sand-200 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 overflow-x-auto">
            <button
              onClick={() => setStatusFilter('ALL')}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                statusFilter === 'ALL' ? 'bg-forest-800 text-white' : 'bg-white text-sand-700 border border-sand-300 hover:bg-sand-100'
              }`}
            >
              All ({interviews.length})
            </button>
            <button
              onClick={() => setStatusFilter('SCHEDULED')}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                statusFilter === 'SCHEDULED' ? 'bg-emerald-700 text-white' : 'bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100'
              }`}
            >
              Scheduled ({scheduledCount})
            </button>
            <button
              onClick={() => setStatusFilter('CANCELLED')}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                statusFilter === 'CANCELLED' ? 'bg-rose-700 text-white' : 'bg-rose-50 text-rose-800 border border-rose-200 hover:bg-rose-100'
              }`}
            >
              Cancelled ({cancelledCount})
            </button>
          </div>

          <div className="flex items-center gap-2 flex-1 max-w-xs">
            <input
              type="text"
              placeholder="Search candidate (e.g. Alex, S0421)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-3 py-1.5 text-xs bg-white border border-sand-300 rounded-lg text-sand-900 focus:outline-none focus:ring-1 focus:ring-forest-600 font-medium"
            />
          </div>
        </div>

        <div className="overflow-x-auto max-h-[480px]">
          <table className="w-full ops-table">
            <thead>
              <tr>
                <th>Time Slot</th>
                <th>Candidate</th>
                <th>Branch / CGPA</th>
                <th>Room</th>
                <th>Panel</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredInterviews.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-sand-500 italic">
                    No scheduled interviews currently match your search or filter.
                  </td>
                </tr>
              ) : (
                filteredInterviews.map((iv) => {
                  const isCancelled = iv.status === 'CANCELLED';
                  const isRescheduled = iv.status === 'RESCHEDULED' || iv.status === 'REPLACEMENT';

                  return (
                    <tr key={iv.id} className={isCancelled ? 'bg-rose-50/50' : isRescheduled ? 'bg-amber-50/30' : ''}>
                      <td className="font-mono font-bold text-xs">
                        <span className={isCancelled ? 'line-through text-rose-600' : 'text-forest-800'}>
                          {iv.start_time_str} – {iv.end_time_str}
                        </span>
                      </td>
                      <td>
                        <div className={`font-semibold ${isCancelled ? 'line-through text-rose-900 font-bold' : 'text-sand-900'}`}>
                          {iv.student_name}
                        </div>
                        <div className="text-xs text-sand-500 font-mono">{iv.student_code}</div>
                      </td>
                      <td>
                        <span className="font-mono text-xs bg-sand-200 px-1.5 py-0.5 rounded mr-1">{iv.student_branch}</span>
                        <span className="font-semibold text-xs text-sand-800">{iv.student_cgpa.toFixed(2)}</span>
                      </td>
                      <td>
                        <span className={`font-mono text-xs border px-2 py-0.5 rounded font-semibold ${
                          isCancelled ? 'bg-rose-100 text-rose-800 border-rose-200' : 'bg-forest-50 text-forest-900 border-forest-200'
                        }`}>
                          {iv.room_code}
                        </span>
                      </td>
                      <td>
                        <span className="font-mono text-xs bg-sand-100 text-sand-800 border border-sand-300 px-2 py-0.5 rounded font-semibold">
                          {iv.panel_code}
                        </span>
                      </td>
                      <td>
                        {isCancelled ? (
                          <Badge variant="critical" size="sm" dot>
                            CANCELLED
                          </Badge>
                        ) : isRescheduled ? (
                          <Badge variant="warning" size="sm" dot>
                            RESCHEDULED
                          </Badge>
                        ) : (
                          <Badge variant="healthy" size="sm" dot>
                            {iv.status}
                          </Badge>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Delay Modal */}
      {isDelayModalOpen && (
        <ReportDelayModal
          company={company}
          onClose={() => setIsDelayModalOpen(false)}
        />
      )}
    </div>
  );
};
