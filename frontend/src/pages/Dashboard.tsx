import { useState, useCallback } from 'react';
import { useTelemetryStream } from '../hooks/useTelemetryStream';
import { api } from '../services/api';
import type { WorldPoint } from '../types';
import { TopBar } from '../components/TopBar';
import { MapPanel } from '../components/MapPanel';
import { CameraPanel } from '../components/CameraPanel';
import { ControlPanel } from '../components/ControlPanel';
import { StatusPanel } from '../components/StatusPanel';
import { TelemetryPanel } from '../components/TelemetryPanel';
import { LogPanel } from '../components/LogPanel';

const EMPTY_TELEMETRY = {
  x: 0, y: 0, heading_deg: 0, velocity: 0, distance_travelled_m: 0,
  distance_remaining_m: null, obstacle_count: 0, camera_fps: 0,
  inference_fps: 0, ai_latency_ms: 0, localization_confidence: 0,
};

const EMPTY_MODULES = {
  camera: 'NOT_IMPLEMENTED' as const,
  perception: 'NOT_IMPLEMENTED' as const,
  traversability: 'NOT_IMPLEMENTED' as const,
  localization: 'NOT_IMPLEMENTED' as const,
  planner: 'NOT_IMPLEMENTED' as const,
  controller: 'NOT_IMPLEMENTED' as const,
  communication: 'NOT_IMPLEMENTED' as const,
};

export function Dashboard() {
  const { message, connection } = useTelemetryStream();
  const [pendingDestination, setPendingDestination] = useState<WorldPoint | null>(null);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const state = message?.state ?? 'IDLE';
  const telemetry = message?.telemetry ?? EMPTY_TELEMETRY;
  const modules = message?.system_status ?? EMPTY_MODULES;
  const logs = message?.logs ?? [];
  const trajectory = message?.trajectory ?? [];
  const route = message?.route ?? [];
  const destination = message?.destination ?? null;
  const position = message?.position ?? { x: 0, y: 0, heading_deg: 0, localization_confidence: 0 };

  const runCommand = useCallback(async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setErrorMsg(null);
    try {
      await fn();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Command failed');
    } finally {
      setBusy(false);
    }
  }, []);

  const handlePickDestination = useCallback((point: WorldPoint) => {
    setPendingDestination(point);
    void runCommand(() => api.setDestination(point[0], point[1]));
  }, [runCommand]);

  return (
    <div className="max-w-[1280px] mx-auto p-5">
      <TopBar state={state} connection={connection} />

      {errorMsg && (
        <div className="mb-4 font-mono text-[12px] text-rust border border-rust-dim rounded-[2px] px-3 py-2 bg-rust-dim/10">
          {errorMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr_300px] gap-4 items-start">
        <div className="flex flex-col gap-4">
          <MapPanel
            currentPosition={position}
            trajectory={trajectory}
            route={route}
            destination={destination}
            pendingDestination={pendingDestination}
            onPickDestination={handlePickDestination}
          />
          <ControlPanel
            state={state}
            pendingDestination={destination ?? pendingDestination}
            onStart={() => runCommand(api.start)}
            onPause={() => runCommand(api.pause)}
            onResume={() => runCommand(api.resume)}
            onStop={() => runCommand(() => { setPendingDestination(null); return api.stop(); })}
            onEmergencyStop={() => runCommand(api.emergencyStop)}
            busy={busy}
          />
        </div>

        <div className="flex flex-col gap-4">
          <CameraPanel
            frameDataUri={message?.camera_frame ?? null}
            telemetry={telemetry}
            connectionOpen={connection === 'open'}
          />
          <TelemetryPanel telemetry={telemetry} />
        </div>

        <div className="flex flex-col gap-4">
          <StatusPanel state={state} modules={modules} />
          <LogPanel logs={logs} />
        </div>
      </div>
    </div>
  );
}
