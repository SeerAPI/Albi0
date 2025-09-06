import os

from asyncer import syncify
import click

from albi0.update import updaters
from albi0.utils import set_directory


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
@click.argument('patterns', nargs=-1, default=None)
@click.pass_context
@syncify
async def update(
	ctx: click.Context,
	patterns: list[str] | None,
	working_dir: str | None,
	updater_name: str,
):
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

	for updater in updater_set:
		click.echo(f'运行更新器：{updater.name}')
		if not updater.version_manager.is_version_outdated:
			click.echo('本地资源清单已经是最新版本了，跳过！ ')
			continue

		click.echo(
			f'本地版本：{updater.version_manager.load_local_version() or "无"}\n'
			f'远程版本：{updater.version_manager.get_remote_version()}\n'
			f'开始更新...'
		)
		with set_directory(working_dir or './'):
			await updater.update(
				progress_bar_message='下载资源文件',
				patterns=patterns,
			)
		click.echo(
			f'(<ゝω・)～☆资源下载完毕！本地版本：{updater.version_manager.load_local_version()}'
		)
