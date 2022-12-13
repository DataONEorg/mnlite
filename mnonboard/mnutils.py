import json
import pyshacl

from .defs import DEFAULT_JSON, FIELDS, FILL_FIELDS, SITEMAP_URLS
from . import L

def default_json():
    """
    A function that spits out a json file to be used in onboarding.
    """
    return json.loads(DEFAULT_JSON)

def user_input():
    """
    We need a few pieces of information to fill the json fields.
    """
    for f in FIELDS:
        if f in 'num_sitemap_urls':
            while True:
                try:
                    FIELDS[f][1] = int(input(FIELDS[f][0]))
                    break
                except ValueError as e:
                    L.warning(e)
                    print('Please enter an integer.')
            while True:
                if FIELDS[f][1] >= 1:
                    break
                else:
                    L.warning("The number of database sitemap URLs can't be less than 1.")
        elif f in ('contact_subject', 'default_submitter', 'default_owner'):
            while True:
                FIELDS[f][1] = input(FIELDS[f][0])
                if len(FIELDS[f][1]) == 19:
                    break
                else:
                    print('Please enter a valid ORCiD number (ex: 0000-0000-0000-0000).')
        else:
            FIELDS[f][1] = input(FIELDS[f][0])
    return FIELDS

def sitemap_urls(num_urls):
    """
    Collect the sitemap URLs.
    Usually there will be just one of these but we will prepare for more.
    """
    i = 0
    while i < num_urls:
        SITEMAP_URLS[i] = input("Sitemap URL #%s: " % (i+1))
        i += 1
    return SITEMAP_URLS
