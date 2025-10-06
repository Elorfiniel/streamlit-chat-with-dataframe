from typing import Dict, List

import io
import os
import tempfile


HIDDEN_FOLDER = '.hidden'


class FileContext:
  _instance = None

  def __new__(cls, cache_root: str, folder: str):
    if cls._instance is None:
      cls._instance = super(FileContext, cls).__new__(cls)

    cls._instance.set_context(cache_root, folder)

    return cls._instance

  def set_context(self, cache_root: str, folder: str):
    self.context = dict(
      cache_root=cache_root, folder=folder,
    )

  def cwd(self) -> Dict[str, str]:
    return os.path.join(self.context['cache_root'], self.context['folder'])

  @classmethod
  def get_instance(cls, *, cache_root: str = None, folder: str = None):
    if cache_root and folder:
      return cls(cache_root, folder)
    return cls._instance


def create_cache_folder(cache_root: str, **kwargs):
  cache_root = os.path.abspath(cache_root)
  if not os.path.exists(cache_root):
    os.makedirs(cache_root, exist_ok=True)

  folder = tempfile.mkdtemp(dir=cache_root, **kwargs)
  relpath = os.path.relpath(folder, cache_root)

  hidden = os.path.join(cache_root, relpath, HIDDEN_FOLDER)
  os.makedirs(hidden, exist_ok=True)

  return relpath


def save_uploaded_files(cache_root: str, folder: str, files: List[io.BytesIO]):
  file_status = {}

  for file in files:
    upload_path = os.path.join(cache_root, folder, file.name)

    try:
      with open(upload_path, 'wb') as fp:
        fp.write(file.getvalue())
    except Exception as ex:
      status = (False, type(ex).__name__, str(ex))
    else:
      status = (True, )

    file_status[file.name] = status

  return file_status


def list_files(cache_root: str, folder: str):
  return [
    filename
    for filename in os.listdir(os.path.join(cache_root, folder))
    if os.path.isfile(os.path.join(cache_root, folder, filename))
  ]
