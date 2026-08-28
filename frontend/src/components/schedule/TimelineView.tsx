import React, { useState } from 'react';
import { Interview } from '../../types';
import { useOperations } from '../../store/operationsStore';
import { Badge } from '../common/Badge';
import { Search, Filter, Clock, MapPin, User, Building, AlertTriangle, RefreshCw, XCircle, CheckCircle } from 'lucide-react';

const TIME_SLOTS = [
  "09:00", "09:45", "10:30", "11:15", "12:00", "12:45",
  "13:30", "14:15", "15:00", "15:45", "16:30", "17:15"
];

interface TimelineViewProps {
  interviews: Interview[];
  filterCompanyId?: string;
  filterStudentId?: string;
  isCompact?: boolean;
}

export const TimelineView: React.FC<TimelineViewProps> = ({
  interviews,
  filterCompanyId,
  filterStudentId,
  isCompact = false,
}) => {
  const { setSelectedInterview, reinstateInterview } = useOperations();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'SCHEDULED' | 'RESCHEDULED' | 'CANCELLED'>('ALL');
  const [selectedSlot, setSelectedSlot] = useState<string | 'ALL'>('ALL');
  const [selectedRoom, setSelectedRoom] = useState<string | 'ALL'>('ALL');

  // Compute status counts
  const totalCount = interviews.length;
  const cancelledCount = interviews.filter((iv) => iv.status === 'CANCELLED').length;
  const rescheduledCount = interviews.filter((iv) => iv.status === 'RESCHEDULED' || iv.status === 'REPLACEMENT').length;
  const scheduledCount = interviews.filter((iv) => iv.status === 'SCHEDULED').length;

  // Filter interviews
  const filtered = interviews.filter((iv) => {
    if (filterCompanyId && iv.company_id !== filterCompanyId) return false;
    if (filterStudentId && iv.student_id !== filterStudentId) return false;
    if (selectedSlot !== 'ALL' && iv.start_time_str !== selectedSlot) return false;
    if (selectedRoom !== 'ALL' && iv.room_code !== selectedRoom) return false;
    
    // Status Filter
    if (statusFilter === 'CANCELLED' && iv.status !== 'CANCELLED') return false;
    if (statusFilter === 'RESCHEDULED' && iv.status !== 'RESCHEDULED' && iv.status !== 'REPLACEMENT') return false;
    if (statusFilter === 'SCHEDULED' && iv.status !== 'SCHEDULED') return false;

    if (search) {
      const q = search.toLowerCase();
      return (
        iv.student_name.toLowerCase().includes(q) ||
        iv.student_code.toLowerCase().includes(q) ||
        iv.company_name.toLowerCase().includes(q) ||
        iv.room_code.toLowerCase().includes(q) ||
        iv.panel_code.toLowerCase().includes(q) ||
        iv.status.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const roomsList = Array.from(new Set(interviews.map((iv) => iv.room_code))).sort();

  return (
    <div className="space-y-4">
      {/* Controls & Filter Strip */}
      <div className="bg-white p-4 border border-sand-300 rounded-xl space-y-3 shadow-xs">
        
        {/* Status Tab Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-sand-200">
          <div className="flex items-center gap-2 overflow-x-auto">
            <button
              onClick={() => setStatusFilter('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                statusFilter === 'ALL'
                  ? 'bg-forest-800 text-white shadow-xs'
                  : 'bg-sand-100 text-sand-700 hover:bg-sand-200'
              }`}
            >
              All Interviews ({totalCount})
            </button>
            <button
              onClick={() => setStatusFilter('SCHEDULED')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                statusFilter === 'SCHEDULED'
                  ? 'bg-emerald-700 text-white shadow-xs'
                  : 'bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100'
              }`}
            >
              <CheckCircle className="w-3 h-3" />
              Scheduled ({scheduledCount})
            </button>
            <button
              onClick={() => setStatusFilter('RESCHEDULED')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                statusFilter === 'RESCHEDULED'
                  ? 'bg-amber-600 text-white shadow-xs'
                  : 'bg-amber-50 text-amber-900 border border-amber-200 hover:bg-amber-100'
              }`}
            >
              <RefreshCw className="w-3 h-3" />
              Rescheduled ({rescheduledCount})
            </button>
            <button
              onClick={() => setStatusFilter('CANCELLED')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                statusFilter === 'CANCELLED'
                  ? 'bg-rose-700 text-white shadow-xs'
                  : 'bg-rose-50 text-rose-800 border border-rose-200 hover:bg-rose-100'
              }`}
            >
              <XCircle className="w-3 h-3" />
              Cancelled ({cancelledCount})
            </button>
          </div>

          <span className="text-xs text-sand-500 font-mono">
            Showing {filtered.length} of {interviews.length} slots
          </span>
        </div>

        {/* Dropdowns and Search */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-sand-400" />
            <input
              type="text"
              placeholder="Filter by candidate, company, panel, or room..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-sm bg-transparent border-none focus:outline-none placeholder:text-sand-400 text-sand-800"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 text-xs text-sand-600">
              <Clock className="w-3.5 h-3.5" />
              <select
                value={selectedSlot}
                onChange={(e) => setSelectedSlot(e.target.value)}
                className="text-xs bg-sand-50 border border-sand-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest-600 font-medium"
              >
                <option value="ALL">All Time Slots</option>
                {TIME_SLOTS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-xs text-sand-600">
              <MapPin className="w-3.5 h-3.5" />
              <select
                value={selectedRoom}
                onChange={(e) => setSelectedRoom(e.target.value)}
                className="text-xs bg-sand-50 border border-sand-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest-600 font-medium"
              >
                <option value="ALL">All Rooms</option>
                {roomsList.map((r) => (
                  <option key={r} value={r}>
                    Room {r}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Structured Timetable */}
      <div className="bg-white border border-sand-300 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full ops-table">
            <thead>
              <tr>
                <th>Time Slot</th>
                <th>Candidate</th>
                <th>Branch / CGPA</th>
                <th>Company</th>
                <th>Room</th>
                <th>Panel</th>
                <th>Status / Integrity</th>
                <th>Audit</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-sand-500 italic">
                    No interviews match the selected status or filters.
                  </td>
                </tr>
              ) : (
                filtered.map((iv) => {
                  const isCancelled = iv.status === 'CANCELLED';
                  const isRescheduled = iv.status === 'RESCHEDULED' || iv.status === 'REPLACEMENT';

                  return (
                    <tr
                      key={iv.id}
                      className={`hover:bg-sand-50/80 cursor-pointer transition-colors ${
                        isCancelled ? 'bg-rose-50/30' : isRescheduled ? 'bg-amber-50/20' : ''
                      }`}
                      onClick={() => setSelectedInterview(iv)}
                    >
                      <td className="font-mono font-medium text-xs">
                        <span className={isCancelled ? 'line-through text-rose-500' : 'text-forest-800'}>
                          {iv.start_time_str} – {iv.end_time_str}
                        </span>
                      </td>
                      <td>
                        <div className={`font-medium text-sand-900 ${isCancelled ? 'line-through text-rose-800' : ''}`}>
                          {iv.student_name}
                        </div>
                        <div className="text-xs text-sand-500 font-mono">{iv.student_code}</div>
                      </td>
                      <td>
                        <span className="inline-block bg-sand-200 text-sand-800 text-[11px] font-mono px-1.5 py-0.5 rounded mr-1.5">
                          {iv.student_branch}
                        </span>
                        <span className="text-xs font-semibold text-sand-700">{iv.student_cgpa.toFixed(2)}</span>
                      </td>
                      <td>
                        <div className={`font-medium ${isCancelled ? 'line-through text-rose-800' : 'text-sand-900'}`}>
                          {iv.company_name}
                        </div>
                        <div className="text-[10px] text-amber-700 font-medium">Tier {iv.company_tier} Recruiter</div>
                      </td>
                      <td>
                        <span className={`font-mono text-xs border px-2 py-0.5 rounded font-semibold ${
                          isCancelled ? 'bg-rose-100 text-rose-800 border-rose-200' : 'bg-forest-50 text-forest-800 border-forest-200'
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
                          <div className="space-y-0.5">
                            <Badge variant="warning" size="sm" dot>
                              RESCHEDULED
                            </Badge>
                            {iv.audit_metadata?.assignment_reason && (
                              <div className="text-[10px] text-amber-800 font-medium">
                                Replacement assigned
                              </div>
                            )}
                          </div>
                        ) : (
                          <Badge variant="healthy" size="sm" dot>
                            Feasible (0 conflicts)
                          </Badge>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedInterview(iv);
                            }}
                            className={`text-xs font-semibold underline underline-offset-2 ${
                              isCancelled ? 'text-rose-700 hover:text-rose-900' : 'text-forest-700 hover:text-forest-900'
                            }`}
                          >
                            Explain Decision
                          </button>

                          {(isCancelled || iv.status === 'UNSCHEDULED') && (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                if (iv.student_id && iv.company_id) {
                                  await reinstateInterview(iv.student_id, iv.company_id);
                                }
                              }}
                              className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100 transition-colors"
                            >
                              [ Restore / Schedule ]
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
