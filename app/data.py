from typing import List, Optional

from pydantic import BaseModel, parse_obj_as

class CreateClub(BaseModel):
  name: str

class UpdateClub(BaseModel):
  name: str
  director: str

class ClubList(BaseModel):
  cid: int
  name: str

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
