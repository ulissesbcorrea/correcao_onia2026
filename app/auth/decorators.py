from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.extensions import db
from app.models.evaluator import Evaluator


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = db.session.get(Evaluator, int(get_jwt_identity()))
        if not user or user.role != "admin":
            return {"error": "Admin access required"}, 403
        return fn(*args, **kwargs)

    return wrapper


def evaluator_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = db.session.get(Evaluator, int(get_jwt_identity()))
        if not user or user.role not in ("admin", "evaluator"):
            return {"error": "Authentication required"}, 403
        return fn(*args, **kwargs)

    return wrapper
