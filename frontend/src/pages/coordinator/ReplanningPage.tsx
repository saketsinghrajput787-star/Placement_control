import React, { useState } from 'react';
import { useOperations } from '../../store/operationsStore';
import { RecoveryStrategyTable } from '../../components/disruptions/RecoveryStrategyTable';
import { ScheduleDiffView } from '../../components/disruptions/ScheduleDiffView';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { ShieldAlert, GitPullRequestDraft, CheckCircle2, Sparkles, AlertTriangle, ArrowRight } from 'lucide-react';
import { RecoveryStrategyOption } from '../../types';
import { useNavigate } from 'react-router-dom';

export const ReplanningPage: React.FC = () => {
  const {
    replanningResult,
    applyReplanningStrategy,
    setIsDisruptionModalOpen,
    setIsDiffModalOpen,
    liveBannerMessage,
    isLoading
  } = useOperations();
  const navigate = useNavigate();
  
  const [selectedStrategyType, setSelectedStrategyType] = useState<string | undefined>(undefined);
  const [strategyToApply, setStrategyToApply] = useState<RecoveryStrategyOption | null>(null);

  const activeStrategy = replanningResult?.strategies_comparison.find(
    (s) => s.strategy_type === (selectedStrategyType || replanningResult.selected_strategy)
  ) || replanningResult?.strategies_comparison[0];

  const activeDiff =
    activeStrategy?.diff ||
    (selectedStrategyType && replanningResult?.strategy_diffs?.[selectedStrategyType]) ||
    replanningResult?.diff ||
    [];

  const isZeroDisplaced = replanningResult?.strategies_comparison.every((s) => s.moved_interviews === 0);

  const handleConfirmApply = async () => {
    if (!strategyToApply || !replanningResult) return;
    const stratType = strategyToApply.strategy_type;
    setStrategyToApply(null);
    await applyReplanningStrategy(replanningResult.replanning_run_id, stratType);
    navigate('/coordinator/dashboard');
  };


  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <div>
          <h2 className="text-xl font-bold text-sand-900 tracking-tight">MINIMAL-DISRUPTION REPLANNING ENGINE</h2>
          <p className="text-xs text-sand-600 mt-1">
            Mathematical optimization re-evaluating displaced interviews while preserving schedule stability &gt; 90%
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsDiffModalOpen(true)}
          >
            Inspect Schedule Diff
          </Button>

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

      {/* Live Application Toast Message */}
      {liveBannerMessage && (
        <div className="bg-forest-50 border border-forest-300 p-4 rounded-lg flex items-center justify-between text-xs text-forest-900 animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-forest-700 shrink-0" />
            <span className="font-semibold">{liveBannerMessage}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setIsDiffModalOpen(true)}>
            View Version Diff
          </Button>
        </div>
      )}

      {!replanningResult ? (
        <div className="bg-white border border-sand-300 rounded-lg p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-forest-50 text-forest-700 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-sand-900">Current Schedule is Fully Stabilized</h3>
          <p className="text-xs text-sand-600 max-w-md mx-auto">
            Zero unresolved disruptions detected. Launch the Disruption Simulator to test recruiter delays, panel outages, or student candidate withdrawals and generate dynamic recovery plans.
          </p>
          <Button
            variant="primary"
            size="sm"
            icon={<ShieldAlert className="w-4 h-4" />}
            onClick={() => setIsDisruptionModalOpen(true)}
            className="mt-2"
          >
            Launch Disruption Simulator
          </Button>
        </div>
      ) : (
        <div className="space-y-6 animate-fadeIn">
          
          {/* Zero displaced warning notice */}
          {isZeroDisplaced && (
            <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg flex items-center justify-between text-xs text-amber-900">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
                <span>
                  <b>Schedule is 100% optimal with 0 displaced interviews.</b> To test recovery plans with candidate movements, click <b>Simulate Disruption</b> below.
                </span>
              </div>
              <Button variant="accent" size="sm" onClick={() => setIsDisruptionModalOpen(true)}>
                Simulate Disruption
              </Button>
            </div>
          )}

          {/* Recovery Strategy Comparison Table */}
          <RecoveryStrategyTable
            strategies={replanningResult.strategies_comparison}
            onSelectStrategy={(strategyType) => {
              const strat = replanningResult.strategies_comparison.find(s => s.strategy_type === strategyType);
              if (strat) setStrategyToApply(strat);
              else applyReplanningStrategy(replanningResult.replanning_run_id, strategyType);
            }}
            onViewSchedule={(strat) => setSelectedStrategyType(strat.strategy_type)}
            selectedStrategyType={activeStrategy?.strategy_type}
            isLoading={isLoading}
          />

          {/* Active Strategy Candidate Banner */}
          {activeStrategy && (
            <div className="bg-sand-50 p-4 border border-sand-300 rounded-lg flex items-center justify-between">
              <div>
                <span className="text-xs font-mono uppercase text-sand-500 font-semibold block">Inspecting Candidate Recovery Schedule</span>
                <h4 className="text-sm font-bold text-sand-900">{activeStrategy.strategy_title}</h4>
              </div>
              <div className="flex items-center gap-3 text-xs font-mono">
                <span>Moved: <b>{activeStrategy.moved_interviews}</b></span>
                <span>Stability: <b>{activeStrategy.stability_score.toFixed(1)}%</b></span>
                <span>Waiting: <b>{activeStrategy.waiting_time_level} (~{Math.round(activeStrategy.student_waiting_minutes || 0)}m)</b></span>
                <span>Score: <b>{activeStrategy.overall_score.toFixed(1)}</b></span>
              </div>
            </div>
          )}

          {/* Schedule Diff */}
          <ScheduleDiffView
            diff={activeDiff}
            stabilityScore={activeStrategy?.stability_score ?? replanningResult.stability_score}
          />
        </div>
      )}

      {/* Confirmation Modal Before Applying Strategy */}
      {strategyToApply && (
        <Modal
          isOpen={true}
          onClose={() => setStrategyToApply(null)}
          title={`Apply ${strategyToApply.strategy_title}?`}
          subtitle="Confirm applying this mathematical recovery schedule to live database and broadcasting updates"
          maxWidth="lg"
        >
          <div className="space-y-4">
            <div className="bg-sand-50 p-4 rounded-lg border border-sand-300 text-xs space-y-2">
              <div className="flex justify-between items-center py-1 border-b border-sand-200">
                <span className="text-sand-600 font-medium">Strategy Type:</span>
                <span className="font-bold text-sand-900">{strategyToApply.strategy_title}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-sand-200">
                <span className="text-sand-600 font-medium">Interviews Moved:</span>
                <span className="font-bold text-amber-800">{strategyToApply.moved_interviews} slots</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-sand-200">
                <span className="text-sand-600 font-medium">Interviews Preserved Unchanged:</span>
                <span className="font-bold text-forest-800">{strategyToApply.unchanged_interviews} slots</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-sand-200">
                <span className="text-sand-600 font-medium">Schedule Stability:</span>
                <span className="font-bold text-forest-800">{strategyToApply.stability_score.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-sand-200">
                <span className="text-sand-600 font-medium">Avg Student Waiting Time:</span>
                <span className="font-bold text-sand-800">~{Math.round(strategyToApply.student_waiting_minutes || 0)} minutes</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-sand-600 font-medium">Overall Composite Score:</span>
                <span className="font-bold text-sand-900 text-sm">{strategyToApply.overall_score.toFixed(1)} / 100</span>
              </div>
            </div>

            <p className="text-xs text-sand-600">
              Applying this schedule will create a new official Schedule Version and instantly update all Coordinator, Company, and Student portals.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-sand-200">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStrategyToApply(null)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={<ArrowRight className="w-4 h-4" />}
                onClick={handleConfirmApply}
                isLoading={isLoading}
              >
                Confirm & Apply Recovery Schedule
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
