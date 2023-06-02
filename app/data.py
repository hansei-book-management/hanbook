from typing import List, Optional

from pydantic import BaseModel, parse_obj_as

class UserData(BaseModel):
  name: str
  passwd: str

class UserList(BaseModel):
  name: str
  role: str

class UserPasswd(BaseModel):
  passwd: str
