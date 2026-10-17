import React, { useState, useMemo } from 'react';
import { AlertCircle, CheckCircle, Calendar, XCircle, ArrowUpRight, ShieldAlert, Cpu } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import type { AdvisoryOut } from '../../types/api';
import { useUpdateAdvisory } from '../../hooks/useEngineQueries';
import { useAuth } from '../../hooks/useAuth';

interface AdvisoryCardProps {
  advisory: AdvisoryOut;
  onNavigateComponent?: (componentId: string) => void;
  onSchedule?: (advisory: AdvisoryOut) => void;
  compact?: boolean;
}

export const AdvisoryCard: React.FC<AdvisoryCardProps> = ({
  advisory,
  onNavigateComponent,
  onSchedule,
  compact = false,
}) => {
  const { role } = useAuth();
  const updateMutation = useUpdateAdvisory();
  const [showDismissModal, setShowDismissModal] = useState(false);
  const [dismissReason, setDismissReason] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  const canAction = role === 'commander' || role === 'planner';

  const handleAccept = async () => {
    setActionError(null);
    try {
      await updateMutation.mutateAsync({
        id: advisory.advisory_id,
        payload: { status: 'accepted' },
      });
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to accept advisory');
    }
  };

  const handleDismissSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dismissReason.trim()) return;
    setActionError(null);
    try {
      await updateMutation.mutateAsync({
        id: advisory.advisory_id,
        payload: { status: 'dismissed', reason: dismissReason.trim() },
      });
      setShowDismissModal(false);
      setDismissReason('');
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to dismiss advisory');
    }
  };

  const explanationDrivers: Array<{ feature: string; impact: number }> = useMemo(() => {
    const raw =
      advisory.explanation?.top_shap_factors ||
      advisory.explanation?.top_factors ||
      advisory.explanation?.top_drivers ||
      [];
    return raw.map((item) => ({
      feature: item.feature,
      impact:
        'shap_impact' in item && typeof item.shap_impact === 'number'
          ? item.shap_impact
          : 'impact' in item && typeof item.impact === 'number'
          ? item.impact
          : 0,
    }));
  }, [advisory.explanation]);

  return (
    <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-5 shadow-ap-card relative overflow-hidden flex flex-col justify-between hover:shadow-ap-floating hover:border-[#D8D2E5] transition-all duration-200">
      {/* Top Banner & Priority */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center space-x-2">
            <StatusBadge status={advisory.priority} size="md" />
            <StatusBadge status={advisory.status} size="sm" />
            {advisory.spare_status && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#E0F8FA] text-[#0E7490] border border-[#B6EFF4]">
                Spare: {advisory.spare_status}
              </span>
            )}
          </div>
          <span className="text-[11px] font-mono text-[#6B5B84]">{advisory.as_of_date}</span>
        </div>

        {/* Title / Action */}
        <h4 className="text-base font-semibold text-[#3B1D5E] flex items-center gap-1.5">
          <ShieldAlert className="w-4 h-4 text-[#D97706] shrink-0" />
          <span>{advisory.action}</span>
        </h4>

        {/* Component & Airframe info */}
        <div className="mt-2 text-xs font-mono text-[#6B5B84] flex flex-wrap gap-x-4 gap-y-1">
          <span>
            Airframe:{' '}
            <strong className="text-[#3B1D5E]">{advisory.tail_code || advisory.aircraft_id || 'N/A'}</strong>
          </span>
          <span>
            System: <strong className="text-[#3B1D5E]">{advisory.system_name || 'N/A'}</strong>
          </span>
          <span className="flex items-center gap-1">
            Component:{' '}
            <button
              onClick={() => onNavigateComponent && onNavigateComponent(advisory.component_id)}
              className="text-[#7C3AED] hover:text-[#5B21B6] hover:underline flex items-center font-bold"
            >
              {advisory.component_name || advisory.component_id}
              <ArrowUpRight className="w-3 h-3 ml-0.5" />
            </button>
          </span>
        </div>

        {/* Expected Downtime */}
        {advisory.expected_downtime_days !== null && advisory.expected_downtime_days !== undefined && (
          <div className="mt-2 text-xs font-mono text-[#6B5B84]">
            Estimated turnaround loss:{' '}
            <span className="text-[#3B1D5E] font-bold">{advisory.expected_downtime_days} days</span>
          </div>
        )}

        {/* SHAP Drivers / Explanation */}
        {!compact && explanationDrivers.length > 0 && (
          <div className="mt-3.5 pt-3 border-t border-[#EDE9F5]">
            <span className="text-[11px] uppercase tracking-wider text-[#6B5B84] font-semibold block mb-1.5 flex items-center gap-1">
              <Cpu className="w-3.5 h-3.5 text-[#7C3AED]" />
              Primary Degradation Drivers (ML Attribution)
            </span>
            <div className="space-y-1.5">
              {explanationDrivers.slice(0, 3).map((driver, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs font-mono">
                  <span className="text-[#6B5B84] truncate max-w-[200px]">{driver.feature}</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-24 bg-[#F4F2FB] h-1.5 rounded-full overflow-hidden border border-[#E6E2F0]">
                      <div
                        className="bg-gradient-to-r from-[#1DE9C0] to-[#7C3AED] h-full rounded-full"
                        style={{ width: `${Math.min(100, Math.abs(driver.impact) * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#7C3AED] w-8 text-right font-bold">
                      {driver.impact > 0 ? `+${driver.impact.toFixed(2)}` : driver.impact.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {advisory.dismiss_reason && (
          <div className="mt-2 p-2.5 bg-[#FEF2F2] border border-[#FECACA] rounded-[10px] text-xs font-mono text-[#DC2626]">
            <strong>Dismissal Reason:</strong> {advisory.dismiss_reason}
          </div>
        )}

        {actionError && (
          <div className="mt-2 p-2.5 bg-[#FEF2F2] border border-[#FECACA] rounded-[10px] text-xs text-[#DC2626]">
            {actionError}
          </div>
        )}
      </div>

      {/* Action Buttons (Human-in-the-loop workflow) */}
      {advisory.status === 'proposed' && (
        <div className="mt-4 pt-3 border-t border-[#EDE9F5] flex items-center justify-between gap-2">
          {canAction ? (
            <>
              <button
                onClick={handleAccept}
                disabled={updateMutation.isPending}
                className="flex-1 py-1.5 px-3 bg-[#1DE9C0] hover:bg-[#18D4AD] text-[#3B1D5E] rounded-[10px] text-xs font-semibold flex items-center justify-center gap-1 transition shadow-sm"
              >
                <CheckCircle className="w-3.5 h-3.5" /> Accept
              </button>

              <button
                onClick={() => (onSchedule ? onSchedule(advisory) : undefined)}
                className="flex-1 py-1.5 px-3 bg-[#F4EBFF] hover:bg-[#EDE9F5] text-[#7C3AED] border border-[#E5D0FA] rounded-[10px] text-xs font-semibold flex items-center justify-center gap-1 transition shadow-sm"
              >
                <Calendar className="w-3.5 h-3.5" /> Schedule
              </button>

              <button
                onClick={() => setShowDismissModal(true)}
                disabled={updateMutation.isPending}
                className="py-1.5 px-2.5 bg-[#F4F2FB] hover:bg-[#FEF2F2] text-[#6B5B84] hover:text-[#DC2626] border border-[#E6E2F0] hover:border-[#FECACA] rounded-[10px] text-xs font-mono transition"
                title="Dismiss with reason"
              >
                <XCircle className="w-3.5 h-3.5" />
              </button>
            </>
          ) : (
            <span className="text-[11px] font-mono text-[#8F7FA8] italic">
              Read-only view (Requires Planner / Commander role to accept or schedule)
            </span>
          )}
        </div>
      )}

      {/* Dismiss Reason Modal */}
      {showDismissModal && (
        <div className="fixed inset-0 bg-[#3B1D5E]/30 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleDismissSubmit}
            className="bg-white border border-[#E6E2F0] rounded-[20px] p-6 max-w-md w-full shadow-ap-floating space-y-4"
          >
            <div className="flex items-center space-x-2 text-[#DC2626]">
              <AlertCircle className="w-5 h-5" />
              <h3 className="font-semibold text-sm text-[#3B1D5E]">
                Engineering Justification Required
              </h3>
            </div>
            <p className="text-xs text-[#6B5B84]">
              Provide an engineering rationale for dismissing advisory #{advisory.advisory_id}:
            </p>
            <textarea
              required
              rows={3}
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              placeholder="e.g. Component inspected visually and verified nominal; sensor drift suspected."
              className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] p-2.5 text-xs text-[#3B1D5E] focus:outline-none focus:border-[#7C3AED] focus:bg-white"
            />
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowDismissModal(false)}
                className="px-3.5 py-1.5 bg-[#F4F2FB] hover:bg-[#EDE9F5] text-[#6B5B84] rounded-[10px] text-xs border border-[#E6E2F0]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!dismissReason.trim() || updateMutation.isPending}
                className="px-4 py-1.5 bg-[#DC2626] hover:bg-[#B91C1C] disabled:opacity-50 text-white rounded-[10px] text-xs font-semibold shadow-sm"
              >
                Confirm Dismissal
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
