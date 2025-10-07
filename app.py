from streamlit_file_browser import st_file_browser
from typing import Optional

from toolkit.database import (
  connect_session, search_active_chats,
  create_chat_history, ChatHistory,
  update_chat_name, update_chat_status,
)
from toolkit.fileio import FileContext, create_cache_folder, save_uploaded_files
from toolkit.chatbot import create_chatbot, init_chat_session
from toolkit.ui import render_human_prompt, render_message

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
if 'chat_model' not in st.session_state:
  st.session_state.chatbot = create_chatbot('gpt-4o-mini', os.getenv('MESSAGE_DB'))
if 'browse_file' not in st.session_state:
  st.session_state.browse_file = False


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

def browse_file_cb():
  st.session_state.browse_file = not st.session_state.browse_file

def dismiss_file_cb():
  st.session_state.browse_file = False


# Helper functions
def format_user_message(user_inputs: dict):
  user_message = user_inputs['text']
  if user_inputs['files']:
    file_entries = []
    for file in user_inputs['files']:
      status = user_inputs['status'][file.name]
      if status[0]:
        entry = f'- {file.name}: {file.type}, success.'
      else:
        failure_details = f'failure ({status[1]}, {status[2]})'
        entry = f'- {file.name}: {file.type}, {failure_details}.'
      file_entries.append(entry)

    files = '\n\n'.join(['**Uploaded Files**', '\n'.join(file_entries)])
    user_message = '\n\n'.join([user_message, files])

  return user_message


# Streamlit Sidebar
def streamlit_welcome():
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

@st.dialog('Browse Files', width='medium', on_dismiss=dismiss_file_cb)
def streamlit_file_browser(cache_root: str, folder: str):
  st_file_browser(path= os.path.join(cache_root, folder))

def streamlit_sidebar():
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
      session_id, chat_history = '', None

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

    if session_id and st.button('Browse Files', width='stretch', on_click=browse_file_cb):
      if st.session_state.browse_file:
        streamlit_file_browser(cache_root=os.getenv('CACHE_ROOT'), folder=chat_history.folder)

  return session_id, chat_history

def streamlit_content(session_id: str, chat_history: Optional[ChatHistory]):
  FileContext.get_instance(cache_root=os.getenv('CACHE_ROOT'), folder=chat_history.folder)

  session_history = st.session_state.chatbot.get_session_history(session_id)
  for message in session_history.get_messages():
    render_message(message)

  file_kwargs = dict(accept_file=True, file_type=['csv', 'txt', 'xlsx'])
  if user_inputs := st.chat_input('Chat with Me!', **file_kwargs):
    if user_inputs['files']:
      with st.spinner('Caching uploaded files...', show_time=True, width='stretch'):
        file_status = save_uploaded_files(
          cache_root=os.getenv('CACHE_ROOT'),
          folder=chat_history.folder, files=user_inputs['files'],
        )
      user_inputs['status'] = file_status

    user_message = format_user_message(user_inputs)
    render_human_prompt(user_message)

    stream = st.session_state.chatbot.stream(
      {'message': user_message},
      config={'configurable': {'session_id': session_id}},
    )
    for message in stream:
      render_message(message)


# Streamlit App
session_id, chat_history = streamlit_sidebar()
if session_id:
  streamlit_content(session_id, chat_history)
else:
  streamlit_welcome()
