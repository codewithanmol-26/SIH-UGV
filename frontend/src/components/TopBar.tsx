import { StatusDot } from './Primitives';
import type { ConnectionState } from '../hooks/useTelemetryStream';
import type { NavigationState } from '../types';

export function TopBar({ state, connection }: { state: NavigationState; connection: ConnectionState }) {
  return (
    <div className="flex items-center justify-between pb-4 mb-4.5 border-b border-panel-line flex-wrap gap-3">
      <div>
        <div className="font-display font-bold text-[22px] tracking-wide">
          UGV<span className="text-amber">-MC</span> · MISSION CONSOLE
        </div>
        <div className="text-[13px] text-text-dim mt-0.5">
          Smart India Hackathon PS 26126 · GPS-denied, vision-guided outdoor navigation
        </div>
      </div>
      <div className="flex items-center gap-5 font-mono text-[12.5px]">
        <span className="flex items-center gap-2">
          <StatusDot tone="down" pulse={false} />
          GPS: DENIED (by design)
        </span>
        <span className="flex items-center gap-2">
          <StatusDot tone={connection === 'open' ? 'ok' : 'down'} pulse={connection === 'open'} />
          LINK: {connection === 'open' ? 'CONNECTED' : connection === 'connecting' ? 'CONNECTING…' : 'DISCONNECTED'}
        </span>
        <span className="flex items-center gap-2">
          <StatusDot tone={state === 'AUTONOMOUS' ? 'ok' : 'warn'} pulse={state === 'AUTONOMOUS'} />
          NAV: {state}
        </span>
      </div>
    </div>
  );
}
