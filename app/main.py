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
      "name": "Club",
    },
    {
      "name": "Member",
    },
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

@app.get("/api/club", tags=["Club"])
async def read_club(response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    res = session.query(dbList).filter_by(uid = uid).all()
  ret = []
  for i in res:
    tmp = {
      "cid": i.cid,
      "name": i.name,
      "freeze": i.freeze
    }
    ret.append(tmp)
  return parse_obj_as(List[ClubList], ret)

@app.post("/api/club", tags=["Club"])
async def create_club(data: CreateClub, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    Club = dbClub(name=data.name, director=uid)
    session.add(Club)
    session.commit()

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).all()
    cid = res[-1].cid

  with SessionContext() as session:
    ClubList = dbList(uid=uid, cid=cid, name=data.name, freeze=0)
    session.add(ClubList)
    session.commit()

  response.status_code = 201
  tmp = {
    "name": data.name,
    "director": uid
  }
  return tmp

@app.put("/api/club/{cid}", tags=["Club"])
async def update_club(cid: int, data: UpdateClub, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"Access denied"}

  with SessionContext() as session:
    res = session.query(dbList).filter_by(uid = data.director, cid = cid)
  if not len(list(res)):
    response.status_code = 404
    return {"User does not exist"}

  with SessionContext() as session:
    Club = session.query(dbClub).filter_by(cid = cid)
    Club.update({"name": data.name, "director": data.director})
    session.commit()

  with SessionContext() as session:
    ClubList = session.query(dbList).filter_by(cid = cid)
    ClubList.update({"name": data.name})
    session.commit()

  tmp = {
    "name": data.name,
    "director": data.director
  }
  return tmp

@app.delete("/api/club/{cid}", tags=["Club"])
async def delete_club(cid: int, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"Access denied"}

  with SessionContext() as session:
    ClubList = session.query(dbList).filter_by(cid = cid)
    ClubList.delete()
    session.commit()

  with SessionContext() as session:
    Club = session.query(dbClub).filter_by(cid = cid)
    Club.delete()
    session.commit()

  response.status_code = 204
  return {}

@app.post("/api/club/member", tags=["Member"])
async def member(data: InviteToken, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  cid = check_invite(data.token)
  if not cid:
    response.status_code = 400
    return {"Access denied"}

  with SessionContext() as session:
    res = session.query(dbList).filter_by(uid = uid).filter_by(cid = cid)
  if len(list(res)):
    response.status_code = 202
    return {"Already uid exists"}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 404
    return {"Club does not exist"}

  with SessionContext() as session:
    ClubList = dbList(uid=uid, cid=cid, name=res[0].name, freeze=0)
    session.add(ClubList)
    session.commit()

  tmp = {
    "name": res[0].name,
    "cid": cid,
  }
  return tmp

@app.get("/api/club/{cid}/member", tags=["Member"])
async def read_member(cid: int, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"Access denied"}

  with SessionContext() as session:
    res = session.query(dbList).filter_by(cid = cid)

  user_list = []
  for i in res:
    user_list.append([i.uid, i.freeze])

  ret = []
  for i in user_list:
    with SessionContext() as session:
      res = session.query(dbUser).filter_by(uid = i[0])
    tmp = {
      "uid": res[0].uid,
      "role": res[0].role,
      "name": res[0].name,
      "num": res[0].num,
      "phone": res[0].phone,
      "freeze": i[1]
    }
    ret.append(tmp)
  return parse_obj_as(List[ClubUserList], ret)

@app.post("/api/club/{cid}/member", tags=["Member"])
async def invite_member(cid: int, data: InviteMember, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"Access denied"}

  token = sign_invite(cid, data.end)

  tmp = {
    "token": token,
  }
  return tmp


@app.patch("/api/club/{cid}/member/{user_id}", tags=["Member"])
async def patch_member(cid: int, user_id: str, data: Freeze, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"Access denied"}

  with SessionContext() as session:
    ClubList = session.query(dbList).filter_by(uid = user_id).filter_by(cid = cid)
    ClubList.update({"freeze": data.freeze})
    session.commit()
  response.status_code = 204
  return {"freeze": data.freeze}

@app.delete("/api/club/{cid}/member/{user_id}", tags=["Member"])
async def delete_member(cid: int, user_id: str, response: Response, auth: Optional[str] = Header(None)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"Unauthorized"}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"Access denied"}

  with SessionContext() as session:
    ClubList = session.query(dbList).filter_by(uid = user_id).filter_by(cid = cid)
    ClubList.delete()
    session.commit()
  response.status_code = 204
  return {}

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
