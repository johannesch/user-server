user-server
===========

Requirements
------------

flask 0.8
sqlite3

Running the server
------------------

```
python user_server.py
```

The server will be running on http://localhost:5000/users

Running the tests
-----------------

```
python test_user_server.py
```

To see test code coverage (using the coverage python program):

```
python-coverage run --source . test_user_server.py
python-coverage report -m
```

Interactive tests
-----------------

```
curl -i -X PUT -H "Content-Type: application/json" -d '{"name": "Hans Huber", "email": "hahu@example.com", "password": "verysecretpassword"}' http://localhost:5000/users
curl -i -X PUT -H "Content-Type: application/json" -d '{"name": "Hans Huber", "email": "hahu@example.com", "password": "verysecretpassword"}' http://localhost:5000/users
```

Will result in:

```
HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 142
Server: Werkzeug/0.8.1 Python/2.7.3
Date: Fri, 11 Jul 2014 14:42:45 GMT

{
  "user created": {
    "uri": "http://localhost:5000/users/4",
    "email": "hahu@example.com",
    "name": "Hans Huber",
    "id": 4
  }
}
[...]
HTTP/1.0 400 BAD REQUEST
Content-Type: application/json
Content-Length: 43
Server: Werkzeug/0.8.1 Python/2.7.3
Date: Fri, 11 Jul 2014 14:42:59 GMT

{"error code": 400, "error": "Bad request"}
```

The socond time, the user already exists.