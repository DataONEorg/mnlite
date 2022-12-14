import json
import pyshacl

from defs import DEFAULT_JSON, FIELDS, FILL_FIELDS, SITEMAP_URLS
from mnonboard import L

def default_json():
    """
    A function that spits out a json file to be used in onboarding.
    """
    return json.loads(DEFAULT_JSON)

def load_json(loc):
    """
    Load json from file.
    """
    try:
        with open(loc, 'r') as f:
            return json.load(f)
    except FileNotFoundError as e:
        L.error('File does not exist - %s' % e)
        exit(1)
    except Exception as e:
        L.error('Error: %s' % e)
        exit(1)

def save_json(loc, jf):
    """
    Output json to file.
    """
    with open(loc, 'w') as f:
        json.dump(jf, f)

def valid_orcid(orcid):
    """
    Checks the validity of an ORCiD number.

    ORCiDs have 4 groupings of 4 of integers separated by dashes (-)
    for a total of 19 characters, thus `0000-0000-0000-0000` is valid
    but `0000-0000-00000-000` and `0000-0000-0000-000` are not.

    This seems like overkill but is probably good to have since it will be
    used to store contacts for database upkeep/maintenance.
    """
    if (len(orcid) == 19):
        # it's 19 characters long. start test loop
        for i in range(0,19):
            # does it have a dash (-) in positions 5, 10, and 15?
            if i in (4, 9, 14):
                if orcid[i] in '-':
                    # dash exists in correct position, next test
                    continue
                else:
                    # fail (not a dash)
                    #print('no dash at %s' % i)
                    return False
            try:
                # int exists in correct position, next test
                int(orcid[i])
            except ValueError as e:
                # fail (not an integer)
                #print('valueerror at %s' % i)
                return False
        # pass
        return True
    else:
        # fail (not 19 characters)
        #print('not 19 chars')
        return False

def sitemap_urls(num_urls):
    """
    Collect the sitemap URLs.
    Usually there will be just one of these but we will prepare for more.
    """
    i = 0
    while i < num_urls:
        # add URLs one at a time (should only be a few at most)
        # if we start getting MNs with 10+ sitemap URLs, maybe we change to accept lists
        SITEMAP_URLS[i] = input("Sitemap URL #%s: " % (i+1))
        i += 1
    return SITEMAP_URLS

def enter_int(prompt):
    """
    Make sure the user enters an integer value of 1 or greater.
    """
    i = None
    while True:
        # make sure user enters an int
        try:
            # ask the user for input
            i = int(input(prompt))
            # must be 1 or greater
            assert i >= 1
            # tests ok
            return i
        except ValueError as e:
            L.warning(e)
            print('Please enter an integer.')
        except AssertionError as e:
            L.warning("Number of database sitemap URLs can't be less than 1. (%s entered)" % i)
            print('Please enter 1 or greater.')

def enter_orcid(prompt):
    """
    Make sure the user enters an integer value of 1 or greater.
    """
    while True:
        # ask the user for an ORCiD number
        o = input(prompt)
        # make sure user has entered a valid ORCiD number
        if valid_orcid(o):
            return o
        else:
            L.warning("Invalid ORCiD number entered: %s" % o)
            print('Please enter a valid ORCiD number (ex: 0000-0000-0000-0000).')

def user_input():
    """
    We need a few pieces of information to fill the json fields.
    """
    for f in FIELDS:
        if f in 'num_sitemap_urls':
            FIELDS[f][1] = enter_int(FIELDS[f][0])
        elif f in ('contact_subject', 'default_submitter', 'default_owner'):
            FIELDS[f][1] = enter_orcid(FIELDS[f][0])
        else:
            FIELDS[f][1] = input(FIELDS[f][0])
    # add the sitemap URLs field now that we're done with the loops
    FIELDS['sitemap_urls'] = ['Sitemap URLs: ', {}]
    # pass the number of mn sitemap URLs to sitemap_urls()
    # fx will ask the user to enter the URL(s) and return them as a dict
    # we then store it as the second list item in the 'sitemap_urls' field
    FIELDS['sitemap_urls'][1] = sitemap_urls(FIELDS['num_sitemap_urls'][1])
    return FIELDS

def input_test(fields):
    return 
