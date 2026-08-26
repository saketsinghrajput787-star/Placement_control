import React, { useEffect, useState } from 'react';
import { apiClient } from '../../api/client';
import { Company } from '../../types';
import { Badge } from '../../components/common/Badge';
import { Building2, Search } from 'lucide-react';

export const CompaniesPage: React.FC = () => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    apiClient.get('/companies').then((res) => setCompanies(res.data)).catch(console.error);
  }, []);

  const filtered = companies.filter((c) => {
    if (search) {
      const q = search.toLowerCase();
      return c.name.toLowerCase().includes(q) || c.company_code.toLowerCase().includes(q) || c.industry.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <h2 className="text-xl font-bold text-sand-900 tracking-tight">CORPORATE RECRUITERS DIRECTORY</h2>
        <p className="text-xs text-sand-600 mt-1">
          Active placement recruiters, priority tiers, eligibility criteria, and allocated panel capacity
        </p>
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white p-8 rounded-lg border border-sand-300 text-center text-sand-600 font-semibold text-sm">
          No companies imported yet. Upload companies.csv in Data Import Center.
        </div>
      ) : (
        <div className="bg-white border border-sand-300 rounded-lg overflow-hidden shadow-sm">
          <table className="w-full ops-table">
            <thead>
              <tr>
                <th>Company Name</th>
                <th>Priority Tier</th>
                <th>Industry</th>
                <th>Min CGPA</th>
                <th>Eligible Branches</th>
                <th>Panels</th>
                <th>Shortlisted</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-sand-50">
                  <td>
                    <div className="font-semibold text-sand-900">{c.name}</div>
                    <div className="text-xs text-sand-500 font-mono">{c.company_code}</div>
                  </td>
                  <td>
                    <Badge variant={c.priority_tier === 1 ? 'accent' : 'neutral'} size="sm">
                      Tier {c.priority_tier} (Day {c.priority_tier})
                    </Badge>
                  </td>
                  <td className="text-xs text-sand-700">{c.industry}</td>
                  <td className="font-mono font-bold text-sand-800 text-sm">
                    {c.requirements?.min_cgpa.toFixed(1) || '6.0'}
                  </td>
                  <td>
                    <div className="flex flex-wrap gap-1 max-w-xs">
                      {(c.requirements?.eligible_branches || []).map((b, i) => (
                        <span key={i} className="text-[10px] bg-sand-200 text-sand-800 px-1.5 py-0.5 rounded font-mono">
                          {b}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="font-mono font-semibold text-xs text-forest-800">
                    {c.panels_count} active panels
                  </td>
                  <td className="font-mono font-bold text-xs text-sand-900">
                    {c.shortlisted_count} students
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
