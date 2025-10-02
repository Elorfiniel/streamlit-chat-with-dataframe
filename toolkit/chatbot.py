from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import AIMessage
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_openai.chat_models import ChatOpenAI


# Prompt Templates
prompt = ChatPromptTemplate.from_messages([
  ('system', 'You are a helpful assistant.'),
  MessagesPlaceholder(variable_name='history'),
  ('human', '{message}'),
])


def init_chat_session(session_id: str, message_db: str):
  session_history = SQLChatMessageHistory(session_id, connection=f'sqlite:///{message_db}')
  ai_message = AIMessage(content='How can I help you today? Please ask me anything.')
  session_history.add_ai_message(ai_message)


# Chatbot
def create_chatbot(model: str, message_db: str, **kwargs):
  llm = ChatOpenAI(model=model, **kwargs)

  chatbot = RunnableWithMessageHistory(
    runnable=prompt | llm,
    get_session_history=lambda session_id: (
      SQLChatMessageHistory(session_id, connection=f'sqlite:///{message_db}')
    ),
    input_messages_key='message',
    history_messages_key='history',
  )

  return chatbot
