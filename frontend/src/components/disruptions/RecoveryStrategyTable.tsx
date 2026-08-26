import React from 'react';
import { RecoveryStrategyOption } from '../../types';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Check, Star } from 'lucide-react';

interface RecoveryStrategyTableProps {
  strategies: RecoveryStrategyOption[];
  onSelectStrategy: (strategyType: string) => void;
  onViewSchedule?: (strategy: RecoveryStrategyOption) => void;
  selectedStrategyType?: string;
  isLoading?: boolean;
}

export const RecoveryStrategyTable: React.FC<RecoveryStrategyTableProps> = ({
  strategies,
  onSelectStrategy,
  onViewSchedule,
  selectedStrategyType,
  isLoading = false,
}) => {
  return (
    <div className="bg-white border border-sand-300 rounded-lg overflow-hidden shadow-sm">
      <div className="px-5 py-4 border-b border-sand-200 bg-sand-50 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-sand-900">Multi-Recovery Strategy Optimization Comparison</h3>
          <p className="text-xs text-sand-600">
            CP-SAT generated mathematical recovery paths evaluating schedule churn vs waiting time
          </p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full ops-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Interviews Moved</th>
              <th>Stability %</th>
              <th>Student Waiting</th>
              <th>Panel Utilization</th>
              <th>Room Utilization</th>
              <th>Scheduled</th>
              <th>Overall Score</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {strategies.map((strat) => {
              const isSelected = selectedStrategyType === strat.strategy_type;
              return (
                <tr
                  key={strat.strategy_type}
                  className={
                    isSelected
                      ? 'bg-forest-50/70 hover:bg-forest-50'
                      : strat.is_recommended
                      ? 'bg-amber-50/40 hover:bg-amber-50/70'
                      : 'hover:bg-sand-50'
                  }
                >
                  <td>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sand-900">{strat.strategy_title}</span>
                      {strat.is_recommended && (
                        <Badge variant="accent" size="sm" dot>
                          Recommended
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-sand-500 mt-0.5 max-w-sm">{strat.explanation}</p>
                  </td>
                  <td className="font-mono font-bold text-sand-800 text-xs">
                    {strat.moved_interviews} <span className="font-normal text-sand-500">moved</span>
                  </td>
                  <td>
                    <span className="font-mono font-bold text-forest-800 text-sm">
                      {strat.stability_score.toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <div className="flex flex-col gap-0.5">
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded w-fit ${
                          strat.waiting_time_level?.toUpperCase() === 'LOW'
                            ? 'bg-green-100 text-green-800'
                            : strat.waiting_time_level?.toUpperCase() === 'MEDIUM'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {strat.waiting_time_level}
                      </span>
                      {strat.student_waiting_minutes !== undefined && (
                        <span className="text-[10px] text-sand-500 font-mono">
                          ~{Math.round(strat.student_waiting_minutes)} mins avg
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="font-mono text-xs text-sand-700">{strat.panel_utilization_pct.toFixed(1)}%</td>
                  <td className="font-mono text-xs text-sand-700">{strat.room_utilization_pct.toFixed(1)}%</td>
                  <td className="font-mono font-bold text-xs text-sand-800">
                    {strat.scheduled_interviews ?? (strat.unchanged_interviews + strat.moved_interviews)}
                  </td>
                  <td>
                    <div className="flex items-center gap-1 font-mono font-bold text-sand-900 text-base">
                      {strat.overall_score.toFixed(1)}
                      {strat.is_recommended && <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />}
                    </div>
                  </td>
                  <td>
                    <div className="flex items-center gap-1.5">
                      {onViewSchedule && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onViewSchedule(strat)}
                        >
                          View Schedule
                        </Button>
                      )}
                      <Button
                        variant={strat.is_recommended ? 'primary' : 'outline'}
                        size="sm"
                        icon={<Check className="w-3.5 h-3.5" />}
                        onClick={() => onSelectStrategy(strat.strategy_type)}
                        isLoading={isLoading}
                      >
                        Apply
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
