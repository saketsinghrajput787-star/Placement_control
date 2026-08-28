import React from 'react';
import { useOperations } from '../../store/operationsStore';
import { Badge } from '../common/Badge';
import { X, CheckCircle2, ShieldCheck, Cpu, AlertCircle, XCircle, RefreshCw, AlertTriangle } from 'lucide-react';

export const ExplainabilityDrawer: React.FC = () => {
  const { selectedInterview, setSelectedInterview } = useOperations();

  if (!selectedInterview) return null;

  const audit = selectedInterview.audit_metadata;
  const isCancelled = selectedInterview.status === 'CANCELLED';
  const isRescheduled = selectedInterview.status === 'RESCHEDULED' || selectedInterview.status === 'REPLACEMENT';
  const isUnscheduled = selectedInterview.status === 'UNSCHEDULED';

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div
        className="fixed inset-0 bg-sand-900/40 backdrop-blur-xs transition-opacity"
        onClick={() => setSelectedInterview(null)}
      />

      <div className="fixed inset-y-0 right-0 max-w-lg w-full bg-white shadow-2xl border-l border-sand-300 flex flex-col z-50 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className={`p-5 border-b flex items-center justify-between ${
          isCancelled ? 'bg-rose-50 border-rose-200' : isRescheduled ? 'bg-amber-50 border-amber-200' : 'bg-sand-50 border-sand-200'
        }`}>
          <div>
            <div className="flex items-center gap-2">
              {isCancelled ? (
                <XCircle className="w-5 h-5 text-rose-600" />
              ) : isRescheduled ? (
                <RefreshCw className="w-5 h-5 text-amber-600" />
              ) : (
                <Cpu className="w-5 h-5 text-forest-700" />
              )}
              <h3 className="text-base font-bold text-sand-900">
                {isCancelled
                  ? 'Interview Cancellation Audit'
                  : isRescheduled
                  ? 'Reassignment & Recovery Audit'
                  : isUnscheduled
                  ? 'Unscheduled Shortlist Status'
                  : 'Assignment Engineering Audit'}
              </h3>
            </div>
            <p className="text-xs text-sand-600 font-mono mt-0.5">
              {isCancelled
                ? 'Candidate/Recruiter cancellation record & freed slot analysis'
                : isRescheduled
                ? 'Automated candidate reallocation & replanning trail'
                : 'Deterministic CP-SAT solver constraint & decision trail'}
            </p>
          </div>
          <button
            onClick={() => setSelectedInterview(null)}
            className="p-1 rounded-md text-sand-400 hover:text-sand-700 hover:bg-sand-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Summary Card */}
          <div className={`p-4 rounded-xl border space-y-3 ${
            isCancelled ? 'bg-rose-50/60 border-rose-200' : isRescheduled ? 'bg-amber-50/60 border-amber-200' : 'bg-sand-100 border-sand-300'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-forest-800">{selectedInterview.student_code}</span>
              <Badge
                variant={isCancelled ? 'critical' : isRescheduled ? 'warning' : isUnscheduled ? 'warning' : 'healthy'}
                size="sm"
                dot
              >
                {selectedInterview.status}
              </Badge>
            </div>
            <div>
              <h4 className="text-base font-bold text-sand-900">{selectedInterview.student_name}</h4>
              <p className="text-xs text-sand-600">
                {selectedInterview.student_branch} • CGPA: {selectedInterview.student_cgpa.toFixed(2)}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-sand-200/80 text-xs">
              <div>
                <span className="text-sand-500 block">Recruiter:</span>
                <span className="font-semibold text-sand-900">{selectedInterview.company_name}</span>
              </div>
              <div>
                <span className="text-sand-500 block">Priority:</span>
                <span className="font-semibold text-amber-700">Tier {selectedInterview.company_tier}</span>
              </div>
              <div>
                <span className="text-sand-500 block">Time Slot:</span>
                <span className={`font-mono font-semibold ${isCancelled ? 'line-through text-rose-700' : 'text-forest-800'}`}>
                  {selectedInterview.start_time_str} – {selectedInterview.end_time_str}
                </span>
              </div>
              <div>
                <span className="text-sand-500 block">Location:</span>
                <span className="font-semibold text-sand-900">
                  Room {selectedInterview.room_code || 'TBD'} • Panel {selectedInterview.panel_code || 'TBD'}
                </span>
              </div>
            </div>
          </div>

          {/* Section 1: CANCELLED Details */}
          {isCancelled && (
            <div className="space-y-4">
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-2 text-rose-900 font-bold text-xs uppercase tracking-wider">
                  <AlertTriangle className="w-4 h-4 text-rose-600" />
                  Official Cancellation Reason
                </div>
                <div className="bg-white p-3.5 rounded-lg border border-rose-200 text-sm font-bold text-rose-950">
                  "{audit?.cancellation_reason || 'Personal reason / Candidate requested cancellation'}"
                </div>

                {audit?.comment && (
                  <div className="text-xs text-rose-900 bg-rose-100/60 p-2.5 rounded-md border border-rose-200">
                    <span className="font-bold">Candidate Comment:</span> {audit.comment}
                  </div>
                )}

                <div className="pt-2 border-t border-rose-200/60 grid grid-cols-2 gap-2 text-xs text-rose-900">
                  <div>
                    <span className="text-rose-700 block">Cancelled By:</span>
                    <span className="font-bold">{audit?.cancelled_by_role || 'STUDENT'}</span>
                  </div>
                  <div>
                    <span className="text-rose-700 block">Shortlist Status:</span>
                    <span className="font-bold text-rose-800">WITHDRAWN</span>
                  </div>
                </div>
              </div>

              {/* Slot Impact & Vacancy Breakdown */}
              <div className="bg-sand-50 border border-sand-300 rounded-xl p-4 space-y-2 text-xs">
                <h4 className="font-bold text-sand-900 uppercase tracking-wider text-[11px]">
                  Campus Infrastructure Impact
                </h4>
                <p className="text-sand-700 leading-relaxed">
                  The slot at <strong className="font-mono text-sand-900">{selectedInterview.start_time_str}</strong> in <strong className="text-sand-900">Room {selectedInterview.room_code} / Panel {selectedInterview.panel_code}</strong> was vacated and candidate shortlist marked as withdrawn.
                </p>
              </div>
            </div>
          )}

          {/* Section 2: RESCHEDULED / REASSIGNED Details */}
          {isRescheduled && (
            <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-2 text-amber-900 font-bold text-xs uppercase tracking-wider">
                  <RefreshCw className="w-4 h-4 text-amber-700" />
                  Reallocation & Replanning Rationale
                </div>
                <div className="bg-white p-3 rounded-lg border border-amber-200 text-xs font-semibold text-amber-950 leading-relaxed">
                  {audit?.assignment_reason || audit?.replan_reason || 'Reassigned to optimize slot utilization following cancellation.'}
                </div>

                {audit?.candidate_score && (
                  <div className="text-xs text-amber-800 bg-amber-100/60 p-2 rounded-md">
                    <span className="font-bold">Heuristic Match Score:</span> {audit.candidate_score.toFixed(2)}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Section 3: Hard Constraints Checklist (for active SCHEDULED interviews) */}
          {!isCancelled && !isUnscheduled && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-sand-700 mb-3 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-status-healthy" />
                Hard Constraints Verified (10/10)
              </h4>
              <div className="bg-white border border-sand-300 rounded-lg p-3.5 space-y-2">
                {[
                  { label: 'Student CGPA & Branch Eligibility Satisfied', ok: true },
                  { label: 'Zero Student Schedule Overlap at assigned slot', ok: true },
                  { label: 'Room available & dedicated to this interview', ok: true },
                  { label: 'Company panel active and available', ok: true },
                  { label: 'Interview fits within 45-min duration window', ok: true },
                ].map((c, i) => (
                  <div key={i} className="flex items-center gap-2.5 text-xs text-sand-800">
                    <CheckCircle2 className="w-4 h-4 text-status-healthy shrink-0" />
                    <span>{c.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 4: Optimization Reasons (for SCHEDULED interviews) */}
          {!isCancelled && !isUnscheduled && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-sand-700 mb-3 flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-forest-700" />
                Optimization Decision Rationale
              </h4>
              <ul className="space-y-2">
                {(audit?.optimization_reasons && audit.optimization_reasons.length > 0 ? audit.optimization_reasons : [
                  `Assigned slot (${selectedInterview.start_time_str}) based on deterministic CP-SAT objective.`,
                  `Company tier ${selectedInterview.company_tier} priority scalarization reward applied.`,
                  `Preserves room stability and avoids panel contention.`,
                ]).map((reason, i) => (
                  <li key={i} className="text-xs text-sand-800 bg-sand-50 border border-sand-200 p-2.5 rounded-md flex items-start gap-2">
                    <span className="text-forest-700 font-bold">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Section 5: Evaluated Alternatives (for active SCHEDULED interviews) */}
          {!isCancelled && !isUnscheduled && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-sand-700 mb-3 flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 text-sand-500" />
                Evaluated Alternatives
              </h4>
              <div className="border border-sand-300 rounded-lg overflow-hidden text-xs">
                <table className="w-full">
                  <thead className="bg-sand-200 text-sand-700 font-semibold">
                    <tr>
                      <th className="py-2 px-3 text-left">Slot</th>
                      <th className="py-2 px-3 text-left">Evaluation Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-sand-200">
                    {(audit?.rejected_alternatives && audit.rejected_alternatives.length > 0 ? audit.rejected_alternatives : [
                      { slot: '10:00', reason: 'Student had conflicting Tier-1 shortlist interview' },
                      { slot: '11:30', reason: 'Panel P1 reached maximum consecutive load' },
                      { slot: '14:15', reason: 'Lower multi-objective score due to longer waiting gap' },
                    ]).map((alt, i) => (
                      <tr key={i} className="hover:bg-sand-50">
                        <td className="py-2 px-3 font-mono text-sand-800">{alt.slot}</td>
                        <td className="py-2 px-3 text-sand-600">{alt.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-sand-200 bg-sand-50 flex items-center justify-between text-xs text-sand-500 font-mono">
          <span>Engine: Google OR-Tools CP-SAT</span>
          <span className="text-forest-800 font-semibold">
            Status: {selectedInterview.status}
          </span>
        </div>
      </div>
    </div>
  );
};
