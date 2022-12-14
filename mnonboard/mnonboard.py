import os
import sys
import json
import click

import mnutils
from opersist.cli import getOpersistInstance

@click.command()
@click.option("-j", "--jsonfile", default=None,
              help="JSON file to load (defaults to None).")
@click.option("-c", "--createjson", default='node.json',
              help="Create a default blanked JSON file for the user to fill in themselves.")
def main(ctx, loc):
    """
    Wrapper around opersist that simplifies the process of onboarding a new
    member node to DataONE.
    """

    if loc is None:
        # do the full user-driven info gathering process
        fields = mnutils.user_input()
        fields['sitemap_urls'] = ['Sitemap URLs: ', '']
        # get the sitemap urls as a list
        fields['sitemap_urls'][1] = mnutils.sitemap_urls(fields['num_sitemap_urls'][1]) # type: ignore
    else:
        # grab the info from a json
        pass


if __name__ == '__main__':
    main()
