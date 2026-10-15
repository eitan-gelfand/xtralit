"""JWT handling for monday integration requests (verify incoming, sign outgoing)."""
import os
import time

import jwt
from flask import abort, request

SIGNING_SECRET = os.environ.get("MONDAY_SIGNING_SECRET")
APP_ID = os.environ.get("MONDAY_APP_ID")


def verify_request() -> dict:
    """Decode the Authorization JWT monday sends with subscribe/unsubscribe/action calls.

    Returns its claims (accountId, userId, shortLivedToken, ...); aborts 401 if invalid.
    """
    token = request.headers.get("Authorization", "")
    try:
        return jwt.decode(token, SIGNING_SECRET, algorithms=["HS256"], options={"verify_aud": False})
    except jwt.PyJWTError as e:
        print(f"Rejected request to {request.path}: {e}", flush=True)
        abort(401)


def trigger_auth_header() -> str:
    """JWT for calling a trigger's webhookUrl: app id signed with the signing secret, 1-min expiry."""
    return jwt.encode({"appId": int(APP_ID), "exp": int(time.time()) + 60}, SIGNING_SECRET, algorithm="HS256")
