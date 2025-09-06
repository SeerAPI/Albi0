from pathlib import Path

from albi0.update.version import (
	AbstractVersionManager,
	LocalFileName,
	Manifest,
	ManifestItem,
)


class DummyVersionManager(AbstractVersionManager):
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

	def save_remote_manifest(self) -> None:
		raise NotImplementedError


def lf(name: str | Path) -> LocalFileName:
	return LocalFileName(Path(name))


def make_manifest(version: str, items: dict[Path, tuple[str, str, bytes]]) -> Manifest:
	mapped: dict[LocalFileName, ManifestItem] = {}
	for local_basename, (remote_filename, local_basename2, file_hash) in items.items():
		mapped[lf(local_basename)] = ManifestItem(
			remote_filename,
			local_basename2,
			file_hash,
		)
	return Manifest(version=version, items=mapped)


def test_generate_update_manifest_returns_empty_when_not_outdated(mocker):
	vm = DummyVersionManager(
		is_outdated=False,
		# Not accessed in this branch
		remote_manifest=None,
		local_manifest=None,
	)

	spy_get_remote = mocker.spy(vm, 'get_remote_manifest')
	spy_load_local = mocker.spy(vm, 'load_local_manifest')

	result = vm.generate_update_manifest()

	assert result == {}
	assert spy_get_remote.call_count == 0
	assert spy_load_local.call_count == 0


def test_generate_update_manifest_filters_missing_and_mismatched_hashes(mocker):
	# remote: a(h1), b(h2), c(h3)
	remote = make_manifest(
		'2',
		{
			Path('a.bin'): ('a.r', 'a.bin', b'h1'),
			Path('b.bin'): ('b.r', 'b.bin', b'h2'),
			Path('c.bin'): ('c.r', 'c.bin', b'h3'),
		},
	)
	# local: a(h1) same, b(h2x) different, c missing
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

	# Expect b.bin (hash mismatch) and c.bin (missing) to be included
	assert set(result.keys()) == {lf('b.bin'), lf('c.bin')}
	assert result[lf('b.bin')].file_hash == b'h2'
	assert result[lf('c.bin')].file_hash == b'h3'

	# Should read both manifests exactly once
	assert spy_get_remote.call_count == 1
	assert spy_load_local.call_count == 1


def test_generate_update_manifest_empty_remote_items(mocker):
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

	assert result == {}
	assert spy_get_remote.call_count == 1
	assert spy_load_local.call_count == 1


def test_serialize_manifest_to_json():
	remote_manifest = make_manifest('2', {Path('x.bin'): ('x.r', 'x.bin', b'hX')})
	remote_manifest_json = remote_manifest.to_json()
	remote_manifest_from_json = Manifest.from_json(remote_manifest_json)
	assert remote_manifest == remote_manifest_from_json
