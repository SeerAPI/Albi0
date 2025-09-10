from collections.abc import Generator, Iterable, Iterator
from contextlib import contextmanager
import fnmatch
import functools
import gzip
import hashlib
import itertools
import os
from pathlib import Path
import time
from typing import AnyStr

from tqdm import tqdm

from albi0.log import logger
from albi0.typing import PathTypes, T_PathLike


class Hash:
	def __init__(self, data):
		self.data = data

	@classmethod
	def from_file(cls, filename: PathTypes):
		filename = Path(filename)
		return cls(filename.read_bytes())

	def md5(self) -> str:
		# 创建一个MD5哈希对象
		return hashlib.md5(self.data).hexdigest()

	def sha256(self) -> str:
		# 创建一个SHA256哈希对象
		return hashlib.sha256(self.data).hexdigest()


class FileHash(Hash):
	def __init__(self, filename: PathTypes):
		self.filename = Path(filename)
		super().__init__(self.filename.read_bytes())


def find_files(
	filenames: Iterable[AnyStr], patterns: Iterable[AnyStr]
) -> Iterator[AnyStr]:
	if not patterns:
		for filename in filenames:
			yield filename
	else:
		filter_partial = functools.partial(fnmatch.filter, filenames)
		for filename in itertools.chain(*map(filter_partial, patterns)):
			yield filename


def decompress_file(
	filename: Path, new_filename: Path, remove_original_file: bool = False
):
	"""解压一个gzip文件"""
	with gzip.open(filename, mode='rb') as f_in:
		data = f_in.read()
	with open(new_filename, 'wb') as f_out:
		f_out.write(data)
	if remove_original_file:
		filename.unlink()


def decompress_dir(
	dirname: Path,
	*,
	pattern: str,
	new_suffix: str | None = None,
	remove_original_file: bool = False,
) -> None:
	"""解压目录下所有的gzip文件"""
	files = list(dirname.glob(pattern))
	for file in tqdm(files, desc='解压中'):
		new_filename = file
		if new_suffix is not None:
			new_filename = new_filename.with_suffix(new_suffix)
		try:
			decompress_file(file, new_filename, remove_original_file)
		except gzip.BadGzipFile:
			logger.debug(f'{file.name}不是gzip压缩文件，跳过')


def remove_all_suffixes(filename: T_PathLike) -> T_PathLike:
	"""删除路径的所有后缀"""
	root, suffix = os.path.splitext(filename)
	while suffix:
		root, suffix = os.path.splitext(root)

	return type(filename)(root)  # type: ignore


@contextmanager
def set_directory(path: PathTypes):
	"""Sets the cwd within the context

	Args:
	    path (Path): The path to the cwd

	Yields:
	    None
	"""

	origin = Path().absolute()
	try:
		os.chdir(path)
		yield
	finally:
		os.chdir(origin)


def join_path(path: PathTypes, *args: PathTypes) -> Path:
	return Path(path).joinpath(*args)


def join_url(base: str, *urls: str) -> str:
	from urllib.parse import urljoin

	for url in urls:
		base = urljoin(base, url)

	return base


@contextmanager
def timer(
	message_template: str = '{name} 耗时: {duration:.2f}s', **kwargs
) -> Generator[None, None, None]:
	"""一个简单的计时器上下文管理器

	Args:
		message_template: 最终展示的字符串模板.
		**kwargs: 模板中可用的额外参数.
	"""
	import click

	start_time = time.perf_counter()
	try:
		yield
	finally:
		end_time = time.perf_counter()
		duration = end_time - start_time
		click.echo(message_template.format(duration=duration, **kwargs))
