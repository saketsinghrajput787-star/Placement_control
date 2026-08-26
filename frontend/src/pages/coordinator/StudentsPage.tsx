import React, { useEffect, useState } from 'react';
import { apiClient } from '../../api/client';
import { Student } from '../../types';
import { Badge } from '../../components/common/Badge';
import { Search, Users, GraduationCap } from 'lucide-react';

export const StudentsPage: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [search, setSearch] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('ALL');

  useEffect(() => {
    apiClient.get('/students?limit=500').then((res) => setStudents(res.data)).catch(console.error);
  }, []);

  const branches = ['ALL', 'CSE', 'ISE', 'ECE', 'EEE', 'MECH', 'CIVIL', 'AI_ML'];

  const filtered = students.filter((s) => {
    if (selectedBranch !== 'ALL' && s.branch !== selectedBranch) return false;
    if (search) {
      const q = search.toLowerCase();
      return s.name.toLowerCase().includes(q) || s.student_code.toLowerCase().includes(q) || s.email.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <h2 className="text-xl font-bold text-sand-900 tracking-tight">STUDENT CANDIDATES DATABASE</h2>
        <p className="text-xs text-sand-600 mt-1">
          Complete roster of enrolled graduating students with CGPA cutoffs and corporate shortlist links
        </p>
      </div>

      {/* Filter Strip */}
      <div className="bg-white p-3.5 border border-sand-300 rounded-lg flex flex-wrap items-center justify-between gap-3 shadow-xs">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-sand-400" />
          <input
            type="text"
            placeholder="Search candidate name, code (e.g. S0421), or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-sm bg-transparent border-none focus:outline-none placeholder:text-sand-400 text-sand-800"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-sand-600 font-semibold">Branch:</span>
          <select
            value={selectedBranch}
            onChange={(e) => setSelectedBranch(e.target.value)}
            className="text-xs bg-sand-50 border border-sand-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest-600"
          >
            {branches.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
          <span className="text-xs text-sand-500 font-mono ml-2">
            Showing {filtered.length} candidates
          </span>
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="bg-white p-8 rounded-lg border border-sand-300 text-center text-sand-600 font-semibold text-sm">
          No students imported yet. Upload students.csv in Data Import Center.
        </div>
      ) : (
        <div className="bg-white border border-sand-300 rounded-lg overflow-hidden shadow-sm">
          <table className="w-full ops-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Student Name</th>
                <th>Branch</th>
                <th>CGPA</th>
                <th>Shortlisted By</th>
                <th>Interviews</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 100).map((s) => (
                <tr key={s.id} className="hover:bg-sand-50">
                  <td className="font-mono font-bold text-forest-800 text-xs">{s.student_code}</td>
                  <td>
                    <div className="font-semibold text-sand-900">{s.name}</div>
                    <div className="text-xs text-sand-500">{s.email}</div>
                  </td>
                  <td>
                    <span className="bg-sand-200 text-sand-800 text-xs font-mono px-2 py-0.5 rounded">
                      {s.branch}
                    </span>
                  </td>
                  <td className="font-bold text-sand-800 font-mono text-sm">{s.cgpa.toFixed(2)}</td>
                  <td>
                    <div className="flex flex-wrap gap-1 max-w-xs">
                      {(s.shortlisted_companies || []).map((c, i) => (
                        <span key={i} className="text-[10px] bg-forest-50 text-forest-900 border border-forest-200 px-1.5 py-0.5 rounded font-medium">
                          {c}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="font-mono font-semibold text-xs text-sand-900">
                    {s.interview_count || 0} scheduled
                  </td>
                  <td>
                    <Badge variant={s.is_withdrawn ? 'critical' : 'healthy'} size="sm" dot>
                      {s.is_withdrawn ? 'Withdrawn' : 'Active'}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
