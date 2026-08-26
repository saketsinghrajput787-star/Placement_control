import React, { useEffect, useState } from 'react';
import { useOperations } from '../../store/operationsStore';
import { apiClient } from '../../api/client';
import { DisruptionOut } from '../../types';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { ShieldAlert, Play, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const DisruptionsPage: React.FC = () => {
  const { setIsDisruptionModalOpen, setReplanningResult } = useOperations();
  const [disruptions, setDisruptions] = useState<DisruptionOut[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const loadDisruptions = async () => {
    try {
      const res = await apiClient.get('/disruptions');
      setDisruptions(res.data);
    } catch (e) {
      console.error('Failed to load disruptions', e);
    }
  };

  useEffect(() => {
    loadDisruptions();
  }, []);

  const handleClearDisruptions = async () => {
    if (!window.confirm('Are you sure you want to clear all disruption logs?')) return;
    try {
      await apiClient.delete('/disruptions/clear');
      setDisruptions([]);
      setReplanningResult(null);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to clear disruption logs');
    }
  };

  const handleReplanDisruption = async (disruptionId: string) => {
    setIsLoading(true);
    try {
      const res = await apiClient.post('/replanning/run', { disruption_id: disruptionId });
      setReplanningResult(res.data);
      navigate('/coordinator/replanning');
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Replanning failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <div>
          <h2 className="text-xl font-bold text-sand-900 tracking-tight">OPERATIONAL DISRUPTIONS LOG</h2>
          <p className="text-xs text-sand-600 mt-1">
            Historical audit trail of simulated and applied delays, outages, and candidate withdrawals
          </p>
        </div>

        <div className="flex items-center gap-2">
          {disruptions.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              icon={<Trash2 className="w-4 h-4 text-red-600" />}
              onClick={handleClearDisruptions}
            >
              Clear Log
            </Button>
          )}
          <Button
            variant="accent"
            size="sm"
            icon={<ShieldAlert className="w-4 h-4" />}
            onClick={() => setIsDisruptionModalOpen(true)}
          >
            Simulate New Disruption
          </Button>
        </div>
      </div>

      <div className="bg-white border border-sand-300 rounded-lg overflow-hidden shadow-sm">
        <table className="w-full ops-table">
          <thead>
            <tr>
              <th>Incident Type</th>
              <th>Target Entity</th>
              <th>Severity</th>
              <th>Parameters</th>
              <th>Status</th>
              <th>Recorded At</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {disruptions.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-sand-500 italic">
                  No disruptions recorded. Use the simulator above to test operational edge-cases.
                </td>
              </tr>
            ) : (
              disruptions.map((d) => (
                <tr key={d.id} className="hover:bg-sand-50">
                  <td className="font-semibold text-sand-900">{d.event_type.replace('_', ' ')}</td>
                  <td className="capitalize font-mono text-xs text-sand-700">{d.target_entity_type}</td>
                  <td>
                    <Badge variant={d.severity === 'CRITICAL' ? 'critical' : d.severity === 'HIGH' ? 'warning' : 'info'} size="sm">
                      {d.severity}
                    </Badge>
                  </td>
                  <td className="text-xs text-sand-600 font-mono">
                    {d.parameters.delay_slots ? `${d.parameters.delay_slots} slots delay` : 'Resource outage'}
                  </td>
                  <td>
                    <Badge variant={d.status === 'APPLIED' ? 'healthy' : 'neutral'} size="sm">
                      {d.status}
                    </Badge>
                  </td>
                  <td className="text-xs text-sand-500 font-mono">
                    {new Date(d.created_at).toLocaleTimeString()}
                  </td>
                  <td>
                    <Button
                      variant="outline"
                      size="sm"
                      icon={<Play className="w-3 h-3" />}
                      onClick={() => handleReplanDisruption(d.id)}
                      isLoading={isLoading}
                    >
                      Replan
                    </Button>
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
