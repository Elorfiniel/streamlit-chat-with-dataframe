from typing import List

import io
import os
import tempfile


HIDDEN_FOLDER = '.hidden'


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
