from pydantic import BaseModel, Field


class PythonCode(BaseModel):
  '''Python code that can be saved and executed as a standalone script.'''

  overview: str = Field(description='Overview of the procedures to be performed.')
  code: str = Field(description='Python code to be saved as a standalone script.')


class CodeResult(BaseModel):
  '''Execution result of the Python script.'''

  status: str = Field(description='Status of the Python script execution.')
  stdout: str = Field(description='Stdout of the Python script.')
  stderr: str = Field(description='Stderr of the Python script.')


class ObjectHandle(BaseModel):
  '''Unique identifier for any type of object, such as files.'''

  handle: str = Field(description='Unique object identifier.')
