import click
from pathlib import Path
import logging
import sys
from .server import serve

@click.command()
@click.option("-r", "--servicetype", type=str, help="Type of service to query")
@click.option("-v", "--verbose", count=True)
def main(servicetype: str | None, verbose: bool) -> None:
    """OpenMetadata connector - functionality for MCP"""
    import asyncio

    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)
    asyncio.run(serve(servicetype))

if __name__ == "__main__":
    main()
