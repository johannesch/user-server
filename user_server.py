#!/usr/bin/env python
"""
A minimal REST API to access a simple User resource. The user resource
contains following fields:

id - is a read only property, an id is automatically assigned when a
  User is created
name - the full name of the user (may not be empty or null)
email - (must be a valid email)
password - this is a write only field, meaning, when set, the password
  is hashed and set on the field, but the field is never
  returned when User resource is read (must be at least 8 characters long)
"""

from __future__ import with_statement
from flask import Flask, abort, json, jsonify, request, url_for, \
    make_response, g, current_app
from hashlib import md5
from contextlib import closing
import re
import sqlite3

########## Configuration ###########
DATABASE = 'users.db'
DEBUG = True
####################################


app = Flask(__name__)
app.config.from_object(__name__)


def user_repr(user):
  user_r = user.copy()
  user_r['uri'] = url_for('get_user', uid=user['id'], _external=True)
  try:
    del user_r['password']
  except KeyError, e:
    pass
  return user_r


def connect_db():
  return sqlite3.connect(app.config['DATABASE'])


def init_db(data_file=None):
  with closing(connect_db()) as db:
    with app.open_resource('schema.sql') as f:
      db.cursor().executescript(f.read())
    if data_file != None:
      with app.open_resource(data_file) as f:
        db.cursor().executescript(f.read())
    db.commit()


def valid_email_address(email):
  """
  This function validates most (>99%) addresses correctly that follow
  RFC 5322. To be sure that the email address is valid, we would have
  to check if it is actually in use.
  See http://www.regular-expressions.info/email.html
  """
  return re.match(r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/"
      "=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9]"
      "(?:[a-z0-9-]*[a-z0-9])?", email) and True or False


def hash_password(password):
  p = md5()
  p.update(password)
  return p.hexdigest()

  
def get_uid_by_name(name, like=False):
  like_clause = like and ' LIKE "%%%s%%"' or '="%s"'
  query = 'SELECT id, name, email FROM users WHERE name%s' % like_clause
  cur = g.db.execute(query % name)
  row = cur.fetchone()
  if row == None:
    return None
  return row[0]

  
@app.before_request
def before_request():
  g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
  g.db.close()


@app.route('/')
def index():
  return make_response('User API')


@app.errorhandler(400)
def bad_request(error):
  return make_response(
      json.dumps(
        { 
          'error': 'Bad request',
          'error code': 400
        }
      ), 
      400,
      {"Content-Type": "application/json"})


@app.errorhandler(404)
def resource_not_found(error):
  return make_response(
      json.dumps(
        { 
          'error': 'Not found',
          'error code': 404 
        } 
      ), 
      404,
      {"Content-Type": "application/json"})


@app.route('/users/<string:name>', methods=["GET"])
def get_user_by_name(name):
  uid = get_uid_by_name(name, like=True)
  if uid == None:
    abort(404)
  return get_user(uid)

  
@app.route('/users/<int:uid>', methods=['GET'])
def get_user(uid):
  cur = g.db.execute('SELECT id, name, email FROM users WHERE id=%i' % uid)
  row = cur.fetchone()
  if row == None:
    abort(404)
  user = dict(id=row[0], name=row[1], email=row[2])
  return jsonify(
        { 'user': user_repr(user) } 
      )


@app.route('/users', methods=['GET', 'OPTIONS'])
def get_users():
  if request.method == 'OPTIONS':
    response = current_app.make_default_options_response()
    response.headers["Allow"] = "GET, PUT, POST, OPTIONS"
    return response
  cur = g.db.execute('SELECT id, name, email FROM users ORDER BY id ASC')
  users = [
        dict(
            id=row[0],
            name=row[1],
            email=row[2]
          )
        for row in cur.fetchall()
      ]
  return jsonify(
        { 'users': map(user_repr, users) }
      )
get_users.provide_automatic_options = False


@app.route('/users', methods=["DELETE", "PATCH", "TRACE"])
def method_not_allowed_users():
  return make_response(
      json.dumps(
        {
          'error': 'Method Not Allowed',
          'error code': 405
        }
      ),
      405,
      {"Content-Type": "application/json"})


@app.route('/users', methods=["POST", "PUT"])
def create_user():
  if not request.json or \
      not 'name' in request.json or \
      not 'email' in request.json or \
      not 'password' in request.json or \
      request.json['name'] == None or \
      request.json['name'] == '' or \
      request.json['email'] == None or \
      not valid_email_address(request.json['email']) or \
      request.json['password'] == None or \
      len(request.json['password']) < 8:
    abort(400)
  password = hash_password(request.json['password'])
  try:
    cur = g.db.execute(
        'INSERT INTO users (id,name,email,password) VALUES '
        '(NULL,"%s","%s","%s")' %
        (request.json['name'], request.json['email'], password)
      )
  except sqlite3.IntegrityError, e:
    abort(400)
  cur = g.db.execute('SELECT last_insert_rowid()')
  new_user_id = cur.fetchone()[0]
  g.db.commit()
  new_user = {
    'id': new_user_id,
    'name': request.json['name'],
    'email': request.json['email'],
    'password': password
  }
  return jsonify(
      { 'user created': user_repr(new_user) }
    )


@app.route('/users/<string:name>', methods=["PUT", "PATCH"])
def update_user_by_name(uid):
  uid = get_uid_by_name(name, like=False)
  if uid == None:
    abort(404)
  update_user(uid)


@app.route('/users/<int:uid>', methods=["PUT", "PATCH"])
def update_user(uid):
  if not request.json or len(request.json) == 0:
    abort(400)
  cur = g.db.execute('SELECT id, name, email FROM users WHERE id=%i' % uid)
  row = cur.fetchone()
  if row == None:
    abort(404)
  user = dict(id=row[0], name=row[1], email=row[2])
  modified_user = user
  for field, value in request.json.items():
    if field in ["name", "email", "password"]:
      if value == None or \
          value == '' or \
          field == "email" and not valid_email_address(value) or \
          field == "password" and len(value) < 8:
        abort(400)
      if field == "password":
        value = hash_password(value)
      modified_user[field] = value
  cur = g.db.execute(
      'UPDATE users (id,name,email,password) VALUES (%i,%s,%s,%s)' %
        (uid,request.json['name'], request.json['email'], password)
    )
  g.db.commit()
  return jsonify(
      { 'user modified': user_repr(modified_user) }
    )


@app.route('/users/<string:name>', methods=["DELETE"])
def delete_user_by_name(name):
  uid = get_uid_by_name(name, like=false)
  if uid == None:
    abort(404)
  return delete_user(uid)


@app.route('/users/<int:uid>', methods=["DELETE"])
def delete_user(uid):
  cur = g.db.execute('SELECT id, name, email FROM users WHERE id=%i' % uid)
  row = cur.fetchone()
  if row == None:
    abort(404)
  deleted_user = dict(id=row[0], name=row[1], email=row[2])
  cur = g.db.execute('DELETE FROM users WHERE id=%i' % uid)
  g.db.commit()
  return jsonify(
      { 'user deleted': user_repr(deleted_user) }
    )


if __name__ == '__main__':
  app.run()
  
