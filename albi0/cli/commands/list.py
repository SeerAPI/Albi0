import click

from albi0.extract.extractor import extractors
from albi0.update.updater import updaters


@click.command(help='获取所有提取器/更新器')
@click.pass_context
def list(ctx: click.Context):
	string = '更新器组：\n'
	string += ''.join(
		[f'    {name}: {processor.desc}\n' for name, processor in updaters.items()]
	)
	string += '\n'
	string += '提取器组：\n'
	string += ''.join(
		[f'    {name}: {processor.desc}\n' for name, processor in extractors.items()]
	)
	click.echo(string)
