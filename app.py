import streamlit as st


def main():
  st.title("Chat with DataFrame")
  st.markdown("""
  Welcome to the **Chat with DataFrame** application!

  This is a Streamlit application that allows you to interact with `pandas` DataFrames through natural language queries.
  The app leverages large language models (LLMs) to interpret your questions and generate appropriate `pandas` code to
  manipulate and analyze your data.

  ## Key Features
  - Upload your own tabular data.
  - Ask questions about the data.
  - Get insights from the feedback.

  This makes data analysis more accessible and intuitive for everyone!
  """)


if __name__ == "__main__":
  main()
