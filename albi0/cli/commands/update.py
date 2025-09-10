import os

import anyio
from asyncer import syncify
import click
from tqdm.asyncio import tqdm

from albi0.update import updaters
from albi0.utils import set_directory, timer


@click.command(help='更新资源清单并下载资源文件')
@click.option(
	'-w',
	'--working-dir',
	default=None,
	type=click.Path(exists=True, file_okay=False, writable=True),
)
@click.option(
	'-n',
	'--updater-name',
	type=str,
	help='更新器名称，支持传入更新器/组名',
)
@click.option(
	'-s',
	'--semaphore-limit',
	'--max-workers',
	default=10,
	type=int,
	show_default=True,
)
@click.option(
	'--version-only',
	is_flag=True,
	default=False,
	help='仅获取远程版本号，不下载资源文件',
)
@click.argument('patterns', nargs=-1, default=None)
@click.pass_context
@syncify
async def update(
	ctx: click.Context,
	patterns: list[str] | None,
	working_dir: str | None,
	updater_name: str,
	version_only: bool,
	semaphore_limit: int,
) -> None:
	patterns = patterns or []
	os.chdir(working_dir or './')
	updater_set = updaters.get_processors(updater_name)
	if not updater_set:
		click.echo(f'找不到输入的更新器/组：{updater_name}')
		return

	_updater_string = '找到以下更新器：\n'
	_updater_string += ''.join(
		[f'    {name}: {processor.desc}\n' for name, processor in updaters.items()]
	)
	click.echo(_updater_string)

	with (
		timer('✅ 更新完成~ 总耗时: {duration:.2f}s'),
		set_directory(working_dir or './'),
	):
		for updater in updater_set:
			click.echo(f'运行更新器：{updater.name}')
			if version_only:
				click.echo(
					f'远程版本：{updater.version_manager.get_remote_version()}\n'
				)
				continue

			click.echo(
				f'本地版本：{updater.version_manager.load_local_version() or "无"}\n'
				f'远程版本：{updater.version_manager.get_remote_version()}\n'
				f'开始运行更新器...'
			)
			await updater.update(
				progress_bar=tqdm(desc='下载资源文件', unit='file'),
				patterns=patterns,
				semaphore=anyio.Semaphore(semaphore_limit),
			)
			click.echo(
				f'✅(<ゝω・)～☆更新完毕！'
				f'本地版本：{updater.version_manager.load_local_version() or "无"}\n'
			)
