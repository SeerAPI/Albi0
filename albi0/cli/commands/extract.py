import glob
import itertools
from pathlib import Path

from asyncer import syncify
import click

from albi0.extract.extractor import extractors
from albi0.log import logger
from albi0.utils import join_path, timer


@click.command(context_settings={'ignore_unknown_options': True})
@click.option(
	'-o',
	'--output-dir',
	default=None,
	type=click.Path(file_okay=False, writable=True),
)
@click.option(
	'-n',
	'--extractor-name',
	default='default',
	type=str,
)
@click.option(
	'-e',
	'--export-as-is',
	default=False,
	is_flag=True,
	show_default=True,
)
@click.option(
	'-m',
	'--merge-extract',
	default=False,
	is_flag=True,
	show_default=True,
)
@click.option(
	'-t',
	'--parallel-threads',
	'--max-workers',
	default=4,
	type=int,
	show_default=True,
)
@click.argument('patterns', nargs=-1, default=None)
@click.pass_context
@syncify
async def extract(
	ctx: click.Context,
	patterns: list[str] | None,
	output_dir: str | None,
	extractor_name: str,
	export_as_is: bool,
	merge_extract: bool,
	parallel_threads: int,
):
	output_dir = output_dir or '.'
	patterns = patterns or []
	ab_paths: set[Path] = {
		Path(path).resolve()
		for path in itertools.chain.from_iterable(map(glob.iglob, patterns))
	}

	if export_as_is:
		extractor_name = 'default'

	extractor_set = extractors.get_processors(extractor_name)

	if not extractor_set:
		click.echo(f'找不到输入的提取器/组{extractor_name}')
		return

	with timer('✅ 提取完成~ 总耗时: {duration:.2f}s'):
		for extractor in extractor_set:
			click.echo(f'运行提取器：{extractor.name}')
			try:
				extractor.extract_asset(
					*ab_paths,
					export_dir=join_path(extractor_name, output_dir),
					merge_extract=merge_extract,
					max_workers=parallel_threads,
				)
				click.echo(f'✅ {extractor.name}提取完成~')
			except Exception as e:
				logger.opt(exception=e).error(e)
				click.echo(f'❌ {extractor.name}提取失败.')
				raise
