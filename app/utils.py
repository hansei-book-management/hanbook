import jwt

from time import time
from hashlib import sha256
from uuid import uuid4

from app.config import *

from base64 import b64decode

DAY = 86400

def image_decode(text):
  try:
    return b64decode(text)
  except:
    return False

def uuid_gen():
  return uuid4().hex

def get_time():
  return int(time())

def sign_auth(user_id):
  end = int(time()) + DAY
  tmp = {
    "id": user_id,
    "type": "auth",
    "role": "user",
    "end": end,
  }
  token = jwt.encode(tmp, SECRET, algorithm="HS256")
  return token

def check_auth(token):
  unix_time = int(time())
  try:
    tmp = jwt.decode(token, SECRET, algorithms="HS256")
    if tmp["type"] == "auth" and tmp["end"] > unix_time:
      return tmp["id"]
    else:
      return False
  except:
    return False

def sign_admin(user_id):
  end = int(time()) + DAY
  tmp = { 
    "id": user_id,
    "type": "auth",
    "role": "admin",
    "end": end,
  }
  token = jwt.encode(tmp, SECRET, algorithm="HS256")
  return token

def check_admin(token):
  unix_time = int(time())
  try:
    tmp = jwt.decode(token, SECRET, algorithms="HS256")
    if tmp["type"] == "auth" and tmp["end"] > unix_time and tmp["role"] == "admin":
      return tmp["id"]
    else:
      return False
  except:
    return False

def hashgen(text):
  salt_text = SALT + text
  return sha256(salt_text.encode()).hexdigest()
