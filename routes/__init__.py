import uuid
import redis
from functools import wraps

from flask import session, request, abort

from models.user import User


def current_user():
    uid = session.get('user_id', '')
    u = User.one(id=uid)
    return u


cache = redis.StrictRedis()



def csrf_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.args['token']
        u = current_user()
        token_id = cache.get(token)
        # if token in csrf_tokens and csrf_tokens[token] == u.id:
        if token_id == u.id:
            return f(*args, **kwargs)
        else:
            abort(401)

    return wrapper


def new_csrf_token():
    u = current_user()
    if u:
        token = str(uuid.uuid4())
        cache.set(token, u.id)
        return token
