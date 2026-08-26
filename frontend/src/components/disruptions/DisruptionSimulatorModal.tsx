import React, { useState, useEffect } from 'react';
import { useOperations } from '../../store/operationsStore';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Company } from '../../types';
import { apiClient } from '../../api/client';
import { ShieldAlert, AlertTriangle, Play, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const DisruptionSimulatorModal: React.FC = () => {
  const { isDisruptionModalOpen, setIsDisruptionModalOpen, setReplanningResult } = useOperations();
  const navigate = useNavigate();

  const [companies, setCompanies] = useState<Company[]>([]);
  const [eventType, setEventType] = useState('COMPANY_DELAY');
  const [selectedCompanyId, setSelectedCompanyId] = useState('');
  const [delaySlots, setDelaySlots] = useState(3);
  const [withdrawnCount, setWithdrawnCount] = useState(15);
  const [reason, setReason] = useState('Recruiter flight delay & panel hardware fault');
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationPreview, setSimulationPreview] = useState<any | null>(null);

  useEffect(() => {
    if (isDisruptionModalOpen) {
      apiClient.get('/companies').then((res) => {
        setCompanies(res.data);
        if (res.data.length > 0 && !selectedCompanyId) {
          setSelectedCompanyId(res.data[0].id);
        }
      }).catch(console.error);
    }
  }, [isDisruptionModalOpen]);

  const handleSimulate = async () => {
    setIsSimulating(true);
    try {
      const res = await apiClient.post('/disruptions/simulate', {
        event_type: eventType,
        target_entity_type: 'company',
        target_entity_id: selectedCompanyId,
        delay_slots: delaySlots,
        withdrawn_student_ids: [],
        reason: reason,
      });
      setSimulationPreview(res.data);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Simulation failed');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleProceedToReplanning = async () => {
    if (!simulationPreview) return;
    setIsSimulating(true);
    try {
      const replanRes = await apiClient.post('/replanning/run', {
        disruption_id: simulationPreview.disruption_id,
      });
      setReplanningResult(replanRes.data);
      setIsDisruptionModalOpen(false);
      navigate('/coordinator/replanning');
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to generate replanning strategies');
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <Modal
      isOpen={isDisruptionModalOpen}
      onClose={() => {
        setIsDisruptionModalOpen(false);
        setSimulationPreview(null);
      }}
      title="Disruption Simulator & Operational Replanner"
      subtitle="Safely simulate recruiter delays, panel outages, and student withdrawals without altering live database"
      maxWidth="2xl"
    >
      <div className="space-y-5">
        {/* Form Grid */}
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <label className="font-semibold text-sand-700 block mb-1">Disruption Event Type</label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full bg-sand-50 border border-sand-300 rounded-md p-2 text-sand-900 focus:ring-1 focus:ring-forest-600"
            >
              <option value="COMPANY_DELAY">Recruiter Delay (Hours)</option>
              <option value="PANEL_UNAVAILABLE">Panel Failure / Outage</option>
              <option value="STUDENT_WITHDRAWAL">Candidate Withdrawals</option>
              <option value="ROOM_UNAVAILABLE">Room Facility Outage</option>
            </select>
          </div>

          <div>
            <label className="font-semibold text-sand-700 block mb-1">Target Entity / Recruiter</label>
            <select
              value={selectedCompanyId}
              onChange={(e) => setSelectedCompanyId(e.target.value)}
              className="w-full bg-sand-50 border border-sand-300 rounded-md p-2 text-sand-900 focus:ring-1 focus:ring-forest-600"
            >
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} (Tier {c.priority_tier})
                </option>
              ))}
            </select>
          </div>

          {eventType === 'COMPANY_DELAY' && (
            <div>
              <label className="font-semibold text-sand-700 block mb-1">Delay Duration (Time Slots)</label>
              <select
                value={delaySlots}
                onChange={(e) => setDelaySlots(Number(e.target.value))}
                className="w-full bg-sand-50 border border-sand-300 rounded-md p-2 text-sand-900 focus:ring-1 focus:ring-forest-600"
              >
                <option value={1}>1 Slot (45 mins)</option>
                <option value={2}>2 Slots (1.5 hours)</option>
                <option value={3}>3 Slots (2.25 hours) - Demo Preset</option>
                <option value={4}>4 Slots (3.0 hours)</option>
              </select>
            </div>
          )}

          <div>
            <label className="font-semibold text-sand-700 block mb-1">Incident Rationale</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-sand-50 border border-sand-300 rounded-md p-2 text-sand-900 focus:ring-1 focus:ring-forest-600"
            />
          </div>
        </div>

        {/* Action button */}
        {!simulationPreview && (
          <div className="pt-2 flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsDisruptionModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="accent"
              icon={<Play className="w-4 h-4" />}
              onClick={handleSimulate}
              isLoading={isSimulating}
            >
              Simulate Impact (Non-destructive)
            </Button>
          </div>
        )}

        {/* Simulation Impact Preview Box */}
        {simulationPreview && (
          <div className="bg-sand-50 border border-amber-300 rounded-lg p-4 space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-sand-200 pb-2">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-status-warning" />
                <h4 className="text-sm font-bold text-sand-900">Simulated Impact Report</h4>
              </div>
              <span className="text-xs font-mono font-bold text-amber-800">
                Severity: {simulationPreview.severity}
              </span>
            </div>

            <p className="text-xs text-sand-700 leading-relaxed">{simulationPreview.explanation}</p>

            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="bg-white p-2 rounded border border-sand-200">
                <span className="text-sand-500 block text-[10px]">Affected Interviews</span>
                <span className="font-bold text-sand-900 text-sm font-mono">
                  {simulationPreview.affected_interviews_count}
                </span>
              </div>
              <div className="bg-white p-2 rounded border border-sand-200">
                <span className="text-sand-500 block text-[10px]">Affected Candidates</span>
                <span className="font-bold text-sand-900 text-sm font-mono">
                  {simulationPreview.affected_students_count}
                </span>
              </div>
              <div className="bg-white p-2 rounded border border-sand-200">
                <span className="text-sand-500 block text-[10px]">Expected Delay</span>
                <span className="font-bold text-sand-900 text-sm font-mono">
                  {simulationPreview.expected_delay_hours} hrs
                </span>
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSimulationPreview(null)}
              >
                Reset
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={<Sparkles className="w-4 h-4" />}
                onClick={handleProceedToReplanning}
                isLoading={isSimulating}
              >
                Generate 3 Multi-Recovery Strategies
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
