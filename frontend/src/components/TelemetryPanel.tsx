import { Panel } from './Primitives';
import type { Telemetry } from '../types';

export function TelemetryPanel({ telemetry }: { telemetry: Telemetry }) {
  const rows: [string, string][] = [
    ['X', `${telemetry.x.toFixed(2)} m`],
    ['Y', `${telemetry.y.toFixed(2)} m`],
    ['HEADING', `${telemetry.heading_deg.toFixed(0)}°`],
    ['VELOCITY', `${telemetry.velocity.toFixed(2)} m/s`],
    ['DIST TRAVELLED', `${telemetry.distance_travelled_m.toFixed(1)} m`],
    ['DIST REMAINING', telemetry.distance_remaining_m != null ? `${telemetry.distance_remaining_m.toFixed(1)} m` : '—'],
    ['LOCALIZATION CONF.', `${(telemetry.localization_confidence * 100).toFixed(0)}%`],
    ['OBSTACLES', `${telemetry.obstacle_count} active`],
  ];

  return (
    <Panel title="TELEMETRY">
      <div className="grid grid-cols-2 gap-2.5">
        {rows.map(([label, value]) => (
          <div key={label} className="border border-panel-line rounded-[2px] p-2.5 flex flex-col gap-1">
            <span className="font-mono text-[10px] text-text-dim tracking-wide">{label}</span>
            <span className="font-mono text-[15px] font-semibold">{value}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
