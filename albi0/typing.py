from collections.abc import Callable
import os
from pathlib import Path, PurePath
from typing import NewType, Optional, TypeAlias, TypeVar

from UnityPy.classes import NamedObject
from UnityPy.files import ObjectReader, SerializedFile

PathTypes: TypeAlias = Path | str

DecryptionMethod: TypeAlias = Callable[[memoryview], memoryview]

DownloadPostProcessMethod = Callable[[bytes], bytes]

ObjectPath = NewType('ObjectPath', PurePath)

T_PathLike = TypeVar('T_PathLike', str, ObjectPath, os.PathLike)

T_NamedObject = TypeVar('T_NamedObject', bound='NamedObject')

T_AssetPostHandler: TypeAlias = Callable[
	['ObjectReader', Path], tuple['ObjectReader', Path]
]
T_ObjPreHandler: TypeAlias = Callable[
	[T_NamedObject, ObjectPath], tuple[T_NamedObject, ObjectPath]
]
ExportHandlerResult: TypeAlias = list[tuple[Optional['SerializedFile'], int]]
T_ExportHandler: TypeAlias = Callable[
	[T_NamedObject, PathTypes, str], ExportHandlerResult
]
