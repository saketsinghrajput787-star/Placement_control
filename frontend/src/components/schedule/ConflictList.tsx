import React from 'react';
import { ConflictItem } from '../../types';
import { Badge } from '../common/Badge';
import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

interface ConflictListProps {
  conflicts: ConflictItem[];
}

export const ConflictList: React.FC<ConflictListProps> = ({ conflicts }) => {
  if (conflicts.length === 0) {
    return (
      <div className="bg-white border border-sand-300 rounded-lg p-5 flex items-center gap-3 text-status-healthy">
        <CheckCircle2 className="w-5 h-5 shrink-0" />
        <div>
          <h4 className="text-sm font-semibold text-sand-900">Zero Active Schedule Conflicts</h4>
          <p className="text-xs text-sand-600">
            All 10 Hard Constraints (student, room, and panel non-overlap, CGPA cutoffs, operating windows) strictly verified.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-sand-300 rounded-lg overflow-hidden shadow-sm">
      <div className="px-5 py-3.5 bg-red-50/50 border-b border-red-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-status-critical" />
          <h3 className="text-sm font-semibold text-red-900">Active Conflicts Queue ({conflicts.length})</h3>
        </div>
        <span className="text-xs text-red-700 font-mono">Immediate replanning recommended</span>
      </div>

      <div className="divide-y divide-sand-200 max-h-72 overflow-y-auto">
        {conflicts.map((c) => (
          <div key={c.conflict_id} className="p-4 hover:bg-sand-50 transition-colors flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-red-700">{c.conflict_id}</span>
                <Badge variant="critical" size="sm">
                  {c.conflict_type}
                </Badge>
                <span className="text-xs text-sand-500 font-mono">{c.time_slot}</span>
              </div>
              <p className="text-sm text-sand-900 font-medium">{c.explanation}</p>
              <p className="text-xs text-sand-600 flex items-center gap-1">
                <span className="font-semibold">Suggested Action:</span> {c.suggested_action}
              </p>
            </div>
            <div className="text-right shrink-0">
              {c.student_code && <span className="text-xs font-mono bg-sand-200 px-1.5 py-0.5 rounded">{c.student_code}</span>}
              {c.room_code && <span className="text-xs font-mono bg-sand-200 px-1.5 py-0.5 rounded ml-1">{c.room_code}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
