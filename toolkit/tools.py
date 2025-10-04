from langchain_core.messages import ToolMessage
from langchain_core.tools import tool, BaseTool, InjectedToolArg
from typing import Annotated, Dict, Generator, List, Optional

from toolkit.fileio import HIDDEN_FOLDER
from toolkit.schema import CodeResult

import json
import os
import subprocess
import sys


@tool(parse_docstring=True)
def save_generation(text: str, filename: str, code: bool,
                    cwd: Annotated[str, InjectedToolArg]) -> Dict[str, str]:
  '''Save the generated text content, ie. code snippets, to the specified file.

  Note: code snippets are saved inside a special folder (hidden from the user).

  Args:
    text: The generated text content, ie. text, code, etc.
    filename: The filename (relative path).
    code: Whether the generated text content is code, ie. Python scripts.
    cwd: The working directory for tool execution.
  '''

  prefix = [cwd, HIDDEN_FOLDER] if code else [cwd]
  filepath = os.path.join(*prefix, filename)

  folder = os.path.dirname(filepath)
  os.makedirs(folder, exist_ok=True)

  with open(filepath, 'w', encoding='utf-8') as file:
    file.write(text)

  return dict(filename=filename, location='code' if code else 'text')


@tool(parse_docstring=True)
def code_execution(path: str, cwd: Annotated[str, InjectedToolArg]) -> CodeResult:
  '''Execute Python script file, return execution result.

  Args:
    path: The path of the Python code to execute.
    cwd: The working directory for tool execution.
  '''

  parent_proc_cwd = os.getcwd()
  os.chdir(cwd)

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

  return result


TOOL_LIST = [save_generation, code_execution]
INJECTED_TOOL_ARGS = {
  save_generation.name: ['cwd'],
  code_execution.name: ['cwd'],
}
TOOL_OUTPUT_PARSERS = {
  code_execution.name: lambda x: x.model_dump(),
  '__exec_exception__': lambda x: dict(
    ex_type=type(x).__name__, message=str(x),
  ),
}


def get_tools(names: Optional[List[str]] = None) -> List[BaseTool]:
  filter_fn = lambda t: not names or t.name in names
  return list(filter(filter_fn, TOOL_LIST))


def invoke_tools(tool_calls: List[Dict], injected_args: Dict) -> Generator[ToolMessage, None, None]:
  def _with_injected_args(tool_name: str):
    args = INJECTED_TOOL_ARGS.get(tool_name, [])
    return {k: injected_args[k] for k in args}

  for tool_call in tool_calls:
    tool_name, tool_args = tool_call['name'], tool_call['args']
    args = {**tool_args, **_with_injected_args(tool_name)}

    try:
      tool = get_tools([tool_name])[0]
      tool_output = tool.invoke(args)
      parser = TOOL_OUTPUT_PARSERS.get(tool_name, lambda x: x)
      content = parser(tool_output)
    except Exception as exception:
      parser = TOOL_OUTPUT_PARSERS.get('__exec_exception__')
      content = parser(exception)

    yield ToolMessage(
      tool_call_id=tool_call['id'],
      name=tool_name,
      content=json.dumps(content),
    )
