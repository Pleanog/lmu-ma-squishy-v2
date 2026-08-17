import os

from dotenv import load_dotenv
import uvicorn


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    load_dotenv()

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", "8000"))
    reload_enabled = _env_bool("UVICORN_RELOAD", True)
    ws_ping_interval = float(os.getenv("UVICORN_WS_PING_INTERVAL", "60"))
    ws_ping_timeout = float(os.getenv("UVICORN_WS_PING_TIMEOUT", "60"))

    ssl_certfile = os.getenv("UVICORN_SSL_CERTFILE", "").strip() or None
    ssl_keyfile = os.getenv("UVICORN_SSL_KEYFILE", "").strip() or None

    run_kwargs = {
        "host": host,
        "port": port,
        "reload": reload_enabled,
        "ws_ping_interval": ws_ping_interval,
        "ws_ping_timeout": ws_ping_timeout,
    }

    if ssl_certfile and ssl_keyfile:
        run_kwargs["ssl_certfile"] = ssl_certfile
        run_kwargs["ssl_keyfile"] = ssl_keyfile

    uvicorn.run("main:app", **run_kwargs)


if __name__ == "__main__":
    main()
