import { Panel, StatusDot } from './Primitives';
import type { ModuleStatus, NavigationState, SystemModuleStatus } from '../types';

const STATE_TONE: Record<NavigationState, 'ok' | 'warn' | 'down'> = {
  IDLE: 'warn',
  INITIALIZING: 'warn',
  READY: 'ok',
  AUTONOMOUS: 'ok',
  PAUSED: 'warn',
  REROUTING: 'warn',
  SAFE_STOP: 'down',
  STOPPED: 'warn',
  EMERGENCY_STOP: 'down',
  DESTINATION_REACHED: 'ok',
  CONNECTION_LOST: 'down',
  ERROR: 'down',
};

const MODULE_LABEL: Record<keyof SystemModuleStatus, string> = {
  camera: 'Camera',
  perception: 'Perception (YOLO26)',
  traversability: 'Traversability',
  localization: 'Visual localization',
  planner: 'Path planner',
  controller: 'Motor controller',
  communication: 'Communication',
};

const STATUS_TONE: Record<ModuleStatus, 'ok' | 'warn' | 'down'> = {
  ACTIVE: 'ok',
  SIMULATED: 'warn',
  NOT_IMPLEMENTED: 'down',
};

export function StatusPanel({ state, modules }: { state: NavigationState; modules: SystemModuleStatus }) {
  return (
    <Panel title="STATUS">
      <div className="flex items-center gap-2 mb-4 font-mono text-sm font-semibold">
        <StatusDot tone={STATE_TONE[state]} pulse={state === 'AUTONOMOUS' || state === 'REROUTING'} />
        {state}
      </div>
      <div className="flex flex-col gap-2.5">
        {(Object.keys(MODULE_LABEL) as (keyof SystemModuleStatus)[]).map((key) => (
          <div key={key} className="flex justify-between items-center text-[12.5px]">
            <span>{MODULE_LABEL[key]}</span>
            <span className="flex items-center gap-1.5 font-mono text-[11px] text-text-dim">
              <StatusDot tone={STATUS_TONE[modules[key]]} />
              {modules[key]}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
