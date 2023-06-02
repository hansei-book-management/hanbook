import os

from app.config import *

from sqlalchemy import *
from sqlalchemy.orm import *

Base = declarative_base()
engine = create_engine(DSN, echo = True)

class dbUser(Base):
  __tablename__ = "users"

  name = Column(String, primary_key=True)
  passwd = Column(String, nullable=False)
  role = Column(String, nullable=False)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

class SessionContext:
  session = None

  def __enter__(self):
    self.session = Session()
    return self.session

  def __exit__(self, exc_type, exc_value, traceback):
    self.session.close()
