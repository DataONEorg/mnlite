import json
import pyshacl

from defs import DEFAULT_JSON, FIELDS, FILL_FIELDS, SITEMAP_URLS, ORCID_PREFIX
from mnonboard import L

def default_json():
    """
    A function that spits out a json file to be used in onboarding.
    """
    L.info('Loading default json template.')
    return json.loads(DEFAULT_JSON)

def load_json(loc):
    """
    Load json from file.
    """
    L.info('Loading member node json from %s' % loc)
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
    L.info('Writing member node json to %s' % loc)
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
                    L.warning('ORCiD number failed check (%s has no dash in position %s)' % (orcid, i+1))
                    return False
            try:
                # int exists in correct position, next test
                int(orcid[i])
                continue
            except ValueError as e:
                # fail (not an integer)
                #print('valueerror at %s' % i)
                L.warning('ORCiD number failed check (%s has no integer in position %s)' % (orcid, i+1))
                return False
        # pass
        L.info('ORCiD number passed checks. (%s)' % orcid)
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
        L.info('Sitemap URL #%s: %s' % (i+1, SITEMAP_URLS[i]))
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
            i = input(prompt)
            L.info('User has entered %s' % i)
            i = int(i)
            # must be 1 or greater
            assert i >= 1
            # tests ok
            return i
        except ValueError as e:
            L.warning('Not an integer. Error text: %s' % e)
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
        L.info('User has entered ORCiD number %s' % o)
        # make sure user has entered a valid ORCiD number
        if valid_orcid(o):
            return ORCID_PREFIX + o
        else:
            L.warning("Invalid ORCiD number entered: %s" % o)
            print('Please enter a valid ORCiD number (ex: 0000-0000-0000-0000).')

def user_input():
    """
    We need a few pieces of information to fill the json fields.
    """
    L.info('Collecting user input (mnonboard.mnutils.user_input()).')
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
    # first, test that there are the fields we need
    L.info('Running mnonboard.mnutils.input_test() on imported json.')
    for f in FILL_FIELDS:
        try:
            if f in ('contact_subject', 'default_submitter', 'default_owner'):
                # orcid number will be preceded by a url prefix but no trailing slash
                if ORCID_PREFIX not in fields[f]:
                    L.error('ORCiD number in %s field does not have the correct URL prefix.' % (f))
                    print('Please ensure the correct URL prefix (%s) preceeds the ORCiD number in field %s' % (ORCID_PREFIX,f))
                if fields[f][-1] in '/':
                    L.error('ORCiD number in %s field has a trailing slash.')
                    print('Please remove the trailing slash (/) from the end of the ORCiD number in field %s' % f)
                    exit(1)
                assert valid_orcid(fields[f].split('/')[-1])
        except ValueError as e:
            L.error('No "%s" field found in json.' % f)
            print('Please add the "%s" field to the json and re-run the script.' % f)
            exit(1)
        except AssertionError as e:
            L.error('Invalid ORCiD number %s in field "%s"' % (fields[f], f))
            print('Please correct the ORCiD number in field "%s"' % f)
            exit(1)
    L.info('Loaded json info has passed checks.')
    return True
