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

	async def update(self, progress_bar_message: str):
		if self.version_manager.is_version_outdated:
			tasks = [
				DownloadParams(url=item.remote_filename, filename=local_fn)
				for local_fn, item in self.version_manager.generate_update_manifest().items()
			]
			await self.downloader.downloads(
				*tasks,
				desc=progress_bar_message,
				postprocess_handler=self.postprocess_handler,
			)
			self.version_manager.save_remote_manifest()
