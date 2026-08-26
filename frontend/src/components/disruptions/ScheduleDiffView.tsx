import React, { useState } from 'react';
import { ScheduleDiffItem } from '../../types';
import { Badge } from '../common/Badge';
import { ArrowRight, Search, CheckCircle2, AlertTriangle, XCircle, PlusCircle } from 'lucide-react';

interface ScheduleDiffViewProps {
  diff: ScheduleDiffItem[];
  stabilityScore: number;
}

export const ScheduleDiffView: React.FC<ScheduleDiffViewProps> = ({ diff, stabilityScore }) => {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [search, setSearch] = useState('');

  const filtered = diff.filter((item) => {
    if (filterType !== 'ALL' && item.change_type !== filterType) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        item.student_name.toLowerCase().includes(q) ||
        item.student_code.toLowerCase().includes(q) ||
        item.company_name.toLowerCase().includes(q) ||
        item.reason.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const unchangedCount = diff.filter((d) => d.change_type === 'UNCHANGED').length;
  const movedCount = diff.filter((d) => d.change_type === 'MOVED').length;
  const cancelledCount = diff.filter((d) => d.change_type === 'CANCELLED').length;
  const newCount = diff.filter((d) => d.change_type === 'NEW').length;

  return (
    <div className="bg-white border border-sand-300 rounded-lg overflow-hidden shadow-sm space-y-4">
      {/* Header & Stability Summary */}
      <div className="p-5 border-b border-sand-200 bg-sand-50 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-sand-900">Before & After Schedule Diff Analysis</h3>
          <p className="text-xs text-sand-600">
            Audit of all preserved, moved, and updated candidate time slots
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="text-right">
            <span className="text-xs text-sand-500 block">Schedule Stability</span>
            <span className="text-lg font-bold font-mono text-forest-800">{stabilityScore.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Filter Tabs & Search */}
      <div className="px-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 bg-sand-200/70 p-1 rounded-md text-xs font-semibold">
          <button
            onClick={() => setFilterType('ALL')}
            className={`px-3 py-1 rounded transition-colors ${
              filterType === 'ALL' ? 'bg-white text-sand-900 shadow-xs' : 'text-sand-700 hover:text-sand-900'
            }`}
          >
            All ({diff.length})
          </button>
          <button
            onClick={() => setFilterType('MOVED')}
            className={`px-3 py-1 rounded transition-colors ${
              filterType === 'MOVED' ? 'bg-amber-100 text-amber-900 shadow-xs' : 'text-sand-700 hover:text-sand-900'
            }`}
          >
            Moved ({movedCount})
          </button>
          <button
            onClick={() => setFilterType('UNCHANGED')}
            className={`px-3 py-1 rounded transition-colors ${
              filterType === 'UNCHANGED' ? 'bg-green-100 text-green-900 shadow-xs' : 'text-sand-700 hover:text-sand-900'
            }`}
          >
            Unchanged ({unchangedCount})
          </button>
          {cancelledCount > 0 && (
            <button
              onClick={() => setFilterType('CANCELLED')}
              className={`px-3 py-1 rounded transition-colors ${
                filterType === 'CANCELLED' ? 'bg-red-100 text-red-900 shadow-xs' : 'text-sand-700 hover:text-sand-900'
              }`}
            >
              Cancelled ({cancelledCount})
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-sand-400" />
          <input
            type="text"
            placeholder="Search diff items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="text-xs bg-sand-50 border border-sand-300 rounded px-2.5 py-1.5 w-full focus:outline-none focus:ring-1 focus:ring-forest-600"
          />
        </div>
      </div>

      {/* Diff Table */}
      <div className="overflow-x-auto">
        <table className="w-full ops-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Candidate</th>
              <th>Company</th>
              <th>Original Assignment</th>
              <th>New Assignment</th>
              <th>Movement Reason</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-6 text-sand-500 italic">
                  No schedule diff items match the current filter.
                </td>
              </tr>
            ) : (
              filtered.map((d, i) => (
                <tr key={i} className="hover:bg-sand-50">
                  <td>
                    {d.change_type === 'UNCHANGED' && (
                      <Badge variant="healthy" size="sm" dot>
                        UNCHANGED
                      </Badge>
                    )}
                    {d.change_type === 'MOVED' && (
                      <Badge variant="warning" size="sm" dot>
                        MOVED
                      </Badge>
                    )}
                    {d.change_type === 'CANCELLED' && (
                      <Badge variant="critical" size="sm" dot>
                        CANCELLED
                      </Badge>
                    )}
                    {d.change_type === 'NEW' && (
                      <Badge variant="info" size="sm" dot>
                        NEW
                      </Badge>
                    )}
                  </td>
                  <td>
                    <div className="font-semibold text-sand-900">{d.student_name}</div>
                    <div className="text-xs text-sand-500 font-mono">{d.student_code}</div>
                  </td>
                  <td className="font-medium text-sand-800">{d.company_name}</td>
                  <td>
                    {d.old_time_str ? (
                      <span className="font-mono text-xs text-sand-700 bg-sand-100 px-2 py-1 rounded border border-sand-200">
                        {d.old_time_str} • {d.old_room_code || 'R01'} ({d.old_panel_code || 'P1'})
                      </span>
                    ) : (
                      <span className="text-xs text-sand-400 italic">None</span>
                    )}
                  </td>
                  <td>
                    {d.new_time_str ? (
                      <span className="font-mono text-xs text-forest-900 bg-forest-50 px-2 py-1 rounded border border-forest-200 font-semibold flex items-center gap-1.5 w-fit">
                        <ArrowRight className="w-3 h-3 text-forest-600" />
                        {d.new_time_str} • {d.new_room_code || 'R01'} ({d.new_panel_code || 'P1'})
                      </span>
                    ) : (
                      <span className="text-xs text-status-critical font-medium">Unscheduled</span>
                    )}
                  </td>
                  <td className="text-xs text-sand-600 max-w-xs">{d.reason}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
