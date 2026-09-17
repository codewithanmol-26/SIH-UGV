import { Panel } from './Primitives';
import type { Telemetry } from '../types';

interface CameraPanelProps {
  frameDataUri: string | null;
  telemetry: Telemetry;
  connectionOpen: boolean;
}

export function CameraPanel({ frameDataUri, telemetry, connectionOpen }: CameraPanelProps) {
  return (
    <Panel title="FORWARD CAMERA · PERCEPTION OVERLAY">
      <div className="relative rounded-[2px] overflow-hidden border border-panel-line aspect-video bg-[#1D2116] flex items-center justify-center">
        {frameDataUri ? (
          <img src={frameDataUri} alt="Live camera feed with detection overlay" className="w-full h-full object-cover" />
        ) : (
          <span className="font-mono text-xs text-text-dim">
            {connectionOpen ? 'Waiting for first frame…' : 'No connection to backend'}
          </span>
        )}
      </div>

      <div className="flex justify-between mt-2.5 font-mono text-[11px] text-text-dim">
        <span className="flex items-center gap-1.5">
          <span className={`inline-block w-2 h-2 rounded-full ${connectionOpen ? 'bg-rust shadow-[0_0_6px_var(--color-rust)]' : 'bg-text-dim'}`} />
          FEED {telemetry.camera_fps.toFixed(1)}fps
        </span>
        <span>Obstacles: {telemetry.obstacle_count} active</span>
      </div>

      <div className="grid grid-cols-2 gap-3 mt-4">
        <Readout label="AI LATENCY" value={`${telemetry.ai_latency_ms.toFixed(0)} ms`} />
        <Readout label="INFERENCE FPS" value={telemetry.inference_fps.toFixed(1)} />
      </div>
    </Panel>
  );
}

function Readout({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-panel-line rounded-[2px] p-2.5 flex flex-col gap-1">
      <span className="font-mono text-[10px] text-text-dim tracking-wide">{label}</span>
      <span className="font-mono text-base font-semibold">{value}</span>
    </div>
  );
}
