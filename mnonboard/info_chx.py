import json
from d1_client.cnclient import CoordinatingNodeClient
from d1_common.types import exceptions
from os import environ

from defs import FIELDS, FILL_FIELDS, SITEMAP_URLS, ORCID_PREFIX, DEFAULT_JSON
from mnonboard import L
from opersist.utils import JSON_TIME_FORMAT, dtnow

D1_AUTH_TOKEN = environ.get('D1_AUTH_TOKEN')

# user info checks
def not_empty(f):
    """
    Test whether a string is empty.
    """
    return f != ''

def req_input(desc):
    while True:
        i = input(desc)
        L.info('User entry for %s"%s"' % (desc, i))
        if not_empty(i):
            return i
        else:
            desc_nocolon = desc.split(':')[0]
            L.warning('Empty string entered.')
            print('Please enter a value for %s.' % desc_nocolon)

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

def base_url(descrip):
    """
    Validate the base URL of the member node. Should include trailing slash.
    """
    while True:
        url = req_input(descrip)
        if url[-1] in '/':
            L.info('Base URL is %s' % url)
            return url
        else:
            L.warning('Base URL must contain a trailing slash. Please try again.')

def valid_url_prefix(url, prefix, f):
    """
    Validate a URL prefix (such as for an ORCiD number).
    """
    # orcid number will be preceded by a url prefix but no trailing slash
    if prefix not in url:
        L.error('ORCiD number in "%s" field does not have the correct URL prefix. (URL: %s)' % (f, url))
        print('Please ensure the correct URL prefix (%s) preceeds the ORCiD number in field "%s"' % (ORCID_PREFIX, f))
        exit(1)
    if url[-1] in '/':
        L.error('ORCiD number in "%s" field has a trailing slash.')
        print('Please remove the trailing slash (/) from the end of the ORCiD number in field "%s"' % f)
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
        # if we start getting MNs with 10+ sitemap URLs, maybe we change to accept formatted lists from the user
        SITEMAP_URLS.append(req_input("Sitemap URL #%s: " % (i+1)))
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

def record_lookup(search, cn_url='https://cn.dataone.org/cn'):
    """
    Use the DataONE API to look up whether a given ORCiD number already exists in the system.
    """
    # this code was adapted from 
    options = {"headers": {"Authorization": "Bearer %s" % (D1_AUTH_TOKEN)}}
    # Create the Member Node Client
    client = CoordinatingNodeClient(cn_url, **options)
    # Set your ORCID
    try:
        # Get records
        L.info('Starting record lookup for %s from %s' % (search, cn_url))
        subject = client.getSubjectInfo(search)
        r = subject.content()[0].content()
        name = '%s %s' % (r[1], r[2])
        L.info('Name associated with record %s found in %s: %s.' % (search, cn_url, name))
        return True
    except exceptions.NotFound as e:
        L.info('Caught NotFound error from %s during lookup: %s' % (cn_url, e))
        L.info('%s does not exist in this database. Will create a record.' % (search))
        return False
    except exceptions.NotAuthorized as e:
        L.error('Caught NotAuthorized error from %s. Is your auth token up to date?' % (cn_url))
        exit(1)
    except exceptions.DataONEException as e:
        L.error('Unspecified error from %s:\n%s' % (cn_url, e))
        exit(1)

def orcid_name(orcid, f):
    """
    Ask the user for the name of an orcid number.
    """
    L.info('Asking for name of %s (ORCiD number %s)' % (f, orcid))
    name = req_input('Please enter the name of %s (ORCiD number %s): ' % (f, orcid))
    L.info('User has entered "%s"' % name)
    return name

