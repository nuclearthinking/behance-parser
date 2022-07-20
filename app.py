import logging

import click

from behance_parser import exporter, html_parser, parser, storage

logging.basicConfig(
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command(name="add-agencies")
@click.argument("agencies")
def add_agencies(agencies):
    click.echo(f"Invoked command add-agencies with agencies {agencies}")
    storage.create_agencies(agencies=agencies.split(","))


@cli.command(name="collect-tasks")
def collect_tasks():
    logger.info("Invoked command collect-tasks")
    parser.collect_tasks_for_parsing()


@cli.command(name="process-tasks")
def process_tasks():
    logger.info("Invoked command process-tasks")
    html_parser.process_tasks()


@cli.command(name="export-data")
@click.option("--path", default=None, help="Path to exporting parsing results")
def export_data(path):
    logger.info("Invoked command export-data")
    exporter.export_data_to(path)
    logger.info("Exporting data finished")


if __name__ == "__main__":
    cli()
