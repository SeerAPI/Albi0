from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, NewType

from dataclasses_json import DataClassJsonMixin
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


@dataclass
class Manifest(DataClassJsonMixin):
	version: str
	items: dict[LocalFileName, ManifestItem]


dataclasses_json.cfg.global_config.decoders[ManifestItem] = lambda values: ManifestItem(
	*values
)


class AbstractVersionManager(ABC):
	@abstractmethod
	def get_remote_manifest(self) -> Manifest:
		pass

	@abstractmethod
	def load_local_manifest(self) -> Manifest:
		pass

	@abstractmethod
	def get_remote_version(self) -> str:
		pass

	@abstractmethod
	def load_local_version(self) -> str:
		pass

	@property
	@abstractmethod
	def is_version_outdated(self) -> bool:
		"""如果本地版本不存在或需要更新，返回True，反之返回False"""
		pass

	def generate_update_manifest(self) -> dict[LocalFileName, ManifestItem]:
		"""比对本地与远程清单，返回需要更新的资源。"""
		if not self.is_version_outdated:
			return {}

		remote_items = self.get_remote_manifest().items
		local_items = self.load_local_manifest().items
		# 原代码：使用循环和字典构建需要更新的文件列表
		# result = {}
		# for local_fn, remote_manifest_item in remote_items.items():
		#     with suppress(KeyError):
		#         if local_items[local_fn].file_hash == remote_manifest_item.file_hash:
		#             continue
		#     result[local_fn] = remote_manifest_item

		def needs_update(item: tuple[LocalFileName, ManifestItem]) -> bool:
			local_fn, remote_manifest_item = item
			try:
				return local_items[local_fn].file_hash != remote_manifest_item.file_hash
			except KeyError:
				return True

		return dict(filter(needs_update, remote_items.items()))

	@abstractmethod
	def save_remote_manifest(self):
		"""保存远程资源清单到本地"""
		pass
