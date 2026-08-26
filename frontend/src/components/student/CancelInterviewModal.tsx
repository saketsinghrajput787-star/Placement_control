import React, { useState } from 'react';
import { Interview } from '../../types';
import { apiClient } from '../../api/client';
import { useOperations } from '../../store/operationsStore';

interface Props {
  interview: Interview | null;
  onClose: () => void;
}

const REASONS = [
  "Personal reason",
  "Accepted another opportunity",
  "Unable to attend",
  "Scheduling conflict",
  "Academic commitment",
  "Other"
];

export const CancelInterviewModal: React.FC<Props> = ({ interview, onClose }) => {
  const { loadDashboardData, setIsDiffModalOpen, setLiveBannerMessage } = useOperations();
  const [selectedReason, setSelectedReason] = useState<string>(REASONS[0]);
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!interview) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const res = await apiClient.post(`/interviews/${interview.id}/cancel`, {
        reason: selectedReason,
        comment: comment
      });

      setLiveBannerMessage(`Interview cancelled. Schedule updated to Version ${res.data.new_version_number}.`);
      await loadDashboardData();
      onClose();
      setIsDiffModalOpen(true);
    } catch (err: any) {
      console.error('Failed to cancel interview', err);
      setError(err.response?.data?.detail || 'Failed to cancel interview');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-sand-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-3xl border border-sand-300 shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="p-6 bg-rose-50 border-b border-rose-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-rose-100 flex items-center justify-center text-rose-700 font-bold">
              ⚠️
            </div>
            <div>
              <h3 className="text-lg font-black text-rose-950">Cancel Interview?</h3>
              <p className="text-xs text-rose-700">Confirm cancellation details below</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-rose-400 hover:text-rose-700 hover:bg-rose-100 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content & Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          
          {/* Details Snapshot */}
          <div className="p-4 rounded-2xl bg-sand-50 border border-sand-200 text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-sand-500">Company:</span>
              <span className="font-bold text-sand-900">{interview.company_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sand-500">Time Slot:</span>
              <span className="font-bold text-sand-900">{interview.start_time_str} - {interview.end_time_str}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sand-500">Assigned Location:</span>
              <span className="font-bold text-sand-900">Room {interview.room_code} • Panel {interview.panel_code}</span>
            </div>
          </div>

          {/* Warning Note */}
          <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs leading-relaxed font-medium">
            ⚠️ <strong>Warning:</strong> Cancelling this interview will free slot {interview.start_time_str} for another student and trigger automated replanning.
          </div>

          {/* Reason Selection */}
          <div>
            <label className="block text-xs font-bold text-sand-800 mb-1.5">Select Cancellation Reason</label>
            <select
              value={selectedReason}
              onChange={(e) => setSelectedReason(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-sand-300 text-xs font-semibold text-sand-900 bg-white focus:outline-none focus:ring-2 focus:ring-rose-500"
            >
              {REASONS.map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          {/* Optional Comment */}
          <div>
            <label className="block text-xs font-bold text-sand-800 mb-1.5">Additional Comment (Optional)</label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Provide additional details..."
              rows={2}
              className="w-full px-3.5 py-2.5 rounded-xl border border-sand-300 text-xs text-sand-900 bg-white focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-rose-100 text-rose-800 text-xs font-semibold">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl text-xs font-bold bg-sand-200 text-sand-800 hover:bg-sand-300 transition-colors"
            >
              Keep Interview
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2.5 rounded-xl text-xs font-bold bg-rose-600 text-white hover:bg-rose-700 transition-colors shadow-sm disabled:opacity-50"
            >
              {isSubmitting ? 'Cancelling...' : 'Confirm Cancellation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
