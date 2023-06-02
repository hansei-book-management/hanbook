from typing import List, Optional

from fastapi import FastAPI, Response, Header, status
from pydantic import BaseModel, parse_obj_as

from starlette.middleware.cors import CORSMiddleware

from app.config import *
from app.model import *
from app.utils import *
from app.data import *

tags_metadata = [
    {
      "name": "Authentication",
    },
    {
      "name": "User",
    }
]

app = FastAPI(openapi_tags=tags_metadata)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/auth", tags=["Authentication"])
async def sign_in(data: UserData, response: Response):
  with SessionContext() as session:
    hash_passwd = hashgen(data.passwd)
    res = session.query(dbUser).filter_by(name = data.name, passwd = hash_passwd)
  if len(list(res)):
    if res[0].role == "admin":
      auth = sign_admin(res[0].name)
    else:
      auth = sign_auth(res[0].name)
    response.status_code = 201
    return {"auth": auth}
  else:
    response.status_code = 401
    return {"Auth fail"}

@app.patch("/api/auth", tags=["Authentication"])
async def change_passwd(data: UserPasswd, response: Response, auth: Optional[str] = Header(None)):
  user_name = check_auth(auth)
  if not user_name:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    hash_passwd = hashgen(data.passwd)
    User = session.query(dbUser).filter_by(name = user_name)
    User.update({"passwd": hash_passwd})
    session.commit()
  return {"passwd": data.passwd}

@app.get("/api/user", tags=["User"])
async def read_account(response: Response, admin: Optional[str] = Header(None)):
  with SessionContext() as session:
    res = session.query(dbUser).all()
  ret = []
  for i in res:
    tmp = {
      "name": i.name,
      "role": i.role
    }
    ret.append(tmp)
  return parse_obj_as(List[UserList], ret)

@app.post("/api/user", tags=["User"])
async def create_account(data: UserData, response: Response):
  with SessionContext() as session:
    res = session.query(dbUser).filter_by(name = data.name)
  if len(list(res)):
    response.status_code = 202
    return {"Already name exists"}
  with SessionContext() as session:
    hash_passwd = hashgen(data.passwd)
    User = dbUser(name=data.name, passwd=hash_passwd, role="user")
    session.add(User)
    session.commit()
  response.status_code = 201
  return {"name": data.name, "passwd": data.passwd, "role": "user"}

@app.put("/api/user/{user_name}", tags=["User"])
async def update_account(user_name: str, data: UserPasswd, response: Response, auth: Optional[str] = Header(None)):
  user_name = check_admin(auth)
  if not user_name:
    response.status_code = 401
    return {"Auth fail"}

  with SessionContext() as session:
    res = session.query(dbUser).filter_by(name = user_name)
  if not len(list(res)):
    response.status_code = 404
    return {"Name not found"}
  with SessionContext() as session:
    hash_passwd = hashgen(data.passwd)
    User = session.query(dbUser).filter_by(name = user_name)
    User.update({"passwd": hash_passwd})
    session.commit()
  return {"passwd": data.passwd}

@app.delete("/api/user/{user_name}", tags=["User"])
async def delete_account(user_name: str, response: Response, auth: Optional[str] = Header(None)):
  user_name = check_admin(auth)
  if not user_name:
    response.status_code = 401
    return {"Auth fail"}

  with SessionContext() as session:
    User = session.query(dbUser).filter_by(name = user_name)
    User.delete()
    session.commit()
  response.status_code = 204
  return {}
