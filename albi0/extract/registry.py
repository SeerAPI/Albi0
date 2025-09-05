from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from UnityPy.enums import ClassIDType
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.tools.extractor import EXPORT_TYPES

from albi0.typing import (
	ExportHandlerResult,
	ObjectPath,
	PathTypes,
	T_AssetPostHandler,
	T_ExportHandler,
	T_ObjPreHandler,
)

if TYPE_CHECKING:
	from UnityPy.classes import Object
	from UnityPy.files import ObjectReader

KT = TypeVar('KT')
T_Callable = TypeVar('T_Callable', bound=Callable)


class SkipCurrentHandlerGroup(Exception): ...


class StopExtractThisObject(Exception): ...


class BaseHandlerGroup(ABC):
	@abstractmethod
	def register(self, *args, **kwargs):
		raise NotImplementedError


class ListHandlerGroup(list[T_Callable], BaseHandlerGroup):
	def register(self):
		def _decorator(func: T_Callable) -> T_Callable:
			self.append(func)
			return func

		return _decorator


class DictHandlerGroup(dict[KT, T_Callable], BaseHandlerGroup):
	def register(self, key: KT):
		def _decorator(func: T_Callable) -> T_Callable:
			self[key] = func
			return func

		return _decorator


class MultiValuesDictHandlerGroup(dict[KT, list[T_Callable]], BaseHandlerGroup):
	def register(self, key: KT):
		def _decorator(func: T_Callable) -> T_Callable:
			try:
				self[key].append(func)
			except KeyError:
				self[key] = [func]
			return func

		return _decorator


class AssetPostHandlerGroup(ListHandlerGroup[T_AssetPostHandler]):
	"""Asset后处理程序组"""

	def handle(
		self, obj: 'ObjectReader', export_dir: Path
	) -> tuple[ObjectReader[Any], Path]:
		for handler in self:
			try:
				obj, export_dir = handler(obj, export_dir)
			except SkipCurrentHandlerGroup:
				break

		return obj, export_dir


class ObjPreHandlerGroup(MultiValuesDictHandlerGroup[ClassIDType, T_ObjPreHandler]):
	"""
	Unity对象预处理程序组，key为Unity对象ClassID，value为handler列表。
	处理方式为按ClassID链式处理。
	"""

	def handle(
		self, obj: 'Object', obj_path: ObjectPath
	) -> tuple['Object', ObjectPath]:
		if (obj_reader := obj.object_reader) is None:
			raise ValueError(f'{obj_path} has no object reader')
		handlers = self.get(obj_reader.type, [])
		for handler in handlers:
			try:
				obj, obj_path = handler(obj, obj_path)
			except SkipCurrentHandlerGroup:
				break

		return obj, obj_path


class ExportHandlerGroup(DictHandlerGroup[ClassIDType, T_ExportHandler]):
	"""
	导出处理器组，用于自定义Unity对象的导出逻辑，
	key为Unity对象ClassID，value为导出函数。

	当没有对应的handler时，会使用UnityPy的默认导出逻辑。
	"""

	def __init__(self, mapping: Mapping[ClassIDType, T_ExportHandler] | None = None):
		super().__init__({**EXPORT_TYPES, **(mapping or {})})

	def handle(
		self,
		obj: 'Object',
		obj_type: ClassIDType,
		export_filename: PathTypes,
		*,
		suffix: str,
		export_unknown_as_typetree: bool = False,
	) -> ExportHandlerResult | None:
		export_filename = Path(export_filename)
		try:
			handler = self[obj_type]
		except KeyError:
			if export_unknown_as_typetree:
				handler = self[ClassIDType.MonoBehaviour]
			else:
				return None

		return handler(obj, export_filename, suffix)
