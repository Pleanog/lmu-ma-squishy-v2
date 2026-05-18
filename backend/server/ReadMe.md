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

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

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
