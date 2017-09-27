import sys
import logging
import importlib
"""Stub versions of optional submodules which may fail to clone."""


class Shim(object):
  def __init__(self):
    self.is_shim = True


class version(Shim):
  def get_version(self):
    return None


class simplewrap(Shim):
  class Wrapper(object):
    def __init__(self):
      self.width = 80
    def wrap(self, string):
      return string


class phone(Shim):
  def send_start(script_path,
                 version,
                 domain=None,
                 secure=None,
                 platform=None,
                 test=False,
                 fail='warn'):
    pass
  def send_end(script_path,
               version,
               run_id,
               run_time,
               optional_run_data={},
               domain=None,
               secure=None,
               platform=None,
               test=False,
               fail='warn'):
    pass


class parallel(Shim):
  class Sentinel(object):
    pass
  class RotatingPool(list):
    def __init__(self, num_workers, function, static_args=None, give_logger=False):
      list.__init__(self)
      self.function = function
      self.jobs_submitted = 0
      if static_args is None:
        self.static_args = []
      else:
        self.static_args = list(static_args)
      if give_logger:
        self.static_args.append(logging)
    def compute(self, *input_data):
      args = list(input_data) + self.static_args
      self.jobs_submitted += 1
      return self.function(*args)
    def flush(self):
      if False:
        yield None
    def stop(self):
      pass


def get_module_or_shim(module_path):
  """Load the given module, or if not possible, return a stub."""
  try:
    return importlib.import_module(module_path)
  except ImportError:
    sys.stderr.write('Error importing module '+module_path+'. Some functionality may be missing.\n')
  module_name = module_path.split('.')[-1]
  try:
    shim = globals()[module_name]
  except KeyError:
    sys.stderr.write('Error: cannot find a shim named "'+module_name+'".\n')
    raise
  try:
    return shim()
  except TypeError:
    sys.stderr.write('Error: problem loading shim "'+module_name+'".\n')
    raise
