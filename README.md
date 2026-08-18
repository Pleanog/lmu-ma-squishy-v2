1. Open VS Code
2. Open 3 consoles besides each other

Next Step allways start Pocketbase first!

3. Pocketbase:

Navigate to "C:\Users\hive-2019\Desktop\lmu-ma-squishy-v2\backend\pocketbase_0.35.1_windows_amd64>"
using "cd .\backend\pocketbase_0.35.1_windows_amd64\"
Start the databse using "./pocketbase serve"

2. Main Server:

Navigate to "C:\Users\hive-2019\Desktop\lmu-ma-squishy-v2\backend\server>"
using "cd \backend\server"
then start the virtual enviroment using:
".\venv\Scripts\Activate"

Now start the main server:
"python run_server.py"


Stop Main Server with "Strg + C"
Restart main Server with "python run_server.py" (on need to activate venv again)


3. Frontend:
Navigate to "C:\Users\hive-2019\Desktop\lmu-ma-squishy-v2\frontend>"
using "cd frontend"
Now start the frontend unsing: "npm run dev"

The ip shown that starts with "10.XX..." is the one inside the private "HACUM" network.



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
