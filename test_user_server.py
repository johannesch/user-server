#!/usr/bin/env python

import os
import user_server
import unittest
import tempfile
import sqlite3
from flask import json
from contextlib import closing

class UserServerTestCase(unittest.TestCase):

  def setUp(self):
      self.db_file, user_server.app.config['DATABASE'] = tempfile.mkstemp()
      user_server.app.config['TESTING'] = True
      self.app = user_server.app.test_client()
      user_server.init_db()

      
  def tearDown(self):
      os.close(self.db_file)
      os.unlink(user_server.app.config['DATABASE'])


  def test_root(self):
    response = self.app.get('/')
    self.assertIn('User API', response.data)


  def test_empty_db(self):
    response = self.app.get('/users')
    self.assertIn('"users": []', response.data)


  def test_create_user_post(self):
    self.create_user_m(self.app.post)


  def test_create_user_put(self):
    self.create_user_m(self.app.put)


  def create_user_m(self, method):
    response = method('/users', data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hahu@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 200)
    self.assertIn('Hans Huber', response.data)
    self.assertIn('hahu@example.com', response.data)
    self.assertNotIn('password', response.data)
    self.assertNotIn('thisisapassword', response.data)
    self.assertIn('"id":', response.data)
    response = self.app.get('/users')
    self.assertIn('"users": [', response.data)
    response = method('/users', data='{"password": "thisisapassword',
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method('/users', data=json.dumps(
          {
            "email": "hahu@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method('/users', data=json.dumps(
          {
            "name": "Hans Huber",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method('/users', data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hahu@example.com",
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method('/users', data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hahu@example.com",
            "password": "tooshrt"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method('/users', data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hahu@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    


  def test_options_users(self):
    response = self.app.open('/users', method='OPTIONS')
    self.assertEqual(response._status, '200 OK')
    for method in ['GET', 'PUT', 'POST', 'OPTIONS']:
      self.assertIn(method, response.headers['Allow'])
    for method in ['DELETE', 'PATCH', 'TRACE']:
      self.assertNotIn(method, response.headers['Allow'])
    self.assertEqual(response.headers['Content-Length'], '0')


  def test_unallowed_methods_users(self):
    for method in ['DELETE', 'PATCH', 'TRACE']:
      response = self.app.open('/users', method=method)
      self.assertEqual(response._status_code, 405)
      self.assertIn('"error": "Method Not Allowed"', response.data)
      self.assertIn('"error code": 405', response.data)


  def test_get_uid_by_name(self):
    ctx = user_server.app.test_request_context()
    ctx.push()
    user_server.app.preprocess_request()
    uid = user_server.get_uid_by_name("Hans Huber")
    self.assertEqual(uid, None)
    self.app.post('/users', data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hahu@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    uid = user_server.get_uid_by_name("Hans Huber")
    self.assertEqual(uid, 1)
    uid = user_server.get_uid_by_name("Hans")
    self.assertEqual(uid, None)
    uid = user_server.get_uid_by_name("Hans", like=True)
    self.assertEqual(uid, 1)
    ctx.pop()


  def test_hash_password(self):
    self.assertEqual(user_server.hash_password('password'),
        '5f4dcc3b5aa765d61d8327deb882cf99')
    self.assertEqual(user_server.hash_password(
        '345eztjhnt78i4RTHGSFTGDGHjdtz34'),
        '420231ae9c07a78741c76f82d0275208')


  def test_valid_email_address(self):
    self.assertEqual(user_server.valid_email_address('email'), False)
    self.assertEqual(user_server.valid_email_address('email@'), False)
    self.assertEqual(user_server.valid_email_address('@email'), False)
    self.assertEqual(user_server.valid_email_address('ema@il'), False)
    self.assertEqual(user_server.valid_email_address('e@e@a.com'), False)
    self.assertEqual(user_server.valid_email_address('e@e.com'), True)
    self.assertEqual(user_server.valid_email_address(
        'hahu@example.com'), True)


  def test_init_db(self):
    user_server.init_db('test_data.sql')
    with closing(sqlite3.connect(
        user_server.app.config['DATABASE'])) as db:
      row = db.cursor().execute(
          'SELECT sql FROM SQLITE_MASTER WHERE type="table" and name="users"')
      self.assertEqual(row.fetchone()[0], u'CREATE TABLE users (\n  '
          'id integer PRIMARY KEY autoincrement,\n  name string UNIQUE '
          'NOT NULL,\n  email string NOT NULL,\n  password '
          'string NOT NULL\n)')
      row = db.cursor().execute(
          'SELECT sql FROM SQLITE_MASTER WHERE type="index" and '
          'name="name_index"')
      self.assertEqual(row.fetchone()[0], u'CREATE UNIQUE INDEX name_index '
          'ON users (name)')


  def test_user_repr(self):
    ctx = user_server.app.test_request_context()
    ctx.push()
    user_server.app.preprocess_request()
    ur = user_server.user_repr(
        dict(
          id=1,
          name="Hans Huber",
          email="hahu@example.com",
          password="15c4683193f210ca9c640af9241e8c18"
        )
      )
    self.assertEqual(ur['id'], 1)
    self.assertEqual(ur['email'], 'hahu@example.com')
    self.assertEqual(ur['name'], 'Hans Huber')
    self.assertEqual(ur['uri'], 'http://localhost/users/1')
    self.assertNotIn('password', ur.keys())
    ctx.pop()


  def test_update_user_put(self):
    self.update_user_m(self.app.put)

  def test_update_user_patch(self):
    self.update_user_m(self.app.patch)

  def test_update_user_by_name_put(self):
    self.update_user_m(self.app.put, name=True)

  def test_update_user_by_name_patch(self):
    self.update_user_m(self.app.patch, name=True)


  def update_user_m(self, method, name=False):
    user_server.init_db('test_data.sql')
    uri = name and '/users/Hans%20Huber' or '/users/1'
    response = method(uri, data='{"password": "thisi',
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method(uri, data='',
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method(uri, data='')
    self.assertEqual(response._status_code, 400)
    response = method(uri, data=json.dumps(
          {
            "name": None,
            "email": "hanshu@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method(uri, data=json.dumps(
          {
            "name": "",
            "email": "hanshu@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method(uri, data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hanshu@exampl",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method(uri, data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hanshu@example.com",
            "password": "this"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 400)
    response = method(uri, data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hanshu@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 200)
    self.assertIn('hanshu@example.com', response.data)
    self.assertIn('Hans Huber', response.data)
    self.assertNotIn('password', response.data)
    response = method(uri, data=json.dumps(
          {
            "name": "Hansi",
            "email": "hansi@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 200)
    self.assertIn('hansi@example.com', response.data)
    self.assertIn('Hansi', response.data)
    uri = name and '/users/Hansi' or '/users/1'
    response = method(uri, data=json.dumps(
          {
            "password": "thisisanotherpassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 200)
    self.assertIn('Hansi', response.data)
    self.assertIn('hansi@example.com', response.data)
    with closing(sqlite3.connect(
        user_server.app.config['DATABASE'])) as db:
      cursor = db.cursor().execute('SELECT password FROM users WHERE id=1')
      row = cursor.fetchone()
      self.assertEqual(row[0], '1042e9c6b7770c5a8d73d7274bb1e787')
    uri = name and '/users/Hans Huber' or '/users/4'
    response = method(uri, data=json.dumps(
          {
            "name": "Hans Huber",
            "email": "hanshu@example.com",
            "password": "thisisapassword"
          }
        ),
        content_type='application/json'
      )
    self.assertEqual(response._status_code, 404)


  def test_get_users(self):
    user_server.init_db('test_data.sql')
    response = self.app.get('/users', content_type='application/json')
    self.assertEqual(response._status_code, 200)
    users = json.loads(response.data)
    self.assertEqual(len(users['users']), 3)
    for user in users['users']:
      self.assertEqual(len(user.keys()), 4)
      self.assertIn('name', user.keys())
      self.assertIn('email', user.keys())
      self.assertIn('uri', user.keys())
      self.assertIn('id', user.keys())


  def test_get_user(self):
    self.get_user_m()


  def test_get_user_by_name(self):
    self.get_user_m(name=True)


  def get_user_m(self, name=False):
    user_server.init_db('test_data.sql')
    uri = name and '/users/Hansi' or '/users/4'
    response = self.app.get(uri, content_type='application/json')
    self.assertEqual(response._status_code, 404)
    uri = name and '/users/Hans%20Huber' or '/users/1'
    response = self.app.get(uri, content_type='application/json')
    self.assertEqual(response._status_code, 200)
    user = json.loads(response.data)['user']
    self.assertEqual(len(user.keys()), 4)
    self.assertIn('name', user.keys())
    self.assertIn('email', user.keys())
    self.assertIn('uri', user.keys())
    self.assertIn('id', user.keys())


  def test_delete_user(self):
    self.delete_user_m()


  def test_delete_user_by_name(self):
    self.delete_user_m(name=True)
   
    
  def delete_user_m(self, name=False):
    user_server.init_db('test_data.sql')
    uri = name and '/users/Hansi' or '/users/4'
    response = self.app.delete(uri, content_type='application/json')
    self.assertEqual(response._status_code, 404)
    uri = name and '/users/Hans%20Huber' or '/users/1'
    response = self.app.delete(uri, content_type='application/json')
    self.assertEqual(response._status_code, 200)
    user = json.loads(response.data)['user deleted']
    self.assertEqual(len(user.keys()), 4)
    self.assertIn('name', user.keys())
    self.assertIn('email', user.keys())
    self.assertIn('uri', user.keys())
    self.assertIn('id', user.keys())
    response = self.app.get('/users', content_type='application/json')
    self.assertEqual(response._status_code, 200)
    users = json.loads(response.data)
    self.assertEqual(len(users['users']), 2)
    uri = name and '/users/Hans%20Huber' or '/users/1'
    response = self.app.delete(uri, content_type='application/json')
    self.assertEqual(response._status_code, 404)
    
    
if __name__ == '__main__':
    unittest.main()