// Strong types for everything crossing the frontend/backend boundary.
// Keep these in sync with backend/api/schemas.py and the WebSocket payload
// built in backend/api/websocket.py — they are hand-mirrored, not generated,
// so a backend field rename must be mirrored here manually.

export type ModuleStatus = 'ACTIVE' | 'SIMULATED' | 'NOT_IMPLEMENTED';

export type NavigationState =
  | 'IDLE'
  | 'INITIALIZING'
  | 'READY'
  | 'AUTONOMOUS'
  | 'PAUSED'
  | 'REROUTING'
  | 'SAFE_STOP'
  | 'STOPPED'
  | 'EMERGENCY_STOP'
  | 'DESTINATION_REACHED'
  | 'CONNECTION_LOST'
  | 'ERROR';

export interface UGVPosition {
  x: number;
  y: number;
  heading_deg: number;
  localization_confidence: number;
}

export interface Telemetry {
  x: number;
  y: number;
  heading_deg: number;
  velocity: number;
  distance_travelled_m: number;
  distance_remaining_m: number | null;
  obstacle_count: number;
  camera_fps: number;
  inference_fps: number;
  ai_latency_ms: number;
  localization_confidence: number;
}

export interface Obstacle {
  cls_name: string;
  confidence: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface SystemModuleStatus {
  camera: ModuleStatus;
  perception: ModuleStatus;
  traversability: ModuleStatus;
  localization: ModuleStatus;
  planner: ModuleStatus;
  controller: ModuleStatus;
  communication: ModuleStatus;
}

export interface LogEntry {
  t: string;
  text: string;
  kind: '' | 'good' | 'flag';
}

export type WorldPoint = [number, number];

// Full payload streamed over /ws/telemetry roughly every 150ms.
export interface TelemetryMessage {
  type: 'telemetry';
  state: NavigationState;
  position: UGVPosition;
  telemetry: Telemetry;
  destination: WorldPoint | null;
  route: WorldPoint[];
  trajectory: WorldPoint[];
  obstacles: Obstacle[];
  system_status: SystemModuleStatus;
  logs: LogEntry[];
  camera_frame: string | null; // data:image/jpeg;base64,...
}

// --- REST response shapes -----------------------------------------------

export interface ActionResponse {
  ok: boolean;
  state: NavigationState;
  message?: string;
}

export interface NavigationStatusResponse {
  state: NavigationState;
  destination: WorldPoint | null;
  plan_found: boolean;
  waypoints: WorldPoint[];
}
