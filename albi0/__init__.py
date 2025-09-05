from importlib.metadata import version

from asyncer import asyncify

from albi0.cli import cli

try:
	__version__ = version('albi0')
except Exception:
	__version__ = None


async def cli_main(*args, **kwargs):
	return await asyncify(cli)(*args, **kwargs)
