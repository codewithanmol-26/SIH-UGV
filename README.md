# UGV Mission Console

## Structure
```
ugv-console/
├── frontend/       static dashboard (HTML/CSS/JS)
│   ├── index.html
│   ├── style.css
│   └── script.js
└── backend/        telemetry server (Node.js + WebSocket)
    ├── server.js
    └── package.json
```

## How it fits together
The backend simulates UGV telemetry (speed, heading, obstacles, SLAM
trajectory, event log) and broadcasts it over WebSocket about once a second.
It also serves `frontend/` as static files, so one command runs the whole
thing. `frontend/script.js` opens the WebSocket connection and updates the
dashboard whenever a new telemetry message arrives — it never talks to a
database directly.

## Run it
```bash
cd backend
npm install
npm start
```
Then open `http://localhost:3001` in a browser.

## Wiring in real data
Replace the simulation inside `tick()` in `backend/server.js` with real
readings from your perception model, visual SLAM pipeline, and path planner
(e.g. read them off a ROS topic, serial port, or MQTT broker), and call
`broadcast()` whenever new values come in. The frontend doesn't need to
change — it just renders whatever JSON arrives on the socket.

## Adding the database
When you're ready to log telemetry (e.g. to Firebase or Supabase as discussed),
write to it inside `tick()` right after `broadcast()` — that's the one place
new state is produced each cycle. Keep the database out of the frontend
entirely; it should only ever talk to the backend over WebSocket.
