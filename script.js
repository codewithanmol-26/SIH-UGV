// Connects to the telemetry backend and keeps the console panels in sync.
// Change BACKEND_HOST if the backend runs somewhere other than localhost:3001.
const BACKEND_HOST = location.hostname || 'localhost';
const socket = new WebSocket(`ws://${BACKEND_HOST}:3001`);

const el = (id) => document.getElementById(id);

socket.onopen = () => console.log('Connected to UGV telemetry stream');
socket.onerror = (err) => console.error('Telemetry connection error', err);
socket.onclose = () => console.warn('Telemetry stream closed — is the backend running?');

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);

  updateWaypoints(data.waypoints, data.waypointIndex);
  el('speed').textContent = `${data.speed} m/s`;
  el('heading').textContent = `${data.heading}°`;
  el('dist').textContent = `${data.distToWaypoint} m`;
  el('obstacle-count').textContent = `${data.obstacles.length} active`;
  el('battery').textContent = `${data.battery}%`;
  el('link').textContent = `LINK: ${data.linkMs}ms`;

  updateObstacles(data.obstacles);
  updateTrajectory(data.trajectory);
  updateLog(data.logs);
};

function updateWaypoints(waypoints, activeIndex) {
  const list = el('waypoint-list');
  list.innerHTML = '';
  waypoints.forEach((wp, i) => {
    const li = document.createElement('li');
    li.textContent = wp;
    li.className = i < activeIndex ? 'done' : i === activeIndex ? 'active' : 'pending';
    list.appendChild(li);
  });
}

function updateObstacles(obstacles) {
  const layer = el('obstacle-layer');
  layer.innerHTML = obstacles.map((o) => {
    const color = o.confidence > 0.75 ? '#C4453A' : '#E8A33D';
    return `
      <rect x="${o.x}" y="${o.y}" width="${o.w}" height="${o.h}" fill="none" stroke="${color}" stroke-width="1.5"/>
      <text x="${o.x + 2}" y="${o.y - 4}" fill="${color}" font-family="IBM Plex Mono" font-size="9">${o.type} ${o.confidence}</text>
    `;
  }).join('');
}

function updateTrajectory(points) {
  if (!points.length) return;
  const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  el('slam-path').setAttribute('d', d);
  const now = points[points.length - 1];
  el('slam-now').setAttribute('cx', now.x.toFixed(1));
  el('slam-now').setAttribute('cy', now.y.toFixed(1));
}

function updateLog(logs) {
  el('log').innerHTML = logs.map((l) => `
    <div class="log-entry ${l.kind}"><span class="t">${l.t}</span><span>${l.text}</span></div>
  `).join('');
}
