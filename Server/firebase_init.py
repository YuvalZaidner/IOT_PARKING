import os
import json
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Try env override first (recommended)
ENV_DB_URL = os.environ.get("RTDB_URL") or os.environ.get("FIREBASE_DATABASE_URL")

def _probe_url(url):
    try:
        import requests
        resp = requests.get(url.rstrip("/") + "/.json", timeout=3)
        # treat 404 as non-existing endpoint; 200/401/403/etc means endpoint exists
        return resp.status_code != 404
    except Exception:
        return False

def _derive_database_url(cred_path):
    if ENV_DB_URL:
        return ENV_DB_URL

    try:
        info = json.load(open(cred_path))
        pid = info.get("project_id")
    except Exception:
        return None

    if not pid:
        return None

    candidates = [
        f"https://{pid}-default-rtdb.firebaseio.com",
        f"https://{pid}-default-rtdb.europe-west1.firebasedatabase.app",
        f"https://{pid}-default-rtdb.us-central1.firebasedatabase.app",
        f"https://{pid}-default-rtdb.europe-west3.firebasedatabase.app",
    ]

    for u in candidates:
        if _probe_url(u):
            return u

    # fallback to first candidate
    return candidates[0]

# credential path (use GOOGLE_APPLICATION_CREDENTIALS if set, else 'secret.json' next to this file)
# If the process CWD is the repo root (common when running scripts), a plain
# "secret.json" won't be found. Point the default to the Server/secret.json
# location (next to this module) so both `cd Server && python ...` and
# `python Server/simulation_sondos.py` work.
default_secret = os.path.join(os.path.dirname(__file__), "secret.json")
cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", default_secret)

# Prefer certificate file when available. If missing, fall back to Application Default
# Credentials so importing this module doesn't crash immediately. This makes local
# development easier but we emit a clear message explaining how to provide creds.
if os.path.exists(cred_path):
    try:
        cred = credentials.Certificate(cred_path)
    except Exception as e:
        # Unexpected parsing error from certificate file
        raise RuntimeError(f"Failed to load Firebase certificate from {cred_path}: {e}") from e
else:
    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        # User explicitly set the env var but file does not exist -> fail fast with clear message
        raise FileNotFoundError(
            f"GOOGLE_APPLICATION_CREDENTIALS is set to '{cred_path}' but the file was not found.\n"
            "Please set GOOGLE_APPLICATION_CREDENTIALS to a valid service account JSON path or place 'secret.json' in the Server folder."
        )
    # No certificate file found; fall back to Application Default Credentials (ADC).
    # ADC will work if the environment has been configured (e.g. gcloud auth application-default login)
    # or when running on a Google Cloud environment. We keep `cred` as None so
    # `firebase_admin.initialize_app` uses the default credential flow.
    print("[Firebase] Warning: credential file not found; falling back to Application Default Credentials.\n"
          "If you expect to use a service account file locally, set GOOGLE_APPLICATION_CREDENTIALS or add 'secret.json'.")
    cred = None

database_url = _derive_database_url(cred_path)
if not database_url:
    database_url = os.environ.get("RTDB_URL")  # final fallback

# If we still don't have a database URL, that's unrecoverable for parts of the
# application that expect a Realtime Database (e.g. simulation scripts). Fail
# fast with a helpful message so the user knows how to fix their environment.
if not database_url:
    raise RuntimeError(
        """Firebase Realtime Database URL could not be determined.
Provide one of the following to continue:
 1) Set the RTDB_URL or FIREBASE_DATABASE_URL environment variable to your RTDB URL.
    Example: export RTDB_URL='https://<project>-default-rtdb.europe-west1.firebasedatabase.app'
 2) Place a service account JSON named 'secret.json' in the Server folder or set
    GOOGLE_APPLICATION_CREDENTIALS to its absolute path so the code can derive the project_id.

Note: If you intend to run without a Realtime Database (read-only or offline), adjust imports that
call db.reference or mock the database in tests.
"""
    )

# Initialize Firebase app idempotently. If `cred` is None, firebase_admin will use
# Application Default Credentials or other configured defaults.
try:
    firebase_admin.get_app()
except ValueError:
    init_opts = {"databaseURL": database_url} if database_url else None
    if init_opts:
        firebase_admin.initialize_app(cred, init_opts)
    else:
        # initialize without options if we don't have a databaseURL
        firebase_admin.initialize_app(cred)

print(f"[Firebase] Using DB: {database_url}")
# export db (other modules import `from firebase_init import db as _db_init`)
# Note: `db` is already imported from firebase_admin above