def enter_orcid(prompt):
    """
    Make sure the user enters an integer value of 1 or greater.
    """
    while True:
        # ask the user for an ORCiD number
        o = req_input(prompt)
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
    baseurl = ''
    L.info('Collecting user input (mnonboard.mnutils.user_input()).')
    for f in FIELDS:
        # the lowest level of the dict/json structure
        if f in 'node':
            for nf in FIELDS[f]:
                # the second level beneath 'node'
                if nf in ['contact_subject']:
                    FIELDS[f][nf][1] = enter_orcid(FIELDS[f][nf][0])
                elif '_name' in nf:
                    # put the contact subject name in a different dict
                    names[nf] = req_input(FIELDS[f][nf][0])
                elif nf in 'base_url':
                    # get the base url
                    baseurl = base_url(FIELDS[f][nf][0])
                    FIELDS[f][nf][1] = baseurl
                elif nf in 'subject':
                    # set the subject field as the base_url without trailing slash
                    FIELDS[f][nf][1] = baseurl[:-1]
                else:
                    FIELDS[f][nf][1] = req_input(FIELDS[f][nf][0])
        elif f in ('default_submitter', 'default_owner'):
            FIELDS[f][1] = enter_orcid(FIELDS[f][0])
        elif f in 'num_sitemap_urls':
            FIELDS[f][1] = enter_int(FIELDS[f][0])
        elif '_name' in f:
            names[f] = req_input(FIELDS[f][0])
        else:
            FIELDS[f][1] = req_input(FIELDS[f][0])
    # add the sitemap URLs field now that we're done with the loops
    FIELDS['spider'] = {}
    FIELDS['spider']['sitemap_urls'] = ['Sitemap URLs: ', []]
    # pass the number of mn sitemap URLs to sitemap_urls()
    # fx will ask the user to enter the URL(s) and return them as a dict
    # we then store it as the second list item in the 'sitemap_urls' field
    FIELDS['spider']['sitemap_urls'][1] = sitemap_urls(FIELDS['num_sitemap_urls'][1])
    return FIELDS, names

def transfer_info(ufields):
    """
    Take a user fields dict and translate it to the default json object.
    """
    fields = json.loads(DEFAULT_JSON)
    L.info('Adding user fields to default fields.')
    for f in ufields:
        # take fields we want, ignore fields we don't want
        if f in ['node', 'spider']:
            for nf in ufields[f]:
                if '_name' not in nf:
                    fields[f][nf] = ufields[f][nf][1]
        elif ('_name' not in f) and ('num_' not in f):
            fields[f] = ufields[f][1]
    fields['created'] = dtnow().strftime(JSON_TIME_FORMAT)
    L.info('Successfully merged. Returning json object.')
    return fields

def input_test(fields):
    """
    Testing the manually filled json file.
    """
    L.info('Running mnonboard.mnutils.input_test() on imported json.')
    # first, test that there are the fields we need
    test_fields = json.loads(DEFAULT_JSON)
    # test at nest level 1
    f = ''
    try:
        for f in test_fields:
            if fields[f] == '':
                raise ValueError('Value in field "%s" is an empty string.' % (f))
            if f in ['default_owner', 'default_submitter']:
                # test orcid records while we're here
                assert valid_url_prefix(fields[f], ORCID_PREFIX, f)
                assert valid_orcid(fields[f].split('/')[-1])
    except KeyError as e:
        L.error('No "%s" field found in json.' % f)
        print('Please add the "%s" field to the json you loaded and re-run the script.')
        exit(1)
    except AssertionError as e:
        L.error('Invalid ORCiD number %s in field "%s"' % (fields[f], f))
        print('Please correct the ORCiD number in field "%s"' % (f))
        exit(1)
    except ValueError as e:
        L.error(e)
        print('Please add a value in field "%s" and re-run the script.' % (f))
    # nest level 2
    nf = ''
    try:
        for f in ['node', 'spider']:
            for nf in test_fields[f]:
                if fields[f][nf] == '':
                    raise ValueError('Value in field "%s > %s" is an empty string.' % (f, nf))
                if 'contact_subject' in nf:
                    # test orcid record
                    assert valid_url_prefix(fields[f][nf], ORCID_PREFIX, nf)
                    assert valid_orcid(fields[f][nf].split('/')[-1])
    except KeyError as e:
        L.error('No "%s > %s" field found in json.' % (f, nf))
        print('Please add the "%s > %s" field to the json you loaded and re-run the script.' % (f, nf))
        exit(1)
    except AssertionError as e:
        L.error('Invalid ORCiD number %s in field "%s > %s"' % (fields[f][nf], f, nf))
        print('Please correct the ORCiD number in field "%s > %s"' % (f, nf))
        exit(1)
    except ValueError as e:
        L.error(e)
        print('Please add a value in field "%s > %s" and re-run the script.' % (f, nf))
    # nest level 3 (node > schedule fields)
    nnf = ''
    try:
        for nnf in test_fields['node']['schedule']:
            if fields['node']['schedule'][nnf] == '':
                raise ValueError('Value in field "node > schedule > %s" is an empty string.' % (nnf))
    except KeyError as e:
        L.error('No "node > schedule > %s" field found in json.' % (nnf))
        print('Please add the "node > schedule > %s" field to the json you loaded and re-run the script.' % (nnf))
        exit(1)
    except ValueError as e:
        L.error(e)
        print('Please add a value in field "node > schedule > %s" and re-run the script.' % (nnf))
    L.info('Loaded json info has passed checks.')
    return True
