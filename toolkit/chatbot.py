from langchain_core.prompts import (
  ChatPromptTemplate, MessagesPlaceholder,
  HumanMessagePromptTemplate,
  SystemMessagePromptTemplate,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_openai.chat_models import ChatOpenAI
from typing import Dict, List

from toolkit.prompt import (
  CHATBOT_SYSTEM_PROMPT_TEMPLATE,
  DEFAULT_TOOL_GUIDELINES,
  DEFAULT_GUIDELINES,
  CONVERSATION_OPENINGS,
)
from toolkit.tools import get_tools, invoke_tools

import os
import random


def create_prompt(tool_guidelines: str, guidelines: str, no_human: bool = False):
  system_prompt = SystemMessagePromptTemplate.from_template(
    CHATBOT_SYSTEM_PROMPT_TEMPLATE.format(
      tool_guidelines=tool_guidelines,
      guidelines=guidelines,
    ),
  )
  chat_history = MessagesPlaceholder(variable_name='history')
  human_prompt = HumanMessagePromptTemplate.from_template('{message}')

  messages = [system_prompt, chat_history]
  if not no_human:
    messages.append(human_prompt)

  return ChatPromptTemplate.from_messages(messages)


def init_chat_session(session_id: str, message_db: str):
  session_history = SQLChatMessageHistory(session_id, connection=f'sqlite:///{message_db}')
  session_history.add_ai_message(random.choice(CONVERSATION_OPENINGS))


def create_chat_model(model_name: str, **kwargs) -> BaseChatModel:
  return ChatOpenAI(model=model_name, **kwargs)


def create_chatbot(model: BaseChatModel, message_db: str):
  prompt = create_prompt(
    tool_guidelines=DEFAULT_TOOL_GUIDELINES.strip(),
    guidelines=DEFAULT_GUIDELINES.strip(),
  )
  model_with_tools = model.bind_tools(get_tools())

  chatbot = RunnableWithMessageHistory(
    runnable=prompt | model_with_tools,
    get_session_history=lambda session_id: (
      SQLChatMessageHistory(session_id, connection=f'sqlite:///{message_db}')
    ),
    input_messages_key='message',
    history_messages_key='history',
  )

  return chatbot


def invoke_chatbot_tools(session_history: SQLChatMessageHistory,
                         tool_calls: List[Dict],
                         cache_root: str, folder: str):
  injected_args = dict(cwd=os.path.join(cache_root, folder))
  for tool_message in invoke_tools(tool_calls, injected_args):
    session_history.add_message(tool_message)
    yield tool_message
