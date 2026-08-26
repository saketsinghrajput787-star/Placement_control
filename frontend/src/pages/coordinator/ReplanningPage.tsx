import React, { useState } from 'react';
import { useOperations } from '../../store/operationsStore';
import { RecoveryStrategyTable } from '../../components/disruptions/RecoveryStrategyTable';
import { ScheduleDiffView } from '../../components/disruptions/ScheduleDiffView';
import { Button } from '../../components/common/Button';
import { ShieldAlert, GitPullRequestDraft, CheckCircle2, Sparkles } from 'lucide-react';

export const ReplanningPage: React.FC = () => {
  const {
    replanningResult,
    applyReplanningStrategy,
    setIsDisruptionModalOpen,
    setIsDiffModalOpen,
    liveBannerMessage,
    isLoading
  } = useOperations();
  
  const [selectedStrategyType, setSelectedStrategyType] = useState<string | undefined>(undefined);

  const activeStrategy = replanningResult?.strategies_comparison.find(
    (s) => s.strategy_type === (selectedStrategyType || replanningResult.selected_strategy)
  ) || replanningResult?.strategies_comparison[0];

  const activeDiff =
    activeStrategy?.diff ||
    (selectedStrategyType && replanningResult?.strategy_diffs?.[selectedStrategyType]) ||
    replanningResult?.diff ||
    [];

  const isZeroDisplaced = replanningResult?.strategies_comparison.every((s) => s.moved_interviews === 0);

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
            onSelectStrategy={(strategyType) =>
              applyReplanningStrategy(replanningResult.replanning_run_id, strategyType)
            }
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
    </div>
  );
};
