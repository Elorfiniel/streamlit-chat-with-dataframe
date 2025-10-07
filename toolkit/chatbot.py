from langchain_core.prompts import (
  ChatPromptTemplate, MessagesPlaceholder,
  HumanMessagePromptTemplate,
  SystemMessagePromptTemplate,
)
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.agents import AgentStep
# from langchain_core.callbacks import CallbackManager
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

    # [Experimental] Capture callbacks from RunnableWithMessageHistory
    #
    # Capture the callbacks, invoke the agent executor, format the output,
    # then manually emit the `on_chain_end` event. The ultimate effect is
    # I'll have the formatted output saved to the chat history.
    #
    # I know this looks like some nasty workaround... However, if I forward
    # the callbacks to the agent executor, it will eventually generate an
    # event that gets propagated to the RunnableWithMessageHistory.
    # Once the RunnableWithMessageHistory receives the `on_chain_end` event,
    # it will save the output of AgentExecutor to the chat history.
    #
    # Hope someone out there has a better solution.
    # callback_manager = CallbackManager.configure(
    #   inheritable_callbacks=config.pop('callbacks', None),
    # )
    # run_manager = callback_manager.on_chain_start(
    #   None, input, run_id=None, name=self.get_name(),
    # )

    result = self.agent_executor.invoke(input, config, **kwargs)
    messages = format_to_tool_messages(result['intermediate_steps'])
    messages.append(AIMessageChunk(content=result['output']))

    # run_manager.on_chain_end(messages)

    return messages

  def stream(
    self,
    input: Dict[str, Any],
    config: Optional[RunnableConfig] = None,
    **kwargs: Any,
  ) -> Iterator[BaseMessage]:

    _format_observation = lambda x: x if isinstance(x, str) else json.dumps(x)

    # [Experimental] Capture callbacks from RunnableWithMessageHistory
    # callback_manager = CallbackManager.configure(
    #   inheritable_callbacks=config.pop('callbacks', None),
    # )
    # run_manager = callback_manager.on_chain_start(
    #   None, input, run_id=None, name=self.get_name(),
    # )

    # messages: List[BaseMessage] = []

    for addable_dict in self.agent_executor.stream(input, config, **kwargs):
      message = None

      if 'actions' in addable_dict:
        agent_action: ToolAgentAction = addable_dict['actions'][0]
        message: AIMessageChunk = agent_action.message_log[0]

      elif 'steps' in addable_dict:
        agent_step: AgentStep = addable_dict['steps'][0]
        message = ToolMessage(
          content=_format_observation(agent_step.observation),
          tool_call_id=agent_step.action.tool_call_id,
          additional_kwargs=dict(name=agent_step.action.tool),
        )

      elif 'output' in addable_dict:
        message = AIMessageChunk(content=addable_dict['output'])

      if message is not None:
        # messages.append(message)
        yield message

    # run_manager.on_chain_end(messages)


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
