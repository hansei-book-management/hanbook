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
    res = session.query(dbUser).filter_by(uid = data.uid, passwd = hash_passwd)
  if len(list(res)):
    if res[0].role == "admin":
      auth = sign_admin(res[0].uid)
    else:
      auth = sign_auth(res[0].uid)
    response.status_code = 201
    return {"auth": auth}
  else:
    response.status_code = 401
    return {"Auth fail"}

@app.patch("/api/auth", tags=["Authentication"])
async def change_passwd(data: UserPasswd, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    hash_passwd = hashgen(data.passwd)
    User = session.query(dbUser).filter_by(uid = uid)
    User.update({"passwd": hash_passwd})
    session.commit()
  return {"passwd": data.passwd}

@app.get("/api/user", tags=["User"])
async def read_account(response: Response, auth: Optional[str] = Header(None)):
  admin = check_admin(auth)
  if not admin:
    response.status_code = 401
    return {"Auth fail"}

  with SessionContext() as session:
    res = session.query(dbUser).all()
  ret = []
  for i in res:
    tmp = {
      "uid": i.uid,
      "role": i.role,
      "name": i.name,
      "num": i.num,
      "phone": i.phone
    }
    ret.append(tmp)
  return parse_obj_as(List[UserList], ret)

@app.post("/api/user", tags=["User"])
async def create_account(data: UserSignUp, response: Response, admin: Optional[str] = Header(None)):
  with SessionContext() as session:
    res = session.query(dbUser).filter_by(uid = data.uid)
  if len(list(res)):
    response.status_code = 202
    return {"Already uid exists"}
  if admin == ADMIN_KEY:
    user_role = "admin"
  else:
    user_role = "user"
  with SessionContext() as session:
    hash_passwd = hashgen(data.passwd)
    User = dbUser(uid=data.uid, passwd=hash_passwd, role=user_role, name=data.name, num=data.num, phone=data.phone)
    session.add(User)
    session.commit()
  response.status_code = 201
  tmp = {
    "uid": data.uid,
    "passwd": data.passwd,
    "role": user_role,
    "name": data.name,
    "num": data.num,
    "phone": data.phone
  }
  return tmp

@app.put("/api/user/{uid}", tags=["User"])
async def update_account(uid: str, data: UserPasswd, response: Response, auth: Optional[str] = Header(None)):
  admin = check_admin(auth)
  if not admin:
    response.status_code = 401
    return {"Auth fail"}

  with SessionContext() as session:
    res = session.query(dbUser).filter_by(uid = uid)
  if not len(list(res)):
    response.status_code = 404
    return {"Name not found"}
  with SessionContext() as session:
    hash_passwd = hashgen(data.passwd)
    User = session.query(dbUser).filter_by(uid = uid)
    User.update({"passwd": hash_passwd})
    session.commit()
  return {"passwd": data.passwd}

@app.delete("/api/user/{uid}", tags=["User"])
async def delete_account(uid: str, response: Response, auth: Optional[str] = Header(None)):
  admin = check_admin(auth)
  if not admin:
    response.status_code = 401
    return {"Auth fail"}

  with SessionContext() as session:
    User = session.query(dbUser).filter_by(uid = uid)
    User.delete()
    session.commit()
  response.status_code = 204
  return {}
