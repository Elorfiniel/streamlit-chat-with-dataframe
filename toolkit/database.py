from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

import os
import uuid


Base = declarative_base()

uuid_fn = lambda: str(uuid.uuid4())
time_fn = lambda: datetime.now(timezone.utc)
name_fn = lambda: f'Chat {time_fn().strftime("%Y-%m-%d %H:%M:%S")}'


class ChatHistory(Base):
  __tablename__ = 'chat_history'

  id = Column(String(36), primary_key=True, default=uuid_fn)

  name = Column(String(255), default=name_fn)

  created = Column(DateTime, default=time_fn, nullable=False)
  updated = Column(DateTime, default=time_fn, onupdate=time_fn, nullable=False)

  folder = Column(String(512))
  status = Column(String(20), default='active')


def connect_session(db_path: str):
  db_path = os.path.abspath(db_path)

  db_root = os.path.dirname(db_path)
  if db_root and not os.path.exists(db_root):
    os.makedirs(db_root, exist_ok=True)

  engine = create_engine(f'sqlite:///{db_path}', echo=False)
  Base.metadata.create_all(engine, checkfirst=True)

  Session = sessionmaker(bind=engine)

  return Session()


def search_active_chats(session):
  return session.query(ChatHistory).filter(
    ChatHistory.status == 'active'
  ).all()


def search_chat_history(session, chat_id: str):
  return session.query(ChatHistory).filter(
    ChatHistory.id == chat_id
  ).first()


def create_chat_history(session, chat_history: ChatHistory):
  session.add(chat_history)
  session.commit()


def update_chat_name(session, chat_id: str, name: str):
  chat_history = search_chat_history(session, chat_id)

  if chat_history:
    chat_history.name = name
    session.commit()
    return True

  return False


def update_chat_status(session, chat_id: str, status: str):
  chat_history = search_chat_history(session, chat_id)

  if chat_history:
    chat_history.status = status
    session.commit()
    return True

  return False
