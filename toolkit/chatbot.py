from langchain_core.prompts import (
  ChatPromptTemplate, MessagesPlaceholder,
  HumanMessagePromptTemplate,
  SystemMessagePromptTemplate,
)
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.agents import AgentStep
from langchain_core.messages import BaseMessage, AIMessageChunk, ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.runnables.config import RunnableConfig
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_openai.chat_models import ChatOpenAI
from typing import Any, Dict, Iterator, List, Optional

from toolkit.prompt import (
  CHATBOT_SYSTEM_PROMPT_TEMPLATE,
  DEFAULT_TOOL_GUIDELINES,
  DEFAULT_GUIDELINES,
  CONVERSATION_OPENINGS,
)
from toolkit.tools import get_tools

import json
import random


class AgentExecutorAdapter(Runnable):
  def __init__(self, agent_executor: AgentExecutor):
    self.agent_executor = agent_executor
    self.agent_executor.return_intermediate_steps = True

  def invoke(
    self,
    input: Dict[str, Any],
    config: Optional[RunnableConfig] = None,
    **kwargs: Any,
  ) -> List[BaseMessage]:

    result = self.agent_executor.invoke(input, config, **kwargs)
    messages = format_to_tool_messages(result['intermediate_steps'])
    messages.append(AIMessageChunk(content=result['output']))

    return messages

  def stream(
    self,
    input: Dict[str, Any],
    config: Optional[RunnableConfig] = None,
    **kwargs: Any,
  ) -> Iterator[BaseMessage]:

    _format_observation = lambda x: x if isinstance(x, str) else json.dumps(x)

    for addable_dict in self.agent_executor.stream(input, config, **kwargs):
      if 'actions' in addable_dict:
        agent_action: ToolAgentAction = addable_dict['actions'][0]
        ai_message_chunk: AIMessageChunk = agent_action.message_log[0]
        yield ai_message_chunk

      elif 'steps' in addable_dict:
        agent_step: AgentStep = addable_dict['steps'][0]
        tool_message = ToolMessage(
          content=_format_observation(agent_step.observation),
          tool_call_id=agent_step.action.tool_call_id,
        )
        yield tool_message

      elif 'output' in addable_dict:
        yield AIMessageChunk(content=addable_dict['output'])


def create_prompt(tool_guidelines: str, guidelines: str):
  system_prompt = SystemMessagePromptTemplate.from_template(
    CHATBOT_SYSTEM_PROMPT_TEMPLATE.format(
      tool_guidelines=tool_guidelines,
      guidelines=guidelines,
    ),
  )
  chat_history = MessagesPlaceholder(variable_name='history')
  human_prompt = HumanMessagePromptTemplate.from_template('{message}')
  scratch_pad = MessagesPlaceholder(variable_name='agent_scratchpad')

  messages = [system_prompt, chat_history, human_prompt, scratch_pad]

  return ChatPromptTemplate.from_messages(messages)


def init_chat_session(session_id: str, message_db: str):
  session_history = SQLChatMessageHistory(session_id, connection=f'sqlite:///{message_db}')
  session_history.add_ai_message(random.choice(CONVERSATION_OPENINGS))


def create_chatbot(model_name: str, message_db: str, **kwargs):
  model = ChatOpenAI(model=model_name, **kwargs)

  prompt = create_prompt(
    tool_guidelines=DEFAULT_TOOL_GUIDELINES.strip(),
    guidelines=DEFAULT_GUIDELINES.strip(),
  )
  agent = create_tool_calling_agent(model, get_tools(), prompt)
  agent_executor = AgentExecutor(agent=agent, tools=get_tools())

  chatbot = RunnableWithMessageHistory(
    runnable=AgentExecutorAdapter(agent_executor),
    get_session_history=lambda session_id: (
      SQLChatMessageHistory(session_id, connection=f'sqlite:///{message_db}')
    ),
    input_messages_key='message',
    history_messages_key='history',
  )

  return chatbot
