"""حسابات بسيطة وجلسات محلية ولوحة إحصاءات لا تجمع عنوان IP أو بصمة متصفح."""
import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from starlette.background import BackgroundTask

router = APIRouter(tags=["auth"])

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = Path(os.getenv("APP_DATA_DIR", str(_DEFAULT_DATA_DIR))).expanduser()
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DATA_DIR / "alphabuf_accounts.sqlite3"
_SESSION_COOKIE = "alphabuf_session"
_VISITOR_COOKIE = "alphabuf_visitor"
_SESSION_DAYS = 30


def _connection():
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _initialize():
    with _connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token TEXT PRIMARY KEY, user_id INTEGER, is_guest INTEGER NOT NULL,
          created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS visits (
          visitor_token TEXT NOT NULL, visit_day TEXT NOT NULL, first_seen TEXT NOT NULL,
          PRIMARY KEY(visitor_token, visit_day)
        );
        CREATE TABLE IF NOT EXISTS user_favorites (
          user_id INTEGER NOT NULL, ticker TEXT NOT NULL, name TEXT NOT NULL,
          sector TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(user_id, ticker), FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)


_initialize()


def _now():
    return datetime.now(timezone.utc)


def _hash_password(password, salt=None):
    salt = secrets.token_bytes(16) if salt is None else salt
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return "pbkdf2_sha256$310000$%s$%s" % (
        base64.b64encode(salt).decode("ascii"), base64.b64encode(digest).decode("ascii")
    )


def _verify_password(password, stored):
    try:
        _, rounds, salt_b64, digest_b64 = stored.split("$", 3)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt_b64), int(rounds))
        return hmac.compare_digest(candidate, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


def _admin_email():
    return os.getenv("ADMIN_EMAIL", "").strip().lower()


def _is_admin(email):
    return bool(_admin_email()) and email.lower() == _admin_email()


def _public_user(row, is_guest=False):
    if is_guest:
        return {"kind": "guest", "email": None, "is_admin": False}
    return {"kind": "account", "email": row["email"], "is_admin": _is_admin(row["email"])}


def _set_session(response, user_id=None, is_guest=False):
    token = secrets.token_urlsafe(32)
    now = _now()
    expiry = now + timedelta(days=_SESSION_DAYS)
    with _connection() as conn:
        conn.execute("INSERT INTO sessions(token, user_id, is_guest, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                     (token, user_id, int(is_guest), now.isoformat(), expiry.isoformat()))
    response.set_cookie(_SESSION_COOKIE, token, max_age=_SESSION_DAYS * 86400, httponly=True,
                        samesite="lax", secure=os.getenv("COOKIE_SECURE", "").lower() == "true")


def _session_user(request):
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        return None
    with _connection() as conn:
        row = conn.execute("""
            SELECT sessions.token, sessions.is_guest, users.id AS user_id, users.email
            FROM sessions LEFT JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
        """, (token, _now().isoformat())).fetchone()
    return row


def _require_admin(request):
    session = _session_user(request)
    if not session or session["is_guest"] or not session["email"] or not _is_admin(session["email"]):
        raise HTTPException(status_code=403, detail="هذه الصفحة متاحة لحساب المدير فقط")
    return session


def _require_account(request):
    session = _session_user(request)
    if not session or session["is_guest"] or not session["user_id"]:
        raise HTTPException(status_code=401, detail="سجّل الدخول أولاً لحفظ المفضلات في حسابك")
    return session


def _delete_file(path):
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        value = value.strip().lower()
        if value.count("@") != 1 or value.startswith("@") or value.endswith("@"):
            raise ValueError("البريد الإلكتروني غير صالح")
        return value


class FavoritePayload(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=160)
    sector: str = Field(min_length=1, max_length=100)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value):
        value = value.strip().upper()
        if not all(char.isalnum() or char in ".-" for char in value):
            raise ValueError("رمز السهم غير صالح")
        return value


@router.get("/api/auth/me")
def me(request: Request):
    session = _session_user(request)
    if not session:
        return {"user": None}
    if session["is_guest"]:
        return {"user": _public_user(None, is_guest=True)}
    return {"user": {"kind": "account", "email": session["email"], "is_admin": _is_admin(session["email"])}}


@router.post("/api/auth/register")
def register(payload: Credentials, response: Response):
    email = payload.email.lower()
    if _is_admin(email):
        raise HTTPException(status_code=403, detail="هذا البريد محجوز لحساب المدير")
    with _connection() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="يوجد حساب بهذا البريد بالفعل")
        cursor = conn.execute("INSERT INTO users(email, password_hash, created_at) VALUES (?, ?, ?)",
                              (email, _hash_password(payload.password), _now().isoformat()))
    _set_session(response, user_id=cursor.lastrowid)
    return {"user": {"kind": "account", "email": email, "is_admin": False}}


