from toolkit.database import (
  connect_session, search_active_chats,
  create_chat_history, ChatHistory,
  update_chat_name, update_chat_status,
)
from toolkit.fileio import create_cache_folder
from toolkit.chatbot import create_chatbot, init_chat_session
from toolkit.ui import message_type, message_avatar

import dotenv
import os
import streamlit as st
import uuid


# Environment Variables
dotenv.load_dotenv()


# Streamlit State Session
if 'session_db' not in st.session_state:
  st.session_state.session_db = connect_session(db_path=os.getenv('SESSION_DB'))
if 'restore_id' not in st.session_state:
  st.session_state.restore_id = ''
if 'chatbot' not in st.session_state:
  st.session_state.chatbot = create_chatbot('gpt-4o-mini', message_db=os.getenv('MESSAGE_DB'))


# Streamlit Callbacks to handle user interactions
def create_chat_cb(chat_name: str):
  st.session_state.restore_id = str(uuid.uuid4())
  chat_history = ChatHistory(
    folder=create_cache_folder(cache_root=os.getenv('CACHE_ROOT'), prefix='chat-'),
    id=st.session_state.restore_id,
  )
  if chat_name:
    chat_history.name = chat_name

  create_chat_history(st.session_state.session_db, chat_history=chat_history)
  init_chat_session(
    session_id=st.session_state.restore_id,
    message_db=os.getenv('MESSAGE_DB'),
  )

def rename_chat_cb(chat_name: str, chat_id: str):
  st.session_state.restore_id = chat_id
  if chat_name:
    update_chat_name(
      st.session_state.session_db,
      chat_id=chat_id, name=chat_name,
    )

def delete_chat_cb(chat_id: str):
  st.session_state.restore_id = ''
  update_chat_status(
    st.session_state.session_db,
    chat_id=chat_id, status='delete',
  )


# Streamlit Sidebar
with st.sidebar:
  st.title('Chat with DataFrame')

  # Select from a list of active chat sessions
  chat_history_list = search_active_chats(st.session_state.session_db)
  if chat_history_list:
    chat_history = st.selectbox(
      label='Active Chat Sessions',
      options=chat_history_list,
      format_func=lambda x: x.name,
      index={
        chat_history.id: idx for idx, chat_history in enumerate(chat_history_list)
      }.get(st.session_state.restore_id, None),
      placeholder='Select Chat Session',
    )
    session_id = chat_history.id if chat_history else ''

  else:
    session_id = ''

  more_actions = st.segmented_control(
    label='More Chat Actions',
    options=['Create', 'Rename', 'Delete'],
    default='Create', width='stretch',
  )

  if more_actions == 'Create':
    chat_name = st.text_input(label='Name Chat Session', max_chars=255)
    st.button(
      label='Submit', type='primary', width='stretch',
      on_click=create_chat_cb, args=(chat_name, ),
    )

  if more_actions == 'Rename':
    if session_id:
      chat_name = st.text_input(label='Custom Chat Name', max_chars=255)
      st.button(
        label='Submit', type='primary', width='stretch',
        on_click=rename_chat_cb,
        args=(chat_name, session_id),
      )
    else:
      st.info('Select a chat session to rename.', icon=':material/info:')

  if more_actions == 'Delete':
    if session_id:
      st.button(
        label='Delete', type='primary', width='stretch',
        on_click=delete_chat_cb, args=(session_id, ),
      )
    else:
      st.info('Select a chat session to delete.', icon=':material/info:')


# Streamlit Main Content
if session_id:
  session_history = st.session_state.chatbot.get_session_history(session_id)
  for message in session_history.get_messages():
    mtype, avatar = message_type(message, avatar=True)
    with st.chat_message(mtype, avatar=avatar):
      st.markdown(message.content)

  if prompt := st.chat_input('Chat with Me!'):
    with st.chat_message('human', avatar=message_avatar('human')):
      st.markdown(prompt)

    stream = st.session_state.chatbot.stream(
      {'message': prompt},
      config={'configurable': {'session_id': session_id}},
    )
    with st.chat_message('ai', avatar=message_avatar('ai')):
      st.write_stream(stream)

else:
  st.header('Welcome!', divider='red')

  st.markdown('''
  This Streamlit APP allows you to interact with `pandas` DataFrames through natural language
  queries. The APP leverages LLMs to interpret your questions and generate appropriate code
  to manipulate and analyze your data. Please have fun **experimenting with your data**!
  ''')

  st.header('Quickstart', divider='red')

  st.markdown('''
  1. Create a new chat session, or select from an existing one.
  2. Upload your data for analysis, if not already uploaded.
  3. Ask questions about your data using natural language.
  4. The agentic APP will make mistakes, so please be skeptical.
  ''')
