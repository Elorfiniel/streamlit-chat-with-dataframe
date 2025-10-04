from langchain_core.messages import (
  BaseMessage, BaseMessageChunk,
  SystemMessage, SystemMessageChunk,
  HumanMessage, HumanMessageChunk,
  AIMessage, AIMessageChunk,
  ToolMessage, ToolMessageChunk,
  ChatMessage, ChatMessageChunk,
)
from typing import Dict, List, Iterator, Union

from toolkit.tools import code_execution

import json
import streamlit as st


def message_avatar(mtype: str):
  assert mtype in ['system', 'human', 'ai', 'tool', 'role', 'unknown']
  return {
    'system': ':material/settings:',
    'human': ':material/person:',
    'ai': ':material/robot_2:',
    'tool': ':material/function:',
    'role': ':material/conversation:',
    'unknown': ':material/question_mark:',
  }[mtype]


def message_type(message: Union[str, BaseMessage, BaseMessageChunk], avatar: bool = False):
  if isinstance(message, (SystemMessage, SystemMessageChunk)):
    mtype = 'system'
  elif isinstance(message, (HumanMessage, HumanMessageChunk)):
    mtype = 'human'
  elif isinstance(message, (AIMessage, AIMessageChunk)):
    mtype = 'ai'
  elif isinstance(message, (ToolMessage, ToolMessageChunk)):
    mtype = 'tool'
  elif isinstance(message, (ChatMessage, ChatMessageChunk)):
    mtype = 'role'
  else:
    mtype = 'unknown'
  return (mtype, message_avatar(mtype)) if avatar else mtype


def render_tool_calls(tool_calls: List[Dict]):
  for tool_call in tool_calls:
    with st.expander('Tool Call ID: ' + tool_call['id'], expanded=True):
      call = dict(name=tool_call['name'], args=tool_call['args'])
      st.markdown(f'```json\n{json.dumps(call, indent=2)}\n```')


def render_tool_message(message: ToolMessage):
  with st.expander('Tool Call ID: ' + message.tool_call_id, expanded=True):
    content = json.loads(message.content)

    if 'ex_type' in content:
      st.error(f'{content["ex_type"]}: {content["message"]}')

    elif message.name == code_execution.name:
      if content['status'].startswith('Failure'):
        st.error(content['status'])
        st.markdown(f'```plain\n{content["stderr"]}\n```')
      else:
        st.markdown(f'```plain\n{content["stdout"]}\n```')

    else:
      st.markdown(f'```json\n{json.dumps(content, indent=2)}\n```')


def render_message(message: BaseMessage):
  mtype, avatar = message_type(message, avatar=True)
  with st.chat_message(mtype, avatar=avatar):
    if isinstance(message, AIMessage) and message.tool_calls:
      render_tool_calls(message.tool_calls)
    elif isinstance(message, ToolMessage):
      render_tool_message(message)
    else:
      st.markdown(message.content)


def render_human_prompt(prompt: str):
  with st.chat_message('human', avatar=message_avatar('human')):
    st.markdown(prompt)


def render_ai_response(stream: Iterator):
  ai_message_chunk = AIMessageChunk(content='')

  def custom_stream(stream: Iterator):
    nonlocal ai_message_chunk
    for chunk in stream:
      ai_message_chunk = ai_message_chunk + chunk
      if chunk.content: yield chunk

  with st.chat_message('ai', avatar=message_avatar('ai')):
    st.write_stream(custom_stream(stream))
    if not ai_message_chunk.content:
      render_tool_calls(ai_message_chunk.tool_calls)

  return ai_message_chunk
