from langchain_core.messages import (
  BaseMessage, BaseMessageChunk,
  SystemMessage, SystemMessageChunk,
  HumanMessage, HumanMessageChunk,
  AIMessage, AIMessageChunk,
  ToolMessage, ToolCallChunk,
  ChatMessage, ChatMessageChunk,
)
from typing import Union


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
  elif isinstance(message, (ToolMessage, ToolCallChunk)):
    mtype = 'tool'
  elif isinstance(message, (ChatMessage, ChatMessageChunk)):
    mtype = 'role'
  else:
    mtype = 'unknown'
  return (mtype, message_avatar(mtype)) if avatar else mtype
