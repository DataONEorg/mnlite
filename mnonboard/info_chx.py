import json

from defs import FIELDS, FILL_FIELDS, SITEMAP_URLS, ORCID_PREFIX, DEFAULT_JSON
from mnonboard import L

# user info checks

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

def valid_url_prefix(url, prefix, f):
    """
    Validate a URL prefix (such as for an ORCiD number).
    """
    # orcid number will be preceded by a url prefix but no trailing slash
    if prefix not in url:
        L.error('ORCiD number in %s field does not have the correct URL prefix. (URL: %s)' % (f, url))
        print('Please ensure the correct URL prefix (%s) preceeds the ORCiD number in field %s' % (ORCID_PREFIX,f))
        exit(1)
    if url[-1] in '/':
        L.error('ORCiD number in %s field has a trailing slash.')
        print('Please remove the trailing slash (/) from the end of the ORCiD number in field %s' % f)
        exit(1)
    return True

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

def orcid_name(orcid, f):
    """
    Ask the user for the name of an orcid number.
    """
    L.info('Asking for name of %s (ORCiD number %s)' % (f, orcid))
    name = input('Please enter the name of %s (ORCiD number %s): ' % (f, orcid))
    L.info('User has entered "%s"' % name)
    return name

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
    names = {}
    L.info('Collecting user input (mnonboard.mnutils.user_input()).')
    for f in FIELDS:
        # the lowest level of the dict/json structure
        if f in 'node':
            for nf in FIELDS[f]:
                # the second level beneath 'node'
                if nf in ['contact_subject']:
                    FIELDS[f][nf][1] = enter_orcid(FIELDS[f][nf][0])
                elif '_name' in nf:
                    names[nf] = input(FIELDS[f][nf][0])
                else:
                    FIELDS[f][nf][1] = input(FIELDS[f][nf][0])
        elif f in ('default_submitter', 'default_owner'):
            FIELDS[f][1] = enter_orcid(FIELDS[f][0])
        elif f in 'num_sitemap_urls':
            FIELDS[f][1] = enter_int(FIELDS[f][0])
        elif '_name' in f:
            names[f] = input(FIELDS[f][0])
        else:
            FIELDS[f][1] = input(FIELDS[f][0])
    # add the sitemap URLs field now that we're done with the loops
    FIELDS['sitemap_urls'] = ['Sitemap URLs: ', {}]
    # pass the number of mn sitemap URLs to sitemap_urls()
    # fx will ask the user to enter the URL(s) and return them as a dict
    # we then store it as the second list item in the 'sitemap_urls' field
    FIELDS['sitemap_urls'][1] = sitemap_urls(FIELDS['num_sitemap_urls'][1])
    return FIELDS, names

def transfer_info(ufields):
    """
    Take a user fields dict and translate it to the default json object.
    """
    fields = json.loads(DEFAULT_JSON)
    L.info('Adding user fields to default fields.')
    for f in ufields:
        if f in 'node':
            for nf in ufields[f]:
                fields[f][nf] = ufields[f][nf]
        fields[f] = ufields[f]
    L.info('Successfully merged. Returning json object.')
    return fields

def input_test(fields):
    """
    Testing the manually filled json file.
    """
    # first, test that there are the fields we need
    L.info('Running mnonboard.mnutils.input_test() on imported json.')
    f = ''
    try:
        # test orcid records
        for f in FILL_FIELDS:
            if f in ['default_submitter', 'default_owner']:
                assert valid_url_prefix(fields[f], ORCID_PREFIX, f)
                assert valid_orcid(fields[f].split('/')[-1])
        f = "'node' -> 'contact_subject'"
        assert valid_url_prefix(fields['node']['contact_subject'], ORCID_PREFIX, f)
        assert valid_orcid(fields['node']['contact_subject'].split('/')[-1])
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
