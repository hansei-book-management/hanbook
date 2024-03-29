from typing import List, Optional

from fastapi import FastAPI, Depends, Response, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import  parse_obj_as
import uvicorn

from starlette.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordBearer
from app.config import *
from app.model import *
from app.utils import *
from app.data import *

from app.session import rd

from app.ext.naver_book_api import *

import json
import random

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

tags_metadata = [
    {
      "name": "Book",
    },
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
    "http://127.0.0.1:4173",
    "http://127.0.0.1:5173",
    CORS
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_cache = {}

@app.post("/api/books/search", tags=["Book"])
async def search_books(query: str, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid)
  if not len(list(res)):
    response.status_code = 400
    return {"동아리 부장만 사용할 수 있습니다."}

  response.status_code = 200
  res = query_book(query)
  return {"result": res}


@app.get("/api/books", tags=["Book"])
async def read_book(response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  res = query_book_list()
  return {"result": res}

@app.get("/api/club/{cid}/book", tags=["Book"])
async def read_book(cid: int, response: Response, auth: str = Depends(oauth2_scheme)):
    global user_cache

    user_id = check_auth(auth)
    if not user_id:
      response.status_code = 401
      return {"message": "로그인이 필요합니다."}

    with SessionContext() as session:
      res = session.query(dbClub).filter_by(cid = cid)
    
    if not len(list(res)):
      response.status_code = 401
      return {"message": "동아리를 찾을 수 없습니다."}


    club_name = res[0].name

    ret = []
    with SessionContext() as session:
      res = session.query(dbBook).filter_by(cid = cid)
    book_list = []
    
    freeze_cache = {}

    for j in res:
      if j.uid in user_cache:
        usr = user_cache[j.uid]
      else:
        with SessionContext() as session:
          r0 = session.query(dbUser).filter_by(uid = j.uid)
        usr = {
          "name": r0[0].name,
        }
        user_cache[j.uid] = usr
      
      if j.uid in freeze_cache:
        usr["freeze"] = freeze_cache[j.uid]
      else:
        with SessionContext() as session:
          r1 = session.query(dbList).filter_by(cid = j.cid).filter_by(uid = j.uid)

        usr["freeze"] = r1[0].freeze
        freeze_cache[j.uid] = r1[0].freeze

      tmp = {
        "bid": j.bid,
        "cid": j.cid,
        "uid": j.uid,
        "end": j.end,
        "data": json.loads(j.data),
        "user": usr
      }
      book_list.append(tmp)

    tmp = {
      "cid": cid,
       "name": club_name,
       "book": book_list,
    }
    ret.append(tmp)
    return {"result": ret}

@app.get("/api/club/member/{uid}/book", tags=["Book"])
async def get_book(uid: str, response: Response, auth: str = Depends(oauth2_scheme)):
    user_id = check_auth(auth)
    if not user_id:
      response.status_code = 401
      return {"message": "로그인이 필요합니다."}

    ret = []
    with SessionContext() as session:
      club = session.query(dbList).filter_by(uid = uid)
      user_books_count = session.query(dbBook).filter_by(uid = uid).count()
    
    if uid in user_cache:
        usr = user_cache[uid]
    else:
        with SessionContext() as session:
            r0 = session.query(dbUser).filter_by(uid = uid)
        if not len(list(r0)):
          return {"message": "해당 사용자를 찾을 수 없습니다."}
        usr = {
          "name": r0[0].name,
        }
        user_cache[uid] = usr

    for i in club:
      with SessionContext() as session:
          r1 = session.query(dbList).filter_by(cid = i.cid).filter_by(uid = uid)

      usr["freeze"] = r1[0].freeze

      with SessionContext() as session:
        res = session.query(dbBook).filter_by(cid = int(i.cid)).filter_by(uid = uid)
      book_list = []
      for j in res:
        tmp = {
          "bid": j.bid,
          "cid": j.cid,
          "uid": j.uid,
          "end": j.end,
          "data": json.loads(j.data),
        }
        book_list.append(tmp)

      tmp = {
          "cid": i.cid,
          "name": i.name,
          "book": book_list,
          "borrowBook": user_books_count,
          "user": usr
        }
      ret.append(tmp)
    return {"result": ret}

@app.post("/api/club/{cid}/book", tags=["Book"])
async def add_book(cid: int, data: AddBook, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "자신이 부장인 동아리에만 도서를 추가할 수 있습니다."}

  ISBN = data.isbn.split(",")

  for isbn in ISBN:
    book_data = query_book_isbn(isbn)
    if not book_data:
      response.status_code = 404
      return {"message": "해당하는 도서를 찾을 수 없습니다."}

    with SessionContext() as session:
      Book = dbBook(cid=cid, data=json.dumps(book_data), uid=uid, end=0)
      session.add(Book)
      session.commit()

  tmp = {
    "isbn": data.isbn,
    "cid": cid
  }

  response.status_code = 201
  return {"result": tmp}

@app.post("/api/club/{cid}/book/{bid}", tags=["Book"])
async def rent_book(cid: int, bid: int, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbList).filter_by(uid = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "자신이 속한 동아리에서만 도서를 대여할 수 있습니다."}

  with SessionContext() as session:
    res = session.query(dbList).filter_by(uid = uid).filter_by(cid = cid)
  if len(list(res)):
    if res[0].freeze > get_time(): 
      response.status_code = 400
      return {"message": "대여한 도서를 기간 내에 반납하지 않아 대여가 일시 정지되었어요."}

  with SessionContext() as session:
    res = session.query(dbBook).filter_by(bid = bid).filter_by(cid = cid).filter_by(end = 0)
  if not len(list(res)):
    response.status_code = 404
    return {"message": "해당 도서를 대여할 수 없습니다."}

  with SessionContext() as session:
    res = session.query(dbBook).filter_by(bid = bid).filter_by(cid = cid).filter_by(uid = uid)
  if len(list(res)):
    for i in res:
      if i.end != 0:
        response.status_code = 400
        return {"message": "이미 대여한 도서입니다."}

  end = get_time() + (DAY * 14)

  with SessionContext() as session:
    Book = session.query(dbBook).filter_by(cid = cid).filter_by(bid = bid)
    Book.update({"uid": uid, "end": end})
    session.commit()

  response.status_code = 200
  return {"result": {'end': end}}

@app.delete("/api/club/{cid}/book/{bid}", tags=["Book"])
async def delete_book(cid: int, bid: int, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "자신이 부장인 동아리에만 도서를 삭제할 수 있습니다."}

  with SessionContext() as session:
    Book = session.query(dbBook).filter_by(cid = cid).filter_by(bid = bid)
    Book.delete()
    session.commit()

  return {"message": "성공적으로 도서를 삭제했습니다."}

@app.patch("/api/club/{cid}/book/{bid}", tags=["Book"])
async def return_book(cid: int, bid: int, data: ReturnBook, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbList).filter_by(uid = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "자신이 속한 동아리에만 도서를 반납할 수 있습니다."}

  with SessionContext() as session:
    res = session.query(dbBook).filter_by(bid = bid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 404
    return {"message": "해당하는 도서를 찾을 수 없습니다."}
  if res[0].end == 0:
    response.status_code = 404
    return {"message": "이미 반납 처리된 도서입니다."}
  if res[0].end < get_time():
    freeze = get_time() + (DAY * 10)
    with SessionContext() as session:
      ClubList = session.query(dbList).filter_by(uid = uid).filter_by(cid = cid)
      ClubList.update({"freeze": freeze})
      session.commit()

  save_file = image_decode(data.image)
  if not save_file:
    response.status_code = 400
    return {"message": "이미지 업로드에 실패하였습니다."}

  with SessionContext() as session:
    Book = session.query(dbBook).filter_by(cid = cid).filter_by(bid = bid)
    Book.update({"end": 0})
    session.commit()

  file_name = str(get_time()) + "_" + str(bid)

  fp = open("/code/uploads/" + file_name, "wb")
  fp.write(save_file)
  fp.close()

  response.status_code = 204
  return {}

@app.get('/api/clubs', tags=["Club"])
async def read_clubs(response: Response,):
  
  with SessionContext() as session:
    res = session.query(dbClub).all()
    for i in res:
      with SessionContext() as session:
        book = session.query(dbBook).filter_by(cid = i.cid)
        book_list = []
        for j in book:
          tmp = {
            "bid": j.bid,
            "cid": j.cid,
            "uid": j.uid,
            "end": j.end,
            "data": json.loads(j.data)
          }
          book_list.append(tmp)
        i.book = book_list
    response.status_code = 200
    return {"result": res}


@app.get("/api/club", tags=["Club"])
async def read_club(response: Response, auth: str = Depends(oauth2_scheme)):
    uid = check_auth(auth)
    if not uid:
        response.status_code = 401
        return {"message": "로그인이 필요합니다."}

    ret = []
    with SessionContext() as session:
      club = session.query(dbList).filter_by(uid = uid)
    for i in club:
      with SessionContext() as session:
        res = session.query(dbBook).filter_by(cid = i.cid)
        book_list = []
        for j in res:
          tmp = {
            "bid": j.bid,
            "cid": j.cid,
            "uid": j.uid,
            "end": j.end,
            "data": json.loads(j.data)
          }
          book_list.append(tmp)

      tmp = {
          "cid": i.cid,
          "name": i.name,
          "book": book_list,
        }
      ret.append(tmp)
    return {"result": ret}


@app.post("/api/club", tags=["Club"])
async def create_club(data: CreateClub, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}
  
  with SessionContext() as session:
    if len(list(session.query(dbClub).filter_by(name = data.name).all())):
      response.status_code = 400
      return {"message": "이미 존재하는 동아리 이름입니다."}
    if len(list(session.query(dbClub).filter_by(director = uid).all())):
      response.status_code = 400
      return {"message": "이미 다른 동아리의 부장입니다."}
    userName = session.query(dbUser).filter_by(uid=uid)
    Club = dbClub(name=data.name, director=uid)
    session.add(Club)
    session.commit()

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).all()
    cid = res[-1].cid 

  with SessionContext() as session:
    # change user role to director
    User = session.query(dbUser).filter_by(uid=uid)
    User.update({"role": "director"})
    session.commit()

  with SessionContext() as session:
    ClubList = dbList(uid=uid, cid=cid, name=data.name, freeze=0)
    session.add(ClubList)
    session.commit()

  response.status_code = 201
  tmp = {
    "name": data.name,
    "director": userName[0].name
  }
  return {"result": tmp}

@app.put("/api/club/{cid}", tags=["Club"])
async def update_club(cid: int, data: UpdateClub, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "자신이 부장인 동아리의 정보만 수정할 수 있습니다."}

  with SessionContext() as session:
    res = session.query(dbList).filter_by(uid = data.director, cid = cid)
  if not len(list(res)):
    response.status_code = 404
    return {"message": "부장으로 임명할 사용자를 부원 중에서 찾을 수 없습니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = data.director)
  if len(list(res)):
    response.status_code = 400
    return {"message": "그 사용자는 이미 다른 동아리의 부장입니다."}

  with SessionContext() as session:
    # change user role to director
    User = session.query(dbUser).filter_by(uid=data.director)
    User.update({"role": "director"})
    session.commit()

  with SessionContext() as session:
    # change user role to director
    User = session.query(dbUser).filter_by(uid=uid)
    User.update({"role": "user"})
    session.commit()

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
  return {"result": tmp}

@app.delete("/api/club/{cid}", tags=["Club"])
async def delete_club(cid: int, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "자신이 부장인 동아리만 삭제할 수 있습니다."}

  with SessionContext() as session:
    ClubList = session.query(dbList).filter_by(cid = cid)
    ClubList.delete()
    session.commit()

  with SessionContext() as session:
    Invite = session.query(dbInvite).filter_by(cid = cid)
    Invite.delete()
    session.commit()

  with SessionContext() as session:
    Book = session.query(dbBook).filter_by(cid = cid)
    Book.delete()
    session.commit()

  with SessionContext() as session:
    # change user role to director
    User = session.query(dbUser).filter_by(uid=uid)
    User.update({"role": "user"})
    session.commit()


  with SessionContext() as session:
    Club = session.query(dbClub).filter_by(cid = cid)
    Club.delete()
    session.commit()

  response.status_code = 204
  return {}

@app.post("/api/club/member", tags=["Member"])
async def member(data: InviteToken, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  uuid = data.token

  with SessionContext() as session:
    res = session.query(dbInvite).filter_by(uuid = uuid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "초대 코드가 잘못되었습니다."}
  if res[0].use < 1 or res[0].end < get_time():
    response.status_code = 400
    return {"message": "만료된 초대 코드입니다."}

  cid = res[0].cid
  use = res[0].use

  with SessionContext() as session:
    res = session.query(dbList).filter_by(uid = uid).filter_by(cid = cid)
  if len(list(res)):
    response.status_code = 400
    return {"message": "이미 가입한 동아리입니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 404
    return {"message": "이미 삭제된 동아리입니다."}

  with SessionContext() as session:
    Invite = session.query(dbInvite).filter_by(uuid = uuid)
    Invite.update({"use": use - 1})
    session.commit()

  with SessionContext() as session:
    ClubList = dbList(uid=uid, cid=cid, name=res[0].name, freeze=0)
    session.add(ClubList)
    session.commit()

  tmp = {
    "name": res[0].name,
    "cid": cid,
  }
  return {"result": tmp}

@app.get("/api/club/{cid}", tags=["Member"])
async def club_info(cid: int, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "자신이 부장인 동아리의 정보만 확인할 수 있습니다."}

  with SessionContext() as session:
    club = session.query(dbList).filter_by(cid = cid)

  user_list = []
  for i in club:
    user_list.append([i.uid, i.freeze])

  ret = []
  for i in user_list:
    with SessionContext() as session:
      res = session.query(dbUser).filter_by(uid = i[0])
      user_book = session.query(dbBook).filter_by(uid = i[0]).all()
      user_books_count = 0
      book_list = []
      for e in user_book:
        if e.end > 0:
          user_books_count += 1
        l = e
        l.data = json.loads(l.data)
        book_list.append(l)
    tmp = {
      "uid": res[0].uid,
      "role": res[0].role,
      "name": res[0].name,
      "num": res[0].num,
      "phone": res[0].phone,
      "borrowBook": user_books_count,
      "book": book_list,
      "freeze": i[1]
    }
    ret.append(tmp)
    result = {
      'name': club[0].name,
      'director': uid,
      'cid': cid,
      'members': ret
    }
  return {"result": result}

@app.post("/api/club/{cid}/member", tags=["Member"])
async def invite_member(cid: int, data: InviteMember, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message":"자신이 부장인 동아리의 초대 코드만 생성할 수 있습니다."}

  while True:
    uuid = uuid_gen()
    with SessionContext() as session:
      res = session.query(dbInvite).filter_by(uuid = uuid)
    if not len(list(res)):
      break

  with SessionContext() as session:
    Invite = dbInvite(uuid=uuid, cid=cid, end=data.end * DAY + get_time(), use=data.use)
    session.add(Invite)
    session.commit()

  tmp = {
    "token": uuid,
  }
  return {"result": tmp}

@app.get("/api/club/{cid}/member/{user_id}", tags=["Member"])
async def read_member_info(cid: int, user_id: str, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message":"로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message":"자신이 부장인 동아리의 부원 정보만을 확인할 수 있습니다."}

  with SessionContext() as session:
    club = session.query(dbList).filter_by(uid = user_id).filter_by(cid = cid)
  if not len(list(club)):
    response.status_code = 404
    return {"message":"해당 동아리에 가입된 부원이 아닙니다."}

  with SessionContext() as session:
    res = session.query(dbUser).filter_by(uid = user_id)


  with SessionContext() as session:
    books = session.query(dbBook).filter_by(cid = cid)
    books_info = books.filter_by(uid = user_id)
    borrow_count = books.filter_by(uid = user_id).count()

  books_list = []
  for i in books_info:
    li = i
    li.data = json.loads(i.data)
    books_list.append(li)
  book_club = {}
  for i in books_list:
    if i.cid in book_club:
      continue
    with SessionContext() as session:
      r = session.query(dbClub).filter_by(cid = i.cid)
    club_name = r[0].name
    club_book = []
    with SessionContext() as session:
      r = session.query(dbBook).filter_by(cid = i.cid)
    for i in r:
      li = i
      li.data = json.loads(i.data)
      club_book.append(li)
    book_club[i.cid] = {
      "name": club_name,
      "book": club_book
    }
  tmp = {
    "uid": res[0].uid,
    "role": res[0].role,
    "name": res[0].name,
    "num": res[0].num,
    "phone": res[0].phone,
    "freeze": club[0].freeze,
    "borrowBook": borrow_count,
    "books": book_club[cid] if cid in book_club else {}
  }
  return {"result": tmp}


@app.patch("/api/club/{cid}/member/{user_id}", tags=["Member"])
async def patch_member(cid: int, user_id: str, data: Freeze, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message":"로그인이 필요합니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message":"자신이 부장인 동아리에 소속된 부원만 대여 정지 해제가 가능합니다."}

  freeze = get_time() + data.freeze * DAY if data.freeze else 0

  with SessionContext() as session:
    ClubList = session.query(dbList).filter_by(uid = user_id).filter_by(cid = cid)
    ClubList.update({"freeze": freeze})
    session.commit()
  response.status_code = 200
  return {"result": {'freeze': data.freeze}}

@app.delete("/api/club/{cid}/member/{user_id}", tags=["Member"])
async def delete_member(cid: int, user_id: str, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  if uid == user_id:
    response.status_code = 400
    return {"message": "자기 자신은 추방할 수 없습니다."}

  with SessionContext() as session:
    res = session.query(dbClub).filter_by(director = uid).filter_by(cid = cid)
  if not len(list(res)):
    response.status_code = 400
    return {"message": "자신이 부장인 동아리에서만 부원을 추방할 수 있습니다."}

  with SessionContext() as session:
    ClubList = session.query(dbList).filter_by(uid = user_id).filter_by(cid = cid)
    ClubList.delete()
    session.commit()
  response.status_code = 204
  return {}

@app.post("/auth/refresh", tags=["Authentication"])
async def read_club(response: Response, refresh: str = Depends(oauth2_scheme)):
  uid = rd.get(refresh)

  if not uid:
    response.status_code = 401
    return {"message": "로그인 만료"}

  uid = uid.decode()

  with SessionContext() as session:
    res = session.query(dbUser).filter_by(uid = uid)
  if len(list(res)):
    if res[0].role == "admin":
      auth = sign_admin(res[0].uid)
    else:
      auth = sign_auth(res[0].uid)
    response.status_code = 201
    return {"result": {"auth": auth}}
  else:
    response.status_code = 401
    return {"message": "사용자가 삭제되었습니다."}

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
    
    while True:
      uuid = uuid_gen()
      if not rd.get(uuid):
        break
    rd.set(uuid, str(data.uid))
    
    return {"result": {"auth": auth, "refresh": uuid}}
  else:
    response.status_code = 401
    return {"message": "로그인 실패하였습니다."}

@app.patch("/api/auth", tags=["Authentication"])
async def change_passwd(data: UserPasswd, response: Response, auth: str = Depends(oauth2_scheme)):
  uid = check_auth(auth)
  if not uid:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}

  with SessionContext() as session:
    hash_passwd = hashgen(data.passwd)
    User = session.query(dbUser).filter_by(uid = uid)
    User.update({"passwd": hash_passwd})
    session.commit()
  return {"result": data.passwd}

@app.get("/user/profile", tags=["User"])
async def user_profile(response: Response, auth: str = Depends(oauth2_scheme)):
  userId = check_auth(auth)
  if not userId:
    response.status_code = 401
    return {"message": "로그인이 필요합니다."}
  with SessionContext() as session:
    res = session.query(dbUser).filter_by(uid = userId)
  if not len(list(res)):
    response.status_code = 404
    return {"message": "사용자를 찾을 수 없습니다."}

  with SessionContext() as session:
    tmp = session.query(dbClub).filter_by(director = userId)

  if len(list(tmp)):
    director = tmp[0]
  else:
    director = None

  user = {
    "uid": res[0].uid,
    "role": res[0].role,
    "name": res[0].name,
    "num": res[0].num,
    "phone": res[0].phone,
    "director": director,
  }
  return {"result": user}

@app.get("/api/users", tags=["User"])
async def read_account(response: Response, auth: str = Depends(oauth2_scheme)):
  admin = check_admin(auth)
  if not admin:
    response.status_code = 401
    return {"관리자 전용 기능입니다."}

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
  return {"result": parse_obj_as(List[UserList], ret)}

@app.post("/api/user", tags=["User"])
async def create_account(data: UserSignUp, response: Response, admin: Optional[str] = Header(None)):
  with SessionContext() as session:
    exitsUid = session.query(dbUser).filter_by(uid = data.uid)
    exitsPhone = session.query(dbUser).filter_by(phone = data.phone)
    exitsNum = session.query(dbUser).filter_by(num = data.num)
    # error handling
  if len(list(exitsUid)):
    response.status_code = 400
    return {"message": "이미 있는 아이디입니다."}
  if len(list(exitsPhone)):
    response.status_code = 400
    return {"message": "이미 있는 전화번호입니다."}
  if len(list(exitsNum)):
    response.status_code = 400
    return {"message": "이미 있는 학번입니다."}
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

  if user_role == "admin":
    auth = sign_admin(data.uid)
  else:
    auth = sign_auth(data.uid)

  while True:
      uuid = uuid_gen()
      if not rd.get(uuid):
        break
  rd.set(uuid, str(data.uid))

  return {"result": {"auth": auth, "refresh": uuid}}

@app.put("/api/user/{uid}", tags=["User"])
async def update_account(uid: str, data: UserPasswd, response: Response, auth: str = Depends(oauth2_scheme)):
  admin = check_admin(auth)
  if not admin:
    response.status_code = 401
    return {"message":"관리자 전용 기능입니다."}

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
  return {"result": data.passwd}

@app.delete("/api/user/{uid}", tags=["User"])
async def delete_account(uid: str, response: Response, auth: str = Depends(oauth2_scheme)):
  admin = check_admin(auth)
  if not admin:
    response.status_code = 401
    return {"message": "관리자 전용 기능입니다."}

  with SessionContext() as session:
    User = session.query(dbUser).filter_by(uid = uid)
    User.delete()
    session.commit()
  response.status_code = 204
  return {}

@app.post("/token")
async def token(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
  with SessionContext() as session:
    hash_passwd = hashgen(form_data.password)
    res = session.query(dbUser).filter_by(uid = form_data.username, passwd = hash_passwd)
  if len(list(res)):
    if res[0].role == "admin":
      auth = sign_admin(res[0].uid)
    else:
      auth = sign_auth(res[0].uid)
    return {"access_token": auth, "token_type": "bearer"}

  else:
    return HTTPException(status_code=400, detail="Incorrect username or password")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")
