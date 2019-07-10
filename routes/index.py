import os
import uuid
from . import new_csrf_token, cache
from flask import (
    render_template,
    request,
    redirect,
    session,
    url_for,
    Blueprint,
    make_response,
    abort,
    send_from_directory
)
from config import admin_mail
from models.message import send_mail
from werkzeug.datastructures import FileStorage
from models.reply import Reply
from models.topic import Topic
from models.user import User
from routes import current_user
import json


main = Blueprint('index', __name__)

"""
用户在这里可以
    访问首页
    注册
    登录

用户登录后, 会写入 session, 并且定向到 /profile
"""

import gevent
import threading
import time



@main.route("/")
def index():
    # t = threading.Thread()
    # t.start()
    # gevent.spawn()
    time.sleep(0.5)
    print('time type', time.sleep, gevent.sleep)
    u = current_user()
    return render_template("index.html", user=u)


@main.route("/register", methods=['POST'])
def register():
    form = request.form.to_dict()
    # 用类函数来判断
    u = User.register(form)
    return redirect(url_for('.index'))


@main.route("/login", methods=['POST'])
def login():
    form = request.form
    u = User.validate_login(form)
    if u is None:
        return redirect(url_for('.index'))
    else:
        # session 中写入 user_id
        session['user_id'] = u.id
        # 设置 cookie 有效期为 永久
        session.permanent = True
        # 转到 topic.index 页面
        return redirect(url_for('topic.index'))


def created_topic(user_id):
    # O(n)
    ts = Topic.all(user_id=user_id)
    return ts


def replied_topic(user_id):

    k = 'replied_topic_{}'.format(user_id)
    if cache.exists(k):
        v = cache.get(k)
        ts = json.loads(v)
        return ts
    else:
        rs = Reply.all(user_id=user_id)
        ts = []
        for r in rs:
            t = Topic.one(id=r.topic_id)
            ts.append(t)

        v = json.dumps([t.json() for t in ts])
        cache.set(k, v)

        return ts


@main.route('/profile')
def profile():
    print('running profile route')
    u = current_user()
    if u is None:
        return redirect(url_for('.index'))
    else:
        created = created_topic(u.id)
        replied = replied_topic(u.id)
        return render_template(
            'profile.html',
            user=u,
            created=created,
            replied=replied
        )


@main.route('/user/<int:id>')
def user_detail(id):
    u = User.one(id=id)
    if u is None:
        abort(404)
    else:
        return render_template('profile.html', user=u)


@main.route('/image/add', methods=['POST'])
def avatar_add():
    file: FileStorage = request.files['avatar']

    filename = str(uuid.uuid4())
    path = os.path.join('images', filename)
    file.save(path)

    u = current_user()
    User.update(u.id, image='/images/{}'.format(filename))

    return redirect(url_for('.profile'))


@main.route('/images/<filename>')
def image(filename):

    return send_from_directory('images', filename)


@main.route('/user/<username>')
def user_info(username):
    u = User.one(username=username)
    return render_template('user_info.html', user=u)


@main.route('/settings')
def settings():
    u = current_user()
    if u:
        csrf = new_csrf_token()
        return render_template('settings.html', user=u, csrf_token=csrf)
    else:
        return redirect(url_for('index'))


@main.route('/change_sign', methods=['POST'])
def change_sign():
    form = request.form.to_dict()
    print('....', form)
    name = form['name']
    csrf = form['_csrf']
    sign = form['sign']
    user_id = cache.get(csrf)
    print('****userid', user_id)
    u = User.one(id=user_id)
    if u.username == name:
        u.sign = sign
        u.save()
        return redirect(url_for('index.settings'))
    else:
        abort(401)

@main.route('/email_changepass', methods=['POST'])
def email_changepass():
    u = current_user()
    reciever = u.email
    token = new_csrf_token()
    content = '请点击下面的链接重置您的密码\n{}{}'.format(
        'http://localhost:3000/chagepassword?token=',
        token
    )
    print('邮件内容:', content)
    send_mail(subject='重置您的密码',
              author=admin_mail,
              to=reciever,
              content=content)
    return redirect(url_for('index.settings'))


@main.route('/chagepassword', methods=['GET', 'POST'])
def changepassword():
    token = request.args.get('token')
    user_id = cache.get(token).decode()
    if user_id:
        return render_template('changepassword.html', user_id=user_id)
    else:
        abort(404)

@main.route('/submit_new_pass', methods=['POST'])
def submit_new_pass():
    new_pass = request.form.get('new_pass')
    user_id = request.form.get('user_id')
    u = User.one(id=user_id)
    u.password = User.salted_password(new_pass)
    u.save()
    message = '修改密码成功'
    return render_template('changepassword.html', user_id=user_id, message=message)


