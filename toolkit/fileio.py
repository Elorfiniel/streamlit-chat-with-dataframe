import os
import tempfile


def create_cache_folder(cache_root: str, **kwargs):
  cache_root = os.path.abspath(cache_root)
  if not os.path.exists(cache_root):
    os.makedirs(cache_root, exist_ok=True)

  folder = tempfile.mkdtemp(dir=cache_root, **kwargs)

  return os.path.relpath(folder, cache_root)
