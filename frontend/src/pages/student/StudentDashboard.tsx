import React, { useEffect, useState } from 'react';
import { useAuth } from '../../store/authStore';
import { useOperations } from '../../store/operationsStore';
import { apiClient } from '../../api/client';
import { Student, Interview } from '../../types';
import { Card } from '../../components/common/Card';
import { MetricCard } from '../../components/common/MetricCard';
import { Badge } from '../../components/common/Badge';
import { GraduationCap, Calendar, MapPin, Building2, RotateCcw, CheckCircle2 } from 'lucide-react';
import { CancelInterviewModal } from '../../components/student/CancelInterviewModal';

export const StudentDashboard: React.FC = () => {
  const { user } = useAuth();
  const { scheduleVersion, syncCounter, setIsDiffModalOpen, resetSchedule, reinstateInterview } = useOperations();
  const [profile, setProfile] = useState<Student | null>(null);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [selectedForCancel, setSelectedForCancel] = useState<Interview | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchStudentData = () => {
    setIsLoading(true);
    apiClient.get('/students/me/profile').then((res) => {
      setProfile(res.data);
      return apiClient.get(`/schedule/interviews?student_id=${res.data.id}`);
    }).then((res) => {
      if (res) setInterviews(res.data);
    }).catch(console.error)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchStudentData();
  }, [scheduleVersion, syncCounter]);

  return (
    <div className="space-y-6">
      
      {/* Student Profile Strip */}
      <div className="bg-white p-5 rounded-lg border border-sand-300 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-sand-900 tracking-tight">
              {profile?.name || 'Alex Mercer'}
            </h2>
            <span className="text-xs bg-forest-100 text-forest-800 font-mono px-2 py-0.5 rounded font-bold">
              {profile?.student_code || 'S0421'}
            </span>
          </div>
          <p className="text-xs text-sand-600 mt-1">
            Department of {profile?.branch || 'ISE'} • CGPA: {profile?.cgpa.toFixed(2) || '8.62'} • Class of 2026
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="healthy" size="md" dot>
            Active Placement Candidate
          </Badge>
          <button
            onClick={() => resetSchedule()}
            disabled={isLoading}
            className="px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-50 text-amber-900 border border-amber-300 hover:bg-amber-100 transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs active:scale-95 disabled:opacity-50"
            title="Reset all cancellations and schedule every interview"
          >
            <RotateCcw className={`w-3.5 h-3.5 text-amber-700 ${isLoading ? 'animate-spin' : ''}`} />
            {isLoading ? 'Resetting Schedule...' : '[ Reset All Cancellations ]'}
          </button>
          <button
            onClick={() => setIsDiffModalOpen(true)}
            className="px-3 py-1.5 rounded-xl text-xs font-bold bg-sand-100 text-sand-800 border border-sand-300 hover:bg-sand-200 transition-colors cursor-pointer"
          >
            [ View What Changed ]
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          label="Cumulative CGPA"
          value={profile?.cgpa.toFixed(2) || '8.62'}
          icon={<GraduationCap className="w-4 h-4" />}
          status="healthy"
          subValue="Eligible for Day-1 Tiers"
        />
        <MetricCard
          label="Shortlisted Companies"
          value={profile?.shortlisted_companies?.length || 4}
          icon={<Building2 className="w-4 h-4" />}
          status="primary"
          trend="TechNova, DataCore, FinEdge, CyberNet"
        />
        <MetricCard
          label="Scheduled Interviews"
          value={interviews.length}
          icon={<Calendar className="w-4 h-4" />}
          status="primary"
          trend="Zero Overlapping Slots"
        />
      </div>

      {/* Personal Interview Schedule Lineup */}
      <Card
        title="MY LIVE INTERVIEW SCHEDULE"
        subtitle="Chronological interview lineup with allocated rooms and panel numbers"
      >
        {interviews.length === 0 ? (
          <div className="text-center py-8 text-sand-500 italic">
            No active interviews scheduled for today.
          </div>
        ) : (
          <div className="divide-y divide-sand-200">
            {interviews.map((iv) => (
              <div key={iv.id} className="py-4 flex flex-wrap items-center justify-between gap-4 hover:bg-sand-50/50 px-2 rounded-md transition-colors">
                <div className="flex items-center gap-4">
                  <div className="font-mono font-bold text-base text-forest-800 bg-forest-50 px-3 py-2 rounded-md border border-forest-200 text-center min-w-[90px]">
                    {iv.start_time_str}
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-sand-900">{iv.company_name}</h4>
                    <div className="flex items-center gap-3 text-xs text-sand-600 mt-0.5">
                      <span className="flex items-center gap-1 font-semibold text-sand-800">
                        <MapPin className="w-3.5 h-3.5 text-forest-700" />
                        Room {iv.room_code || 'TBD'}
                      </span>
                      <span>•</span>
                      <span className="font-semibold text-sand-800">
                        Panel {iv.panel_code || 'TBD'}
                      </span>
                      <span>•</span>
                      <span className="text-amber-700 font-medium">
                        Tier {iv.company_tier} Recruiter
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Badge variant={iv.status === 'CANCELLED' ? 'critical' : iv.status === 'UNSCHEDULED' ? 'warning' : 'healthy'} size="sm" dot>
                    {iv.status}
                  </Badge>

                  {iv.status === 'CANCELLED' && (
                    <button
                      onClick={async () => {
                        if (profile?.id && iv.company_id) {
                          await reinstateInterview(profile.id, iv.company_id);
                        }
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors flex items-center gap-1.5"
                    >
                      <RotateCcw className="w-3 h-3 text-emerald-600" />
                      [ RESTORE / SCHEDULE ]
                    </button>
                  )}

                  {iv.status === 'UNSCHEDULED' && (
                    <button
                      onClick={async () => {
                        if (profile?.id && iv.company_id) {
                          await reinstateInterview(profile.id, iv.company_id);
                        }
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-bold bg-forest-50 text-forest-800 border border-forest-300 hover:bg-forest-100 transition-colors flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-3 h-3 text-forest-700" />
                      [ SCHEDULE SLOT ]
                    </button>
                  )}

                  {iv.status !== 'CANCELLED' && iv.status !== 'UNSCHEDULED' && (
                    <button
                      onClick={() => setSelectedForCancel(iv)}
                      className="px-3 py-1.5 rounded-xl text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition-colors"
                    >
                      [ CANCEL INTERVIEW ]
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Cancellation Modal */}
      {selectedForCancel && (
        <CancelInterviewModal
          interview={selectedForCancel}
          onClose={() => setSelectedForCancel(null)}
        />
      )}
    </div>
  );
};
