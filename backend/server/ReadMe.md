# FastAPI Server Setup

## Requirements

* Python 3.10+
* pip

---

# Setup

Navigate into the server directory:

```bash
cd backend/server
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate the virtual environment.

## macOS / Linux

```bash
source venv/bin/activate
```

## Windows PowerShell

```powershell
venv\Scripts\Activate.ps1
```

## Windows CMD

```cmd
venv\Scripts\activate.bat
```

---

# Install Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

Optional:

```bash
pip install --upgrade pip
```

---

# Run the Server

Start the FastAPI development server:

```bash
uvicorn main:app --reload
```

Oder mit spezifischem Port:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --ws-ping-interval 60 --ws-ping-timeout 60
```

Einfacher (empfohlen): Start mit Konfigurationsdatei.

1. `.env.example` nach `.env` kopieren und bei Bedarf anpassen.
2. Dann nur noch:

```bash
python run_server.py
```

Optional mit TLS (für Mic-Zugriff von anderen Geräten im LAN):

- In `.env` setzen:
  - `UVICORN_SSL_CERTFILE=certs/dev-cert.pem`
  - `UVICORN_SSL_KEYFILE=certs/dev-key.pem`

The server will start on:

```text
http://127.0.0.1:8000
```

Interactive API docs:

```text
http://127.0.0.1:8000/docs
```

Alternative ReDoc docs:

```text
http://127.0.0.1:8000/redoc
```

---

# Deactivate the Virtual Environment

When finished:

```bash
deactivate
```
