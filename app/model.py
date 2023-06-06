import os

from app.config import *

from sqlalchemy import *
from sqlalchemy.orm import *

Base = declarative_base()
engine = create_engine(DSN, echo = True)

class dbUser(Base):
  __tablename__ = "users"

  uid = Column(String, primary_key=True)
  passwd = Column(String, nullable=False)
  role = Column(String, nullable=False)
  name = Column(String, nullable=False)
  num = Column(String, nullable=False)
  phone = Column(String, nullable=False)

class dbClub(Base):
  __tablename__ = "clubs"

  cid = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  director = Column(String, ForeignKey("users.uid"))

class dbList(Base):
  __tablename__ = "lists"

  lid = Column(Integer, primary_key=True)
  uid = Column(String, ForeignKey("users.uid"))
  cid = Column(Integer, ForeignKey("clubs.cid"))

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

class SessionContext:
  session = None

  def __enter__(self):
    self.session = Session()
    return self.session

  def __exit__(self, exc_type, exc_value, traceback):
    self.session.close()
