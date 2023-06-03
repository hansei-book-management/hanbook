from typing import List, Optional

from pydantic import BaseModel, parse_obj_as

class UserData(BaseModel):
  uid: str
  passwd: str

class UserSignUp(BaseModel):
  uid: str
  passwd: str
  name: str
  num: str
  phone: str

class UserList(BaseModel):
  uid: str
  role: str
  name: str
  num: str
  phone: str

class UserPasswd(BaseModel):
  passwd: str
