from pathlib import Path

from albi0.update.version import (
	AbstractVersionManager,
	LocalFileName,
	Manifest,
	ManifestItem,
)


class DummyVersionManager(AbstractVersionManager):
	"""用于测试的虚设版本管理器。"""

	def __init__(
		self,
		*,
		is_outdated: bool,
		remote_manifest: Manifest | None = None,
		local_manifest: Manifest | None = None,
		remote_version: str = '',
		local_version: str = '',
	) -> None:
		self._is_outdated = is_outdated
		self._remote_manifest = remote_manifest
		self._local_manifest = local_manifest
		self._remote_version = remote_version
		self._local_version = local_version

	def get_remote_manifest(self) -> Manifest:
		assert self._remote_manifest is not None
		return self._remote_manifest

	def load_local_manifest(self) -> Manifest:
		assert self._local_manifest is not None
		return self._local_manifest

	def get_remote_version(self) -> str:
		return self._remote_version

	def load_local_version(self) -> str:
		return self._local_version

	@property
	def is_version_outdated(self) -> bool:
		return self._is_outdated

	@property
	def is_local_version_exists(self) -> bool:
		return self._local_version != ''

	def save_manifest_to_local(self, manifest: Manifest) -> None:
		raise NotImplementedError


def lf(name: str | Path) -> LocalFileName:
	"""LocalFileName 的简写工厂函数。"""
	return LocalFileName(Path(name))


def make_manifest(version: str, items: dict[Path, tuple[str, str, bytes]]) -> Manifest:
	"""用于测试的清单工厂函数。"""
	mapped: dict[LocalFileName, ManifestItem] = {}
	for local_basename, (remote_filename, local_basename2, file_hash) in items.items():
		mapped[lf(local_basename)] = ManifestItem(
			remote_filename,
			local_basename2,
			file_hash,
		)
	return Manifest(version=version, items=mapped)


def test_generate_update_manifest_returns_none_when_no_update_is_needed(mocker):
	"""测试当本地和远程清单相同时，generate_update_manifest 应返回 None。"""
	manifest = make_manifest(
		'1',
		{
			Path('a.bin'): ('a.r', 'a.bin', b'h1'),
		},
	)
	vm = DummyVersionManager(
		is_outdated=False,  # 该属性不被 generate_update_manifest 使用
		remote_manifest=manifest,
		local_manifest=manifest,
	)
	spy_get_remote = mocker.spy(vm, 'get_remote_manifest')
	spy_load_local = mocker.spy(vm, 'load_local_manifest')

	result = vm.generate_update_manifest()

	assert result is None
	assert spy_get_remote.call_count == 1
	assert spy_load_local.call_count == 1


def test_generate_update_manifest_filters_missing_and_mismatched_hashes(mocker):
	"""测试 generate_update_manifest 是否能正确识别哈希不匹配和缺失的文件。"""
	# 远程: a(h1), b(h2), c(h3)
	remote = make_manifest(
		'2',
		{
			Path('a.bin'): ('a.r', 'a.bin', b'h1'),
			Path('b.bin'): ('b.r', 'b.bin', b'h2'),
			Path('c.bin'): ('c.r', 'c.bin', b'h3'),
		},
	)
	# 本地: a(h1) 相同, b(h2x) 不同, c 缺失
	local = make_manifest(
		'1',
		{
			Path('a.bin'): ('a.r', 'a.bin', b'h1'),
			Path('b.bin'): ('b.r', 'b.bin', b'h2x'),
		},
	)

	vm = DummyVersionManager(
		is_outdated=True,
		remote_manifest=remote,
		local_manifest=local,
	)

	spy_get_remote = mocker.spy(vm, 'get_remote_manifest')
	spy_load_local = mocker.spy(vm, 'load_local_manifest')

	result = vm.generate_update_manifest()

	# 预期 b.bin (哈希不匹配) 和 c.bin (缺失) 会被包含
	assert result is not None
	assert result.version == '2'
	assert set(result.items.keys()) == {lf('b.bin'), lf('c.bin')}
	assert result.items[lf('b.bin')].file_hash == b'h2'
	assert result.items[lf('c.bin')].file_hash == b'h3'

	# 应该只读取一次本地和远程清单
	assert spy_get_remote.call_count == 1
	assert spy_load_local.call_count == 1


def test_generate_update_manifest_when_versions_are_same_but_content_differs(
	mocker,
):
	"""测试当本地和远程版本号相同但内容不同时，仍能正确生成更新清单。"""
	# 远程: a(h1), b(h2)
	remote = make_manifest(
		'1',
		{
			Path('a.bin'): ('a.r', 'a.bin', b'h1'),
			Path('b.bin'): ('b.r', 'b.bin', b'h2'),  # 哈希值不同
		},
	)
	# 本地: a(h1), b(h2x)
	local = make_manifest(
		'1',
		{
			Path('a.bin'): ('a.r', 'a.bin', b'h1'),
			Path('b.bin'): ('b.r', 'b.bin', b'h2x'),  # 哈希值不同
		},
	)

	vm = DummyVersionManager(
		is_outdated=False,  # 版本号相同
		remote_manifest=remote,
		local_manifest=local,
		remote_version='1',
		local_version='1',
	)

	spy_get_remote = mocker.spy(vm, 'get_remote_manifest')
	spy_load_local = mocker.spy(vm, 'load_local_manifest')

	result = vm.generate_update_manifest()

	# 预期只有 b.bin (哈希不匹配) 会被包含
	assert result is not None
	assert result.version == '1'
	assert set(result.items.keys()) == {lf('b.bin')}
	assert result.items[lf('b.bin')].file_hash == b'h2'

	# 应该只读取一次本地和远程清单
	assert spy_get_remote.call_count == 1
	assert spy_load_local.call_count == 1


def test_generate_update_manifest_empty_remote_items(mocker):
	"""测试当远程清单为空时，generate_update_manifest 应返回 None。"""
	remote = make_manifest('2', {})
	local = make_manifest('1', {Path('x.bin'): ('x.r', 'x.bin', b'hX')})

	vm = DummyVersionManager(
		is_outdated=True,
		remote_manifest=remote,
		local_manifest=local,
	)

	spy_get_remote = mocker.spy(vm, 'get_remote_manifest')
	spy_load_local = mocker.spy(vm, 'load_local_manifest')

	result = vm.generate_update_manifest()

	assert result is None
	assert spy_get_remote.call_count == 1
	assert spy_load_local.call_count == 1


def test_serialize_manifest_to_json():
	"""测试 Manifest 的 to_json 和 from_json 方法是否能正确序列化和反序列化。"""
	remote_manifest = make_manifest('2', {Path('x.bin'): ('x.r', 'x.bin', b'hX')})
	remote_manifest_json = remote_manifest.to_json()
	remote_manifest_from_json = Manifest.from_json(remote_manifest_json)
	assert remote_manifest == remote_manifest_from_json
