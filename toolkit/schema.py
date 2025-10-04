from pydantic import BaseModel, Field


class CodeResult(BaseModel):
  '''Execution result of the Python script.'''

  status: str = Field(description='Status of the Python script execution.')
  stdout: str = Field(description='Stdout of the Python script.')
  stderr: str = Field(description='Stderr of the Python script.')
