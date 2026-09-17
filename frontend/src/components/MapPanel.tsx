import { useCallback, useMemo, useRef } from 'react';
import type { WorldPoint } from '../types';
import { Panel } from './Primitives';

interface MapPanelProps {
  currentPosition: { x: number; y: number; heading_deg: number };
  trajectory: WorldPoint[];
  route: WorldPoint[];
  destination: WorldPoint | null;
  pendingDestination: WorldPoint | null;
  onPickDestination: (point: WorldPoint) => void;
  viewSpanMeters?: number; // total width/height of the map in meters
}

// Local coordinate system, no GPS: origin (0,0) is where the UGV started.
// The canvas is a fixed square viewport centered on the origin — panning/
// zoom are a reasonable future addition, not needed for the MVP demo.
export function MapPanel({
  currentPosition,
  trajectory,
  route,
  destination,
  pendingDestination,
  onPickDestination,
  viewSpanMeters = 20,
}: MapPanelProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const size = 320; // svg viewBox units

  const toScreen = useCallback(
    (x: number, y: number): [number, number] => {
      const scale = size / viewSpanMeters;
      return [size / 2 + x * scale, size / 2 - y * scale];
    },
    [viewSpanMeters],
  );

  const toWorld = useCallback(
    (screenX: number, screenY: number): WorldPoint => {
      const scale = size / viewSpanMeters;
      return [(screenX - size / 2) / scale, (size / 2 - screenY) / scale];
    },
    [viewSpanMeters],
  );

  const handleClick = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const sx = ((e.clientX - rect.left) / rect.width) * size;
    const sy = ((e.clientY - rect.top) / rect.height) * size;
    onPickDestination(toWorld(sx, sy));
  };

  const trajectoryPath = useMemo(() => {
    if (trajectory.length === 0) return '';
    return trajectory
      .map(([x, y], i) => {
        const [sx, sy] = toScreen(x, y);
        return `${i === 0 ? 'M' : 'L'}${sx.toFixed(1)},${sy.toFixed(1)}`;
      })
      .join(' ');
  }, [trajectory, toScreen]);

  const routePath = useMemo(() => {
    if (route.length === 0) return '';
    return route
      .map(([x, y], i) => {
        const [sx, sy] = toScreen(x, y);
        return `${i === 0 ? 'M' : 'L'}${sx.toFixed(1)},${sy.toFixed(1)}`;
      })
      .join(' ');
  }, [route, toScreen]);

  const [curSx, curSy] = toScreen(currentPosition.x, currentPosition.y);
  const [originSx, originSy] = toScreen(0, 0);
  const destPoint = destination ?? pendingDestination;
  const destScreen = destPoint ? toScreen(destPoint[0], destPoint[1]) : null;

  // Grid lines every 2 meters.
  const gridLines = [];
  const scale = size / viewSpanMeters;
  for (let m = -viewSpanMeters / 2; m <= viewSpanMeters / 2; m += 2) {
    const [sx] = toScreen(m, 0);
    const [, sy] = toScreen(0, m);
    gridLines.push(<line key={`v${m}`} x1={sx} y1={0} x2={sx} y2={size} stroke="var(--color-panel-line)" strokeWidth={0.5} />);
    gridLines.push(<line key={`h${m}`} x1={0} y1={sy} x2={size} y2={sy} stroke="var(--color-panel-line)" strokeWidth={0.5} />);
  }
  void scale;

  return (
    <Panel title="LIVE NAVIGATION MAP" className="flex flex-col gap-2">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${size} ${size}`}
        className="w-full aspect-square rounded-[2px] border border-panel-line cursor-crosshair bg-[#0F110C]"
        onClick={handleClick}
      >
        {gridLines}

        {routePath && (
          <path d={routePath} fill="none" stroke="var(--color-amber)" strokeWidth={1.5} strokeDasharray="4 3" />
        )}
        {trajectoryPath && (
          <path d={trajectoryPath} fill="none" stroke="var(--color-sage)" strokeWidth={1.5} opacity={0.8} />
        )}

        {/* Point A — start / origin */}
        <circle cx={originSx} cy={originSy} r={4} fill="var(--color-text-dim)" />
        <text x={originSx + 6} y={originSy - 6} fontFamily="IBM Plex Mono" fontSize={9} fill="var(--color-text-dim)">A</text>

        {/* Destination — Point B */}
        {destScreen && (
          <g>
            <circle cx={destScreen[0]} cy={destScreen[1]} r={5} fill="none" stroke="var(--color-amber)" strokeWidth={2} />
            <text x={destScreen[0] + 8} y={destScreen[1] - 6} fontFamily="IBM Plex Mono" fontSize={9} fill="var(--color-amber)">B</text>
          </g>
        )}

        {/* Current UGV position + heading */}
        <g transform={`translate(${curSx} ${curSy}) rotate(${-currentPosition.heading_deg})`}>
          <polygon points="0,-8 6,6 -6,6" fill="var(--color-sage)" />
        </g>
      </svg>
      <p className="text-[11px] font-mono text-text-dim leading-relaxed">
        Click the map to set Point B. Sage line = travelled path, amber dashed = planned route.
        Obstacle markers on this map are NOT IMPLEMENTED yet — see the camera panel for live obstacle detections.
      </p>
    </Panel>
  );
}
