import React, { useState } from 'react';
import { Company } from '../../types';
import { apiClient } from '../../api/client';
import { useOperations } from '../../store/operationsStore';

interface Props {
  company: Company | null;
  onClose: () => void;
}

export const ReportDelayModal: React.FC<Props> = ({ company, onClose }) => {
  const { loadDashboardData, setReplanningResult, setIsDisruptionModalOpen, setLiveBannerMessage } = useOperations();
  const [delayHours, setDelayHours] = useState<number>(2.0);
  const [reason, setReason] = useState<string>('Flight / Travel Delay');
  const [simulationResult, setSimulationResult] = useState<any>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!company) return null;

  const handleSimulate = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      const res = await apiClient.post(`/companies/${company.id}/delay`, {
        delay_hours: delayHours,
        reason: reason
      });
      setSimulationResult(res.data);
    } catch (err: any) {
      console.error('Failed to simulate delay', err);
      setError(err.response?.data?.detail || 'Failed to simulate delay impact');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleGenerateStrategies = async () => {
    if (!simulationResult?.disruption_id) return;
    setIsGenerating(true);
    setError(null);

    try {
      const res = await apiClient.post('/replanning/run', {
        disruption_id: simulationResult.disruption_id
      });
      setReplanningResult(res.data);
      onClose();
      setIsDisruptionModalOpen(true);
    } catch (err: any) {
      console.error('Failed to generate recovery strategies', err);
      setError(err.response?.data?.detail || 'Failed to generate strategies');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-sand-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-3xl border border-sand-300 shadow-2xl w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="p-6 bg-sand-100 border-b border-sand-200 flex items-center justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-forest-700">Company Operational Control</span>
            <h3 className="text-lg font-black text-sand-900 mt-0.5">Report Delay / Late Arrival</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-sand-400 hover:text-sand-700 hover:bg-sand-200 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          <div className="p-4 rounded-2xl bg-sand-50 border border-sand-200 text-xs flex justify-between items-center">
            <div>
              <div className="font-bold text-sand-900 text-sm">{company.name}</div>
              <div className="text-sand-500">Company Code: {company.company_code} • Priority Tier {company.priority_tier}</div>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
              Scheduled Arrival: 09:00 AM
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-sand-800 mb-1.5">Delay Duration (Hours)</label>
              <select
                value={delayHours}
                onChange={(e) => {
                  setDelayHours(parseFloat(e.target.value));
                  setSimulationResult(null);
                }}
                className="w-full px-3.5 py-2.5 rounded-xl border border-sand-300 text-xs font-bold text-sand-900 bg-white focus:outline-none focus:ring-2 focus:ring-forest-600"
              >
                <option value={0.75}>0.75 Hours (45 Mins)</option>
                <option value={1.5}>1.5 Hours (90 Mins)</option>
                <option value={2.0}>2.0 Hours (120 Mins)</option>
                <option value={3.0}>3.0 Hours (180 Mins)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-sand-800 mb-1.5">Delay Reason</label>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Flight delay"
                className="w-full px-3.5 py-2.5 rounded-xl border border-sand-300 text-xs text-sand-900 bg-white focus:outline-none focus:ring-2 focus:ring-forest-600"
              />
            </div>
          </div>

          {!simulationResult ? (
            <button
              onClick={handleSimulate}
              disabled={isSimulating}
              className="w-full py-3 rounded-2xl text-xs font-bold bg-amber-600 text-white hover:bg-amber-700 transition-colors shadow-sm disabled:opacity-50"
            >
              {isSimulating ? 'Calculating Impact...' : '[ SIMULATE IMPACT ]'}
            </button>
          ) : (
            <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 space-y-3 animate-in fade-in duration-150">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-900">IMPACT PREVIEW</span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-200 text-amber-900">
                  Risk Level: {simulationResult.risk_level}
                </span>
              </div>

              <div className="grid grid-cols-4 gap-2 text-center text-xs">
                <div className="bg-white p-2 rounded-xl border border-amber-200">
                  <div className="text-[10px] text-sand-500">Interviews</div>
                  <div className="font-bold text-amber-900 text-sm">{simulationResult.affected_interviews_count}</div>
                </div>
                <div className="bg-white p-2 rounded-xl border border-amber-200">
                  <div className="text-[10px] text-sand-500">Students</div>
                  <div className="font-bold text-amber-900 text-sm">{simulationResult.affected_students_count}</div>
                </div>
                <div className="bg-white p-2 rounded-xl border border-amber-200">
                  <div className="text-[10px] text-sand-500">Panels</div>
                  <div className="font-bold text-amber-900 text-sm">{simulationResult.affected_panels_count}</div>
                </div>
                <div className="bg-white p-2 rounded-xl border border-amber-200">
                  <div className="text-[10px] text-sand-500">Rooms</div>
                  <div className="font-bold text-amber-900 text-sm">{simulationResult.affected_rooms_count}</div>
                </div>
              </div>

              <p className="text-xs text-amber-950 leading-relaxed">
                {simulationResult.explanation}
              </p>

              <button
                onClick={handleGenerateStrategies}
                disabled={isGenerating}
                className="w-full py-3 rounded-2xl text-xs font-bold bg-forest-800 text-white hover:bg-forest-900 transition-colors shadow-md disabled:opacity-50"
              >
                {isGenerating ? 'Generating Recovery Options...' : '[ Generate Recovery Strategies ]'}
              </button>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-rose-100 text-rose-800 text-xs font-semibold">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
