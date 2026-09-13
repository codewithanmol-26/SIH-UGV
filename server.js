// Simulated telemetry backend for the UGV mission console.
// Serves the frontend as static files and streams live telemetry over WebSocket.
// Swap the simulation in tick() for real readings from your perception/SLAM
// pipeline (ROS bridge, serial link, MQTT, etc.) when you're ready.

const express = require('express');
const http = require('http');
const path = require('path');
const WebSocket = require('ws');

const app = express();
app.use(express.static(path.join(__dirname, '../frontend')));

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const waypoints = [
  'WP-01 · Launch point',
  'WP-02 · Creek crossing',
  'WP-03 · Rock field',
  'WP-04 · Treeline gap',
  'WP-05 · Drop point',
];

const state = {
  waypointIndex: 2,
  distToWaypoint: 18.6,
  speed: 1.4,
  heading: 247,
  battery: 76,
  linkMs: 340,
  obstacles: [
    { type: 'ROCK', confidence: 0.82, x: 40, y: 150, w: 55, h: 60 },
    { type: 'TREE', confidence: 0.91, x: 300, y: 130, w: 48, h: 80 },
  ],
  trajectory: [{ x: 30, y: 150 }],
  logs: [],
};

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function pushLog(text, kind = '') {
  const t = new Date().toTimeString().slice(0, 8);
  state.logs.unshift({ t, text, kind });
  state.logs = state.logs.slice(0, 6);
}

pushLog('Obstacle flagged — rock cluster, rerouting', 'flag');
pushLog('New path computed, clearance 0.6m', 'good');
pushLog('SLAM keyframe inserted (#118)');
pushLog('WP-02 reached — creek crossing clear', 'good');

function tick() {
  state.speed = clamp(state.speed + (Math.random() - 0.5) * 0.2, 0.6, 2.4);
  state.heading = (state.heading + (Math.random() - 0.5) * 12 + 360) % 360;
  state.distToWaypoint -= state.speed * 0.9;
  state.battery = clamp(state.battery - 0.02, 0, 100);
  state.linkMs = Math.round(clamp(state.linkMs + (Math.random() - 0.5) * 40, 120, 600));

  if (Math.random() < 0.08 && state.obstacles.length < 3) {
    const types = ['ROCK', 'TREE', 'DITCH'];
    const type = types[Math.floor(Math.random() * types.length)];
    state.obstacles.push({
      type,
      confidence: +(0.5 + Math.random() * 0.45).toFixed(2),
      x: 20 + Math.random() * 330,
      y: 90 + Math.random() * 90,
      w: 30 + Math.random() * 30,
      h: 30 + Math.random() * 50,
    });
    pushLog(`Obstacle flagged — ${type.toLowerCase()}, rerouting`, 'flag');
  }
  if (Math.random() < 0.06 && state.obstacles.length > 0) {
    state.obstacles.shift();
    pushLog('Path clear, resuming planned route', 'good');
  }

  if (state.distToWaypoint <= 0) {
    if (state.waypointIndex < waypoints.length - 1) {
      pushLog(`${waypoints[state.waypointIndex]} reached`, 'good');
      state.waypointIndex += 1;
      state.distToWaypoint = 15 + Math.random() * 20;
    } else {
      state.distToWaypoint = 0;
    }
  }

  const last = state.trajectory[state.trajectory.length - 1];
  const rad = (state.heading * Math.PI) / 180;
  const nx = clamp(last.x + Math.sin(rad) * 4, 10, 230);
  const ny = clamp(last.y - Math.cos(rad) * 4, 10, 170);
  state.trajectory.push({ x: nx, y: ny });
  if (state.trajectory.length > 40) state.trajectory.shift();

  broadcast();
}

function broadcast() {
  const payload = JSON.stringify({
    waypointIndex: state.waypointIndex,
    waypoints,
    distToWaypoint: state.distToWaypoint.toFixed(1),
    speed: state.speed.toFixed(1),
    heading: Math.round(state.heading),
    battery: Math.round(state.battery),
    linkMs: state.linkMs,
    obstacles: state.obstacles,
    trajectory: state.trajectory,
    logs: state.logs,
  });
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) client.send(payload);
  });
}

wss.on('connection', (ws) => {
  console.log('Frontend connected');
  broadcast();
});

setInterval(tick, 1200);

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`UGV console backend running on http://localhost:${PORT}`);
});
