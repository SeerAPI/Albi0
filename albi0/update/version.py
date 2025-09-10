from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, NewType
from typing_extensions import Self

from dataclasses_json import DataClassJsonMixin, config
import dataclasses_json.cfg

LocalFileName = NewType('LocalFileName', Path)


def register_path_encoder() -> None:
	from pathlib import Path, PosixPath, WindowsPath

	for path_type in (Path, PosixPath, WindowsPath):
		dataclasses_json.cfg.global_config.encoders[path_type] = str


register_path_encoder()


class ManifestItem(NamedTuple):
	remote_filename: str
	local_basename: str
	file_hash: bytes


def encode_manifest_items(items: dict[LocalFileName, ManifestItem]) -> dict:
	return {
		str(local_fn): {
			'remote_filename': item.remote_filename,
			'local_basename': item.local_basename,
			'file_hash': item.file_hash.hex(),
		}
		for local_fn, item in items.items()
	}


def decode_manifest_items(items: dict) -> dict[LocalFileName, ManifestItem]:
	return {
		LocalFileName(Path(local_fn)): ManifestItem(
			item['remote_filename'],
			item['local_basename'],
			bytes.fromhex(item['file_hash']),
		)
		for local_fn, item in items.items()
	}


@dataclass
class Manifest(DataClassJsonMixin):
	version: str
	items: dict[LocalFileName, ManifestItem] = field(
		metadata=config(
			encoder=encode_manifest_items,
			decoder=decode_manifest_items,
		)
	)

	def filter_local_filenames_by_glob(self, *patterns: str) -> Self:
		"""使用glob模式从本地文件名中筛选

		Args:
			*patterns: 一个或多个glob模式字符串，如 "*.txt", "data/**/*.json"

		Returns:
			包含匹配文件的新Manifest实例，返回所有模式的并集，如果patterns为空，则原样返回
		"""
		from fnmatch import fnmatch

		if not patterns:
			return self

		filtered_items = {}
		for local_fn, item in self.items.items():
			for pattern in patterns:
				if fnmatch(item.local_basename, pattern):
					filtered_items[local_fn] = item
					break

		return self.__class__(version=self.version, items=filtered_items)


dataclasses_json.cfg.global_config.decoders[ManifestItem] = lambda values: ManifestItem(
	*values
)


class AbstractVersionManager(ABC):
	@property
	@abstractmethod
	def is_local_version_exists(self) -> bool:
		"""本地版本是否存在"""
		pass

	@abstractmethod
	def load_local_manifest(self) -> Manifest:
		pass

	@abstractmethod
	def save_manifest_to_local(self, manifest: Manifest) -> None:
		pass

	@abstractmethod
	def load_local_version(self) -> str:
		pass

	@abstractmethod
	def get_remote_manifest(self) -> Manifest:
		pass

	@abstractmethod
	def get_remote_version(self) -> str:
		pass

	@property
	@abstractmethod
	def is_version_outdated(self) -> bool:
		"""
		如果本地版本不存在或版本号小于远程版本号，返回True，反之返回False，
		注意该方法仅判断版本号，不能用于判断是否需要下载资源。
		"""

	def generate_update_manifest(self, *patterns: str) -> Manifest | None:
		"""
		比对本地与远程清单，返回需要更新的资源。

		Args:
			*patterns: 一个或多个glob模式字符串，如 "*.txt", "data/**/*.json"

		Returns:
			包含匹配资源的清单，返回所有模式的并集，patterns为空则原样返回，
			如果没有需要更新的资源，返回None。
		"""
		remote_manifest = self.get_remote_manifest()
		local_manifest = self.load_local_manifest()
		remote_version = remote_manifest.version
		remote_items = remote_manifest.filter_local_filenames_by_glob(*patterns).items
		local_items = local_manifest.filter_local_filenames_by_glob(*patterns).items

		if local_items == remote_items or not remote_items:
			return None

		def needs_update(item: tuple[LocalFileName, ManifestItem]) -> bool:
			local_fn, remote_manifest_item = item
			try:
				return local_items[local_fn].file_hash != remote_manifest_item.file_hash
			except KeyError:
				return True

		items = filter(needs_update, remote_items.items())
		if not items:
			return None

		return Manifest(version=remote_version, items=dict(items))

	def save_remote_manifest(self) -> None:
		"""保存远程资源清单到本地"""
		manifest = self.get_remote_manifest()
		self.save_manifest_to_local(manifest)
