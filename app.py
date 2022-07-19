import logging

import click

from behance_parser.parser import collect_tasks_for_parsing
from behance_parser.storage import create_agencies

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command(name="add-agencies")
@click.argument("agencies")
def add_agencies(agencies):
    click.echo(f"Invoked command add-agencies with agencies {agencies}")
    create_agencies(agencies=agencies.split(","))


@cli.command(name="collect-tasks")
def collect_tasks():
    logger.info("Invoked command collect-tasks")
    collect_tasks_for_parsing()


def process_tasks():
    logger.info("Invoked command process-tasks")


if __name__ == "__main__":
    cli()
