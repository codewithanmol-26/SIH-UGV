# Phone = UGV camera, Laptop = dashboard

1. Copy everything in this patch/ folder over your repo (same paths, overwrite).
2. Phone: install "IP Webcam" (Android) -> Start server. Phone and laptop on the same Wi-Fi/hotspot.
   The app shows the address on screen, e.g. http://192.168.1.23:8080
3. Laptop: `cd backend && python main.py`, then `cd frontend && npm run dev`, open http://localhost:5173
   (If no camera is found at startup, the dashboard still loads.)
4. In the CAMERA panel, paste  http://<phone-ip>:8080/video  and press CONNECT.
5. Click the map to set a destination, press START.

Optional: set UGV_CAMERA_SOURCE=ip_stream and UGV_CAMERA_IP_URL=... in backend/.env to skip step 4.
