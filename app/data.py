from typing import List, Optional

from pydantic import BaseModel, parse_obj_as

class UserData(BaseModel):
  uid: str
  passwd: str

class UserList(BaseModel):
  uid: str
  role: str

class UserPasswd(BaseModel):
  passwd: str
