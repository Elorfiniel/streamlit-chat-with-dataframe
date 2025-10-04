from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, BaseTool, InjectedToolArg
from langchain_openai.chat_models import ChatOpenAI
from typing import Annotated, Dict, Generator, List, Optional, Tuple

from toolkit.prompt import CODE_GENERATION_PROMPT_TEMPLATE
from toolkit.schema import PythonCode, ObjectHandle, CodeResult

import json
import os
import subprocess
import sys
import tempfile


@tool(parse_docstring=True)
def code_generation(desc: str, cwd: Annotated[str, InjectedToolArg]) -> Tuple[PythonCode, ObjectHandle]:
  '''Generate Python code to perform data analysis task based on the description.

  Allowed modules: `pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `sklearn`.

  Args:
    desc: The description of the data anaylsis code.
    cwd: The working directory for code generation.
  '''

  prompt = ChatPromptTemplate.from_template(
    CODE_GENERATION_PROMPT_TEMPLATE
  ).partial(allowed_modules='pandas, numpy, matplotlib, seaborn, scipy, sklearn')

  model = ChatOpenAI(
    model='gpt-4o-mini', temperature=0.2, top_p=0.9,
  ).with_structured_output(PythonCode)

  code: PythonCode = (prompt | model).invoke({'desc': desc})

  fp, path = tempfile.mkstemp(suffix='.py', dir=cwd, text=True)
  with os.fdopen(fp, 'w', encoding='utf-8') as file:
    file.write(code.code)
  handle = ObjectHandle(handle=os.path.relpath(path, cwd))

  return (code, handle)


@tool(parse_docstring=True)
def code_execution(path: str, cwd: Annotated[str, InjectedToolArg]) -> CodeResult:
  '''Execute Python script file, return execution result.

  Args:
    path: The path of the Python code to execute.
    cwd: The working directory for code execution.
  '''

  actual_cwd = os.getcwd()
  os.chdir(cwd)

  try:
    proc = subprocess.run([sys.executable, path], capture_output=True, text=True, check=True)
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

  os.chdir(actual_cwd)

  return result


TOOL_LIST = [code_generation, code_execution]
INJECTED_TOOL_ARGS = {
  code_generation.name: ['cwd'],
  code_execution.name: ['cwd'],
}
TOOL_OUTPUT_PARSERS = {
  code_generation.name: lambda x: dict(
    overview=x[0].overview,
    code=x[0].code,
    path=x[1].handle,
  ),
  code_execution.name: lambda x: dict(
    **x.model_dump(),
  ),
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
      parser = TOOL_OUTPUT_PARSERS.get(tool_name)
      content = parser(tool_output)
    except Exception as exception:
      parser = TOOL_OUTPUT_PARSERS.get('__exec_exception__')
      content = parser(exception)

    yield ToolMessage(
      tool_call_id=tool_call['id'],
      name=tool_name,
      content=json.dumps(content),
    )
