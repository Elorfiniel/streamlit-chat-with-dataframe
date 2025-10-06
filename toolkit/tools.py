from langchain_core.tools import tool, BaseTool
from typing import Dict, List, Optional

from toolkit.fileio import HIDDEN_FOLDER, FileContext
from toolkit.schema import CodeResult

import os
import subprocess
import sys


def _working_directory() -> str:
  context = FileContext.get_instance()
  if context is None:
    raise RuntimeError('Uninitialized file context')
  return context.cwd()


@tool(parse_docstring=True)
def save_generation(text: str, filename: str, code: bool) -> Dict[str, str]:
  '''Save the generated text content, ie. code snippets, to the specified file.

  Note: code snippets are saved inside a special folder (hidden from the user).

  Args:
    text: The generated text content, ie. text, code, etc.
    filename: The filename (relative path).
    code: Whether the generated text content is code, ie. Python scripts.
  '''

  prefix = [_working_directory(), HIDDEN_FOLDER]
  if not code: prefix.pop()
  filepath = os.path.join(*prefix, filename)

  folder = os.path.dirname(filepath)
  os.makedirs(folder, exist_ok=True)

  with open(filepath, 'w', encoding='utf-8') as file:
    file.write(text)

  return dict(filename=filename, type='code' if code else 'text')


@tool(parse_docstring=True)
def code_execution(path: str) -> CodeResult:
  '''Execute Python script file, return execution result.

  Args:
    path: The path of the Python code to execute.
  '''

  parent_proc_cwd = os.getcwd()
  os.chdir(_working_directory())

  script_relpath = os.path.join(HIDDEN_FOLDER, path)

  try:
    proc = subprocess.run(
      [sys.executable, script_relpath],
      capture_output=True, text=True, check=True,
    )
    stdout = proc.stdout if proc.stdout else ''
    stderr = proc.stderr if proc.stderr else ''
    result = CodeResult(status='Success', stdout=stdout, stderr=stderr)
  except subprocess.CalledProcessError as ex:
    result = CodeResult(
      status=f'Failure, with exit code {ex.returncode}',
      stdout=ex.stdout if ex.stdout else '',
      stderr=ex.stderr if ex.stderr else '',
    )
  except Exception as ex:
    result = CodeResult(
      status=f'Failure, with exception {ex}',
      stdout='', stderr='',
    )

  os.chdir(parent_proc_cwd)

  return result.model_dump()


TOOL_LIST = [save_generation, code_execution]


def get_tools(names: Optional[List[str]] = None) -> List[BaseTool]:
  filter_fn = lambda t: not names or t.name in names
  return list(filter(filter_fn, TOOL_LIST))
