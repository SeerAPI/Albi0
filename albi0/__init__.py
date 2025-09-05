import sys

from asyncer import asyncify

from albi0.cli import cli

if sys.version_info < (3, 10):
    from importlib_metadata import version
else:
    from importlib.metadata import version

try:
    __version__ = version("albi0")
except Exception:
    __version__ = None


async def cli_main(*args, **kwargs):
    return await asyncify(cli)(*args, **kwargs)