@router.post("/api/auth/login")
def login(payload: Credentials, response: Response):
    email = payload.email.lower()
    configured_password = os.getenv("ADMIN_PASSWORD", "")
    if _is_admin(email):
        if not configured_password or not hmac.compare_digest(payload.password, configured_password):
            raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة أو حساب المدير غير مهيأ")
        with _connection() as conn:
            row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (_hash_password(payload.password), row["id"]))
                user_id = row["id"]
            else:
                user_id = conn.execute("INSERT INTO users(email, password_hash, created_at) VALUES (?, ?, ?)",
                                       (email, _hash_password(payload.password), _now().isoformat())).lastrowid
        _set_session(response, user_id=user_id)
        return {"user": {"kind": "account", "email": email, "is_admin": True}}

    with _connection() as conn:
        row = conn.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not _verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="البريد أو كلمة المرور غير صحيحة")
    _set_session(response, user_id=row["id"])
    return {"user": _public_user(row)}


@router.post("/api/auth/guest")
def guest(response: Response):
    _set_session(response, is_guest=True)
    return {"user": _public_user(None, is_guest=True)}


@router.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        with _connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    response.delete_cookie(_SESSION_COOKIE)
    return {"ok": True}


@router.post("/api/telemetry/visit")
def record_visit(request: Request, response: Response):
    visitor = request.cookies.get(_VISITOR_COOKIE) or secrets.token_urlsafe(24)
    now = _now()
    with _connection() as conn:
        conn.execute("INSERT OR IGNORE INTO visits(visitor_token, visit_day, first_seen) VALUES (?, ?, ?)",
                     (visitor, now.date().isoformat(), now.isoformat()))
    response.set_cookie(_VISITOR_COOKIE, visitor, max_age=365 * 86400, httponly=True, samesite="lax",
                        secure=os.getenv("COOKIE_SECURE", "").lower() == "true")
    return {"ok": True}


@router.get("/api/favorites")
def list_favorites(request: Request):
    session = _require_account(request)
    with _connection() as conn:
        items = conn.execute("SELECT ticker, name, sector, created_at FROM user_favorites WHERE user_id = ? ORDER BY created_at DESC",
                             (session["user_id"],)).fetchall()
    return {"items": [dict(item) for item in items]}


@router.post("/api/favorites")
def add_favorite(payload: FavoritePayload, request: Request):
    session = _require_account(request)
    with _connection() as conn:
        conn.execute("INSERT OR REPLACE INTO user_favorites(user_id, ticker, name, sector, created_at) VALUES (?, ?, ?, ?, ?)",
                     (session["user_id"], payload.ticker, payload.name.strip(), payload.sector.strip(), _now().isoformat()))
    return {"item": {"ticker": payload.ticker, "name": payload.name.strip(), "sector": payload.sector.strip()}}


@router.delete("/api/favorites/{ticker}")
def remove_favorite(ticker: str, request: Request):
    session = _require_account(request)
    ticker = ticker.strip().upper()
    with _connection() as conn:
        conn.execute("DELETE FROM user_favorites WHERE user_id = ? AND ticker = ?", (session["user_id"], ticker))
    return {"ok": True}


@router.get("/api/admin/metrics")
def admin_metrics(request: Request):
    _require_admin(request)
    today = _now().date()
    start = (today - timedelta(days=6)).isoformat()
    with _connection() as conn:
        daily = conn.execute("SELECT visit_day, COUNT(*) AS visits FROM visits WHERE visit_day >= ? GROUP BY visit_day ORDER BY visit_day", (start,)).fetchall()
        total_visits = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
        visitors = conn.execute("SELECT COUNT(DISTINCT visitor_token) FROM visits").fetchone()[0]
        accounts = conn.execute("SELECT COUNT(*) FROM users WHERE email != ?", (_admin_email(),)).fetchone()[0]
    return {"today": today.isoformat(), "daily": [dict(row) for row in daily], "total_visits": total_visits,
            "unique_visitors": visitors, "accounts": accounts}


@router.get("/api/admin/backup")
def download_backup(request: Request):
    """نسخة SQLite متسقة يمكن للمدير تنزيلها قبل أي نشر."""
    _require_admin(request)
    with tempfile.NamedTemporaryFile(prefix="alphabuf-backup-", suffix=".sqlite3", delete=False) as temp:
        backup_path = Path(temp.name)
    try:
        with _connection() as source, sqlite3.connect(backup_path) as destination:
            source.backup(destination)
    except Exception:
        _delete_file(backup_path)
        raise
    filename = f"alphabuf-backup-{_now().strftime('%Y-%m-%d-%H%M')}.sqlite3"
    return FileResponse(backup_path, media_type="application/vnd.sqlite3", filename=filename,
                        background=BackgroundTask(_delete_file, backup_path))
