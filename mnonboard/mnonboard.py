import os
import sys
import json
import click

from . import mnutils

@click.command()
@click.option("--jsonfile", default=None,
              help="JSON file to load (defaults to None).")
@click.option("--createjson", default=None,
              help="Create a default blanked JSON file for the user to fill in themselves.")
def main(loc):
    """
    Wrapper around opersist that simplifies the process of onboarding a new
    member node to DataONE.
    """

    if loc is None:
        # do the full user-driven info gathering process
    else:
        # grab the info from a json


if __name__ == '__main__':
    main()
