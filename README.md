## 🚀 Local Development Setup

To run the project locally, open **VS Code** and open **3 separate terminal panels** side-by-side. 

> **⚠️ IMPORTANT:** Services must be started in the correct order. **Always start Pocketbase first!**

### 1. Database (Pocketbase)
*Must be started first.*
1. In the first terminal, navigate to the Pocketbase directory:
   ```bash
   cd backend/pocketbase_0.35.1_windows_amd64
   ```
2. Start the database server:
   ```bash
   ./pocketbase serve
   ```

### 2. Main Server (Python)
1. In the second terminal, navigate to the server directory:
   ```bash
   cd backend/server
   ```
2. Activate the virtual environment:
   ```bash
   .\venv\Scripts\Activate
   ```
3. Start the main server:
   ```bash
   python run_server.py
   ```
* **To stop the server:** Press `Ctrl + C`
* **To restart the server:** Simply run `python run_server.py` again (you do not need to reactivate the virtual environment as long as the terminal remains open).

### 3. Frontend (Node/npm)
1. In the third terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Start the development server:
   ```bash
   npm run dev
   ```
> **📝 Network Note:** The IP address shown in the console that starts with `10.XX...` is the local address used inside the private **HACUM** network.

---

## Restarting & Troubleshooting

* **Restarting the Frontend:** Press `Ctrl + C` to stop the current process, then run `npm run dev` again.
* **Backend/Frontend Syncing (Crucial):** If you ever need to restart the **Main Server**, it is highly recommended that you restart the Frontend immediately after. 






---------------------------------




# Old Version of the ReadMe: pre gemini Live APi and Websockets!

First we need to start pocketbase inside the backend/pocketbase folder with the command:
./pocketbase serve

Then we start the python server that handles the communication with the llm. it is inside the backend/server folder. We activate the venv first with:
 .\venv\Scripts\Activate  

 and then run the brain aka server with:
 python brain.py
 oder mittlerweile
 python main.py

 next we start the frontend inside the frontend folder with 
 npm run dev

## LAN microphone access (important)

When a participant opens the frontend from another device in the local network, browser microphone access only works in a secure context.

- `http://localhost` works locally on the same machine.
- For remote LAN access, use `https://<laptop-ip>:5173` for the frontend.

The frontend dev server now supports HTTPS certificates via env vars:

- `VITE_DEV_HTTPS_CERT` (path to cert file)
- `VITE_DEV_HTTPS_KEY` (path to key file)

Example (PowerShell, in `frontend`):

```powershell
$env:VITE_DEV_HTTPS_CERT="certs/dev-cert.pem"
$env:VITE_DEV_HTTPS_KEY="certs/dev-key.pem"
npm run dev -- --host
```

If cert/key are not set, the frontend runs as HTTP as before.

Backend WebSocket/API must use TLS too when frontend runs with HTTPS (so the browser can use `wss://` and `https://`):

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-certfile certs/dev-cert.pem --ssl-keyfile certs/dev-key.pem
```
