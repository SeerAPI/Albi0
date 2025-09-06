from collections.abc import Iterable

import click

from albi0.container import ProcessorContainer
from albi0.typing import DownloadPostProcessMethod

from .downloader import Downloader, DownloadParams
from .version import AbstractVersionManager

updaters: ProcessorContainer['Updater'] = ProcessorContainer()


class Updater:
	def __init__(
		self,
		name: str,
		desc: str,
		*,
		version_manager: AbstractVersionManager,
		downloader: Downloader,
		postprocess_handler: DownloadPostProcessMethod | None = None,
	) -> None:
		self.name = name
		self.desc = desc
		self.version_manager = version_manager
		self.downloader = downloader
		self.postprocess_handler = postprocess_handler

		updaters[self.name] = self

	async def update(
		self,
		*,
		progress_bar_message: str,
		save_manifest: bool = True,
		patterns: Iterable[str] = (),
	) -> None:
		"""异步更新资源文件

		检查版本是否过期，如果需要更新则下载新的资源文件并保存清单，过滤后没有需要更新的文件时不会保存清单。

		Args:
			progress_bar_message: 进度条显示的消息文本
			save_manifest: 是否保存清单
			patterns: glob语法的文件名过滤模式，用于过滤希望检查更新的文件。如果为空则更新所有文件
		"""
		if self.version_manager.is_version_outdated:
			manifest = self.version_manager.generate_update_manifest(*patterns)
			tasks = [
				DownloadParams(url=item.remote_filename, filename=local_fn)
				for local_fn, item in manifest.items()
			]
			if tasks:
				await self.downloader.downloads(
					*tasks,
					desc=progress_bar_message,
					postprocess_handler=self.postprocess_handler,
				)
			if save_manifest and (
				tasks or not self.version_manager.is_local_version_exists
			):
				self.version_manager.save_remote_manifest()
				click.echo(f'更新器：{self.name} | 资源清单更新完成')
