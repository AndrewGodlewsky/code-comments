# existing/login.py -- current password sign-in (Flask). No second factor today.
from flask import request, redirect, make_response
from app.db import db
from app.security import bcrypt_check, new_token, rate_limit
from app.views import render

SESSION_COOKIE = "sid"
SESSION_DAYS = 30


@app.post("/login")
@rate_limit(key="ip", per_minute=10)
def login():
    email = request.form["email"].strip().lower()
    user = db.one("SELECT id, password_hash FROM users WHERE email = %s", email)
    if user is None or not bcrypt_check(request.form["password"], user.password_hash):
        return render("login.html", error="Wrong email or password"), 401
    # The password is the only check today, so the session is created immediately.
    return start_session(user.id)


def start_session(user_id):
    token = new_token(32)  # random, URL-safe
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) "
        "VALUES (sha256(%s), %s, now() + interval '30 days')",
        token, user_id)
    resp = make_response(redirect("/home"))
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, secure=True,
                    samesite="Lax", max_age=SESSION_DAYS * 86400)
    return resp


@app.post("/logout")
def logout():
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash = sha256(%s)", token)
    resp = make_response(redirect("/login"))
    resp.delete_cookie(SESSION_COOKIE)
    return resp
