from asyncio import Semaphore
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, NamedTuple

import aiofiles
import anyio
from httpx import URL
from tqdm.asyncio import tqdm

from ..request import client as default_client
from ..typing import DownloadPostProcessMethod
from ..utils import Hash

if TYPE_CHECKING:
	from httpx import AsyncClient, Response
	from httpx._types import URLTypes


class DownloadParams(NamedTuple):
	url: 'URLTypes'
	filename: Path
	method: Literal['GET', 'POST'] = 'GET'
	md5: str | None = None


class Downloader:
	_global_client: ClassVar['AsyncClient'] = default_client

	def __init__(self, client: 'AsyncClient | None' = None, limit: int = 10):
		self._client = client or self._global_client
		self._semaphore = Semaphore(limit)

	async def _get_data(
		self,
		url: 'URLTypes',
		*,
		method: Literal['GET', 'POST'] = 'GET',
		md5: str | None = None,
	) -> bytes:
		url = URL(str(url))
		async with self._client.stream(method, url, timeout=None) as res:
			res: 'Response'
			res.raise_for_status()

			data = b''
			with tqdm(
				total=int(res.headers['content-length']),
				unit_scale=True,
				unit_divisor=1024,
				unit='B',
				desc=f'{url.path.split("/")[-1]}下载中',
				leave=False,
			) as progress_bar:
				num_bytes_downloaded = res.num_bytes_downloaded
				async for chunk in res.aiter_bytes():
					data += chunk
					progress_bar.update(res.num_bytes_downloaded - num_bytes_downloaded)
					num_bytes_downloaded = res.num_bytes_downloaded

		if md5 is not None and Hash(data).md5() != md5:
			raise

		return data

	async def download(
		self,
		url: 'URLTypes',
		filename: Path,
		*,
		method: Literal['GET', 'POST'] = 'GET',
		md5: str | None = None,
		postprocess_handler: DownloadPostProcessMethod | None = None,
	):
		async with self._semaphore:
			data = await self._get_data(url, method=method, md5=md5)
			if postprocess_handler is not None:
				data = postprocess_handler(data)

			filename.parent.mkdir(parents=True, exist_ok=True)
			async with aiofiles.open(filename, mode='wb') as f:
				await f.write(data)

	async def downloads(
		self,
		*params: DownloadParams,
		desc: str | None = None,
		postprocess_handler: DownloadPostProcessMethod | None = None,
	) -> None:
		with tqdm(total=len(params), desc=desc) as progress_bar:

			async def _handle(p: DownloadParams):
				await self.download(
					p.url,
					p.filename,
					method=p.method,
					md5=p.md5,
					postprocess_handler=postprocess_handler,
				)
				progress_bar.update()

			async with anyio.create_task_group() as tg:
				for param in params:
					tg.start_soon(_handle, param)
