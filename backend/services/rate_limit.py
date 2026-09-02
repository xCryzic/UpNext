from collections import defaultdict, deque
from functools import wraps
from threading import Lock
from time import monotonic

from flask import current_app, jsonify, request


_attempts = defaultdict(deque)
_lock = Lock()


def reset_rate_limits():
    with _lock:
        _attempts.clear()


def rate_limit(config_key, default_limit):
    """Small process-local fixed-window limiter for public V1 endpoints."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_app.config.get("RATE_LIMIT_ENABLED", True):
                return view(*args, **kwargs)
            limit = int(current_app.config.get(config_key, default_limit))
            now = monotonic()
            key = (request.remote_addr or "unknown", request.endpoint or view.__name__)
            with _lock:
                entries = _attempts[key]
                while entries and now - entries[0] >= 60:
                    entries.popleft()
                if len(entries) >= limit:
                    return jsonify({"error": "Too many requests. Please try again shortly."}), 429
                entries.append(now)
            return view(*args, **kwargs)
        return wrapped
    return decorator
