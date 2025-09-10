from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Optional, TypeVar, cast

from tqdm import tqdm
from UnityPy import Environment
from UnityPy.environment import reSplit

from albi0.container import ProcessorContainer
from albi0.log import logger
from albi0.typing import (
	DecryptionMethod,
	ExportHandlerResult,
	ObjectPath,
	PathTypes,
)

from .registry import (
	AssetPostHandlerGroup,
	ExportHandlerGroup,
	ObjPreHandlerGroup,
	StopExtractThisObject,
)

if TYPE_CHECKING:
	from UnityPy.classes import PPtr
	from UnityPy.files import ObjectReader


extractors: ProcessorContainer['Extractor'] = ProcessorContainer()

_T = TypeVar('_T')


def _create_obj(obj: _T | None, type_: type[_T]) -> _T:
	return type_() if obj is None else obj


T = TypeVar('T')


def _output_as_is(x: T) -> T:
	return x


class Extractor:
	def __init__(
		self,
		name: str,
		desc: str,
		*,
		decryption_method: Optional['DecryptionMethod'] = None,
		asset_posthandler_group: Optional['AssetPostHandlerGroup'] = None,
		obj_prehandler_group: Optional['ObjPreHandlerGroup'] = None,
		export_handler_group: Optional['ExportHandlerGroup'] = None,
	) -> None:
		self.name = name
		self.desc = desc

		self.decryption_method = decryption_method or _output_as_is
		self.asset_posthandler_group = _create_obj(
			asset_posthandler_group, AssetPostHandlerGroup
		)
		self.obj_prehandler_group = _create_obj(
			obj_prehandler_group, ObjPreHandlerGroup
		)
		self.export_handler_group = _create_obj(
			export_handler_group, ExportHandlerGroup
		)

		extractors[name] = self

	def from_file_load(self, *filenames: PathTypes) -> Environment:
		env = Environment()
		for filename in tqdm(
			filenames,
			desc='加载文件到内存...',
			disable=len(filenames) == 1,
			unit='file',
		):
			if split_match := reSplit.match(str(filename)):
				name = split_match.groups()[0]
			else:
				name = filename

			with open(filename, mode='rb') as f:
				data = self.decryption_method(memoryview(f.read()))

			env.load_file(cast(BytesIO, data), name=str(name))

		return env

	def extract_asset(
		self,
		*sources: PathTypes,
		export_dir: PathTypes,
		max_workers: int = 4,
		merge_extract: bool = False,
		export_unknown_as_typetree: bool = True,
	) -> None:
		export_types_keys = list(self.export_handler_group.keys())
		export_dir = Path(export_dir)

		def defaulted_export_index(type_: 'ObjectReader'):
			try:
				return export_types_keys.index(type_.type)
			except (IndexError, ValueError):
				return 999
			except Exception as e:
				logger.opt(exception=e).error(f'{e}')
				return -1

		def handle_asset(
			environment: 'Environment',
		) -> 'list[tuple[ObjectReader, ObjectPath]]':
			_result = []
			container = sorted(
				environment.container.items(),
				key=lambda x: defaulted_export_index(x[1]),  # type: ignore
			)
			for obj_path, obj in container:
				try:
					obj = cast('PPtr', obj)
					obj = obj.deref()
					obj, _ = self.asset_posthandler_group.handle(
						obj, export_dir=export_dir
					)
					_result.append((obj, ObjectPath(PurePath(obj_path))))
				except StopExtractThisObject:
					continue
				except Exception as e:
					logger.opt(exception=e).error(f'{obj_path} | {e}')
					continue

			return _result

		def export_obj(
			obj_: 'ObjectReader', obj_path_: ObjectPath
		) -> ExportHandlerResult | None:
			obj_type = obj_.type
			readed_obj_ = obj_.read()  # 返回实际对象
			if self.obj_prehandler_group:
				readed_obj_, obj_path_ = self.obj_prehandler_group.handle(
					readed_obj_, obj_path_
				)

			export_filename = Path(export_dir, obj_path_)
			export_filename.parent.mkdir(parents=True, exist_ok=True)
			# export
			return self.export_handler_group.handle(
				readed_obj_,
				obj_type,
				export_filename.with_suffix(''),
				suffix=export_filename.suffix,
				export_unknown_as_typetree=export_unknown_as_typetree,
			)

		with (
			ThreadPoolExecutor(max_workers=max_workers) as executor,
			tqdm(
				desc='提取中...',
				total=None,
				disable=not merge_extract,
				unit='object',
			) as pbar,
		):

			def export_single_obj(
				obj_and_path: tuple['ObjectReader', ObjectPath],
			) -> None:
				obj, obj_path = obj_and_path
				try:
					export_obj(obj, obj_path)
				except Exception as e:
					logger.opt(exception=e).error(f'{obj_path} | {e}')

			def export_wrap(env: Environment) -> None:
				objs = handle_asset(env)
				if not pbar.disable and pbar.total is None:
					pbar.total = len(objs)

				# 使用多进程处理每个对象的导出
				futures = [
					executor.submit(export_single_obj, obj_and_path)
					for obj_and_path in objs
				]
				for future in futures:
					future.add_done_callback(
						lambda _: pbar.update(1) if not pbar.disable else None
					)
					future.result()

			if merge_extract:
				env = self.from_file_load(*sources)
				export_wrap(env)
				return

			with tqdm(sources, unit='file') as not_merge_pbar:
				for source_fn in not_merge_pbar:
					not_merge_pbar.set_description(f'提取文件: {Path(source_fn).name}')
					env = self.from_file_load(source_fn)
					export_wrap(env)


Extractor('default', '默认提取器，直接提取不做任何处理')
