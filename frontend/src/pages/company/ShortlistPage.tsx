import React, { useEffect, useState } from 'react';
import { apiClient } from '../../api/client';
import { Company, Shortlist } from '../../types';
import { Badge } from '../../components/common/Badge';
import { Search, ListOrdered, CheckCircle2 } from 'lucide-react';

export const ShortlistPage: React.FC = () => {
  const [company, setCompany] = useState<Company | null>(null);
  const [shortlists, setShortlists] = useState<Shortlist[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    apiClient.get('/companies/me/profile').then((res) => {
      setCompany(res.data);
      return apiClient.get(`/shortlists/company/${res.data.id}`);
    }).then((res) => {
      if (res) setShortlists(res.data);
    }).catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  const filtered = shortlists.filter((sh) => {
    if (search) {
      const q = search.toLowerCase();
      return sh.student_name.toLowerCase().includes(q) || sh.student_code.toLowerCase().includes(q) || sh.student_branch.toLowerCase().includes(q);
    }
    return true;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-sand-600 text-sm font-medium">
        Loading shortlisted candidates...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-lg border border-sand-300 shadow-xs flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-sand-900 tracking-tight">SHORTLISTED CANDIDATES</h2>
          <p className="text-xs text-sand-600 mt-1">
            Candidates satisfying CGPA cutoffs (&gt;= {company?.requirements?.min_cgpa || 7.0}) and eligible branches
          </p>
        </div>
        <span className="text-xs font-semibold text-sand-700 bg-sand-100 px-3 py-1.5 rounded-md border border-sand-300">
          {shortlists.length} Candidates Shortlisted
        </span>
      </div>

      <div className="bg-white border border-sand-300 rounded-lg overflow-hidden shadow-sm">
        <table className="w-full ops-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Student Code</th>
              <th>Student Name</th>
              <th>Branch</th>
              <th>CGPA</th>
              <th>Shortlist Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-sand-500 italic">
                  No shortlisted candidates match your search filter.
                </td>
              </tr>
            ) : (
              filtered.map((sh, idx) => (
                <tr key={sh.id} className="hover:bg-sand-50">
                  <td className="font-mono font-bold text-xs text-sand-600">#{idx + 1}</td>
                  <td className="font-mono font-bold text-forest-800 text-xs">{sh.student_code}</td>
                  <td className="font-semibold text-sand-900">{sh.student_name}</td>
                  <td>
                    <span className="bg-sand-200 text-sand-800 text-xs font-mono px-2 py-0.5 rounded">
                      {sh.student_branch}
                    </span>
                  </td>
                  <td className="font-bold text-sand-800 font-mono text-sm">{sh.student_cgpa.toFixed(2)}</td>
                  <td>
                    <Badge variant="healthy" size="sm" dot>
                      {sh.status}
                    </Badge>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
