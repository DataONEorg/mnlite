import os
import sys
import json
import click
import pyshacl

from mnonboard import L
import mnutils
from opersist.cli import getOpersistInstance

@click.command()
@click.option("-j", "--jsonfile", default=None,
              help="JSON file to load (defaults to None).")
@click.pass_context
def main(ctx, jsonfile):
    """
    Wrapper around opersist that simplifies the process of onboarding a new
    member node to DataONE.
    """

    if jsonfile is None:
        # do the full user-driven info gathering process
        fields = mnutils.user_input()
    else:
        # grab the info from a json
        fields = mnutils.load_json(jsonfile)
        mnutils.input_test(fields)

if __name__ == '__main__':
    main(ctx=None, jsonfile=None)
