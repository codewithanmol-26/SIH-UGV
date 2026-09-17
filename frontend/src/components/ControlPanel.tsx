import { Panel } from './Primitives';
import type { NavigationState, WorldPoint } from '../types';

interface ControlPanelProps {
  state: NavigationState;
  pendingDestination: WorldPoint | null;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onEmergencyStop: () => void;
  busy: boolean;
}

export function ControlPanel({
  state, pendingDestination, onStart, onPause, onResume, onStop, onEmergencyStop, busy,
}: ControlPanelProps) {
  const canStart = state === 'READY' && pendingDestination !== null;
  const canPause = state === 'AUTONOMOUS' || state === 'REROUTING';
  const canResume = state === 'PAUSED' || state === 'SAFE_STOP';
  const canStop = !['IDLE', 'STOPPED', 'EMERGENCY_STOP'].includes(state);

  return (
    <Panel title="CONTROL">
      <p className="text-[11px] font-mono text-text-dim mb-3 leading-relaxed">
        The operator sets the destination and issues high-level commands. The navigation
        system decides how to get there — steering is never manual.
      </p>
      <div className="grid grid-cols-2 gap-2">
        <ControlButton label="START" tone="primary" disabled={busy || !canStart} onClick={onStart} />
        <ControlButton label="PAUSE" tone="neutral" disabled={busy || !canPause} onClick={onPause} />
        <ControlButton label="RESUME" tone="primary" disabled={busy || !canResume} onClick={onResume} />
        <ControlButton label="STOP" tone="neutral" disabled={busy || !canStop} onClick={onStop} />
      </div>
      <button
        onClick={onEmergencyStop}
        disabled={busy || state === 'EMERGENCY_STOP'}
        className="w-full mt-2 font-mono text-[11.5px] tracking-wide py-2.5 rounded-[2px] border border-rust-dim text-rust bg-transparent hover:bg-rust-dim/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        EMERGENCY STOP
      </button>
      {!pendingDestination && state === 'READY' && (
        <p className="text-[11px] font-mono text-amber mt-2.5">Click the map to set Point B before starting.</p>
      )}
    </Panel>
  );
}

function ControlButton({
  label, tone, disabled, onClick,
}: { label: string; tone: 'primary' | 'neutral'; disabled: boolean; onClick: () => void }) {
  const toneClasses = tone === 'primary'
    ? 'border-sage-dim text-sage hover:bg-sage-dim/20'
    : 'border-panel-line text-text hover:bg-white/5';
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`font-mono text-[11.5px] tracking-wide py-2.5 rounded-[2px] border bg-transparent disabled:opacity-40 disabled:cursor-not-allowed transition-colors ${toneClasses}`}
    >
      {label}
    </button>
  );
}
