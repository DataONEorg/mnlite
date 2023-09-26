from d1_client.cnclient import CoordinatingNodeClient
from d1_common.types import exceptions
from os import environ

from mnonboard.defs import FIELDS, SITEMAP_URLS, ORCID_PREFIX, SCHEDULES, NODE_ID_PREFIX
from mnonboard import default_json, L
from opersist.utils import JSON_TIME_FORMAT, dtnow
from opersist.cli import getOpersistInstance

D1_AUTH_TOKEN = environ.get('D1_AUTH_TOKEN')

# user info checks
def not_empty(f):
    """
    Test whether a string is empty.

    Args:
        f (str): The string to test.

    Returns:
        (bool): Whether or not the string is empty.
    """
    return f != ''

def req_input(desc):
    """
    Require user input for a given prompt.

    Args:
        desc (str): The prompt to show the user at the input step.

    Returns:
        (str): User input.
    """
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

    Args:
        orcid (str): The orcid number.

    Returns:
        (bool): Whether or not the orcid number passed checks.
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

    Args:
        descrip (str): The prompt to show the user at the base URL input step.

    Returns:
        (str): User input.
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

    Args:
        url (str): The URL to test.
        prefix (str): The URL prefix.
        f (str): The name of the field being tested.

    Returns:
        True (bool): Returns True if the URL passed checks.
    """
    # orcid number will be preceded by a url prefix but no trailing slash
    if prefix not in url:
        L.error('URL in "%s" field does not have the correct prefix. (prefix: %s; URL: %s)' % (f, prefix, url))
        print('Please ensure the correct URL prefix (%s) preceeds URL in field "%s" (currently: %s)' % (ORCID_PREFIX, f, prefix))
        return False
    if url[-1] in '/':
        L.error('URL in "%s" field has a trailing slash.' % (f))
        print('Please remove the trailing slash (/) from the end of URL in field "%s"' % (f))
        return False
    return True

def sitemap_urls(num_urls):
    """
    Collect the sitemap URLs.
    Usually there will be just one of these but we will prepare for more.

    Args:
        num_urls (int): The number of URLs describing the sitemap.

    Returns:
        SITEMAP_URLS (list): The sitemap URLs for the given member node.
    """
    i = 0
    while i < num_urls:
        # add URLs one at a time (should only be a few at most)
        # if we start getting MNs with 10+ sitemap URLs, maybe we change to accept formatted lists from the user
        SITEMAP_URLS.append(req_input("Sitemap URL #%s: " % (i+1)))
        L.info('Sitemap URL #%s: %s' % (i+1, SITEMAP_URLS[i]))
        i += 1
    return SITEMAP_URLS

def enter_schedule():
    """
    Give the user a choice between three basic scheduling options.
    Options are: monthly, daily, and every 3 minutes.

    Returns:
        (int): User-entered integer indicating schedule choice.
    """
    p = 'Select a starting frequency with which to scrape data from this member node.\n' \
        '0: Monthly\n' \
        '1: Daily\n' \
        '2: Hourly\n' \
        '3: Every 3 minutes\n' \
        'Enter 0/1/2/3: '
    while True:
        i = input(p)
        et = 'Please enter a choice of the frequency options above.'
        try:
            if int(i) in SCHEDULES:
                L.info('User has entered frequency option %s.' % i)
                return int(i)
            else:
                L.warning('User entry "%s" is a number but it is not an available option.' % (i))
                print(et)
        except ValueError as e:
                L.warning('User entry "%s" is not an number.' % (i))
                print(et)

def enter_int(prompt):
    """
    Make sure the user enters a number of sitemap URLs of 1 or greater.

    Args:
        prompt (str): The prompt to show the user at the input step.

    Returns:
        (int): User-entered integer indicating number of sitemap URLs.
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

def cn_subj_lookup(subj, cn_url='https://cn.dataone.org/cn', debug=False):
    """
    Use the DataONE API to look up whether a given ORCiD number already exists in the system.

    Args:
        subj (str): The subject to look up.
        cn_url (str): The URL for the DataONE api to send REST searches to (default: 'https://cn.dataone.org/cn').
        debug (bool): Whether to include debug info in log messages (lots of text).

    Returns:
        (str or bool): Received response or False.
    """
    # this authentication method was adapted from:
    # https://github.com/DataONEorg/dataone_examples/blob/master/python_examples/update_object.ipynb
    options = {"headers": {"Authorization": "Bearer %s" % (D1_AUTH_TOKEN)}}
    # Create the Member Node Client
    client = CoordinatingNodeClient(cn_url, **options)
    try:
        # Get records
        L.info('Starting record lookup for %s from %s' % (subj, cn_url))
        subject = client.getSubjectInfo(subj)
        r = subject.content()[0].content()
        name = '%s %s' % (r[1], r[2])
        L.info('Name associated with record %s found in %s: %s.' % (subj, cn_url, name))
        rt = name if not debug else r
        return rt
    except exceptions.NotFound as e:
        estrip = str(e).split('<description>')[1].split('</description>')[0]
        e = e if debug else estrip
        L.info('Caught NotFound error from %s during lookup. Details: %s' % (cn_url, e))
        return False
    except exceptions.NotAuthorized as e:
        L.error('Caught NotAuthorized error from %s. Is your auth token up to date?' % (cn_url))
        exit(1)
    except exceptions.DataONEException as e:
        L.error('Unspecified error from %s:\n%s' % (cn_url, e))
        exit(1)

def local_subj_lookup(subj, name, loc, retn=False):
    """
    Use the local opersist instance to look up a subject.
 
    Args:
        subj (str): Subject id (unique).
        loc (str): Location of the opersist instance.
        name (str): Name of subject.
        retn (bool): Whether to return the record.
    
    Returns:
        (str or False): Returns subject name or False if not found.
    """
    L.info('Looking up %s in sqlite database at %s' % (subj, loc))
    op = getOpersistInstance(loc)
    rec = op.getSubject(subj=subj, name=name, create_if_missing=True)
    op.close()
    if retn:
        rec = rec.asJsonDict()
        L.info('Record: %s' % (rec))
        return rec['name']
    else:
        return

def set_role(loc, title, value):
    """
    Set the subject's role in the opersist database accordingly.
    This should be done before harvest time in order for mnlite to be able to
    populate this information when requested by the web front-end or API.

    :param str loc: The location of the opersist database parent folder
    :param str title: ``default_submitter`` or ``default_owner``
    """
    L.info('Setting %s as "%s" in sqlite database at %s' % (value, title, loc))
    op = getOpersistInstance(loc)
    rec = op.getSubject(subj=value)
    if rec:
        if title in 'default_submitter':
            op.setDefaultSubmitter(value)
        if title in 'default_owner':
            op.setDefaultOwner(value)
    op.close()
    L.info('OPersist record set.')

def orcid_name(orcid, f):
    """
    Ask the user for the name of an orcid number.

    Args:
        orcid (str): Subject orcid number.
        f (str): json field name of inquiry.
    
    Returns:
        (str): Returns user-entered subject name.
    """
    L.info('Asking for name of %s (ORCiD number %s)' % (f, orcid))
    name = req_input('Please enter the name of %s (ORCiD number %s): ' % (f, orcid))
    L.info('User has entered "%s"' % name)
    return name

def enter_orcid(prompt):
    """
    Make sure the user enters a valid orcid number.

    Args:
        prompt (str): Prompt to display at input step.
    
    Returns:
        (str): Returns user-entered orcid number.
    """
    while True:
        # ask the user for an ORCiD number
        o = req_input(prompt)
        o = o.split('orcid.org/')[-1] # returns only number string even if this is not in string
        # make sure user has entered a valid ORCiD number
        if valid_orcid(o):
            return ORCID_PREFIX + o
        else:
            L.warning("Invalid ORCiD number entered: %s" % o)
            print('Please enter a valid ORCiD number (ex: 0000-0000-0000-0000).')

def valid_nodeid(node_id):
    """
    Make sure the node_id contains the correct prefix.

    Args:
        node_id (str): Member node unique id.
    
    Returns:
        (bool): Whether or not the node_id is valid.
    """
    if NODE_ID_PREFIX in node_id:
        # if valid, return
        return True
    else:
        # if invalid, ask user if they meant to do that
        L.warning('Entered node_id does not contain the "%s" prefix. Entry: "%s"' % (NODE_ID_PREFIX, node_id))
        while True:
            # prompt loop
            c = input('node_id usually contains the prefix "%s" but the entered one (%s) does not.\n\
                This could have *serious* downstream consequences!\n\
                Do you wish to modify the node_id entry to fit the standard?\n\
                Please answer "yes" or "no" (yes is default): ' % (NODE_ID_PREFIX, node_id))
            if c.lower() == 'no':
                L.warning('User has chosen to continue with node_id entry of %s' % (node_id))
                return True
            elif (c.lower() == 'yes') or (c.lower() == ''):
                L.info('User has chosen to re-enter node_id. Entry: "%s"' % (c))
                return False
            else:
                L.info('User has entered something other than "yes", "", or "no" and will be prompted again. Entry: "%s"' % (c))
                pass

def enter_nodeid(prompt='Unique node_id: ', id=False):
    """
    Have the user enter a node_id and make sure it contains the correct id prefix.
    Loops until a valid node id is entered.

    Args:
        prompt (str): Prompt to display at input step.
        id (str or bool): The node id from the user's json file or False if none.
    
    Returns:
        (str): Only returns if node id is valid.
    """
    while True:
        L.info('In loop, vars are prompt="%s", id="%s"' % (prompt, id))
        # ask the user for a node id
        if not id:
            print('Please ensure that the node_id is unique from that of all other member nodes!')
            id = req_input(prompt)
        # validate and return
        if valid_nodeid(id):
            return id
        else:
            # loop again
            id = False

def user_input():
    """
    We need a few pieces of information to fill the json fields.
    Collects user input for necessary pieces of node.json information.

    Returns:
        (dict): Dictionary of fields to use for node creation. Will be written to node.json.
    """
    baseurl = ''
    L.info('Collecting user input.')
    for f in FIELDS:
        # the lowest level of the dict/json structure
        if f in 'node':
            for nf in FIELDS[f]:
                # the second level beneath 'node'
                if nf in 'node_id':
                    FIELDS[f][nf][1] = enter_nodeid(prompt=FIELDS[f][nf][0])
                elif nf in ['contact_subject']:
                    FIELDS[f][nf][1] = enter_orcid(FIELDS[f][nf][0])
                elif '_name' in nf:
                    # put the contact subject name in a different dict
                    #names[nf] = req_input(FIELDS[f][nf][0])
                    # postponing this step for later
                    pass
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
            #names[f] = req_input(FIELDS[f][0])
            # postponing this step for later
            pass
        else:
            FIELDS[f][1] = req_input(FIELDS[f][0])
    # add the sitemap URLs field now that we're done with the loops
    FIELDS['spider'] = {}
    FIELDS['spider']['sitemap_urls'] = ['Sitemap URLs: ', []]
    # pass the number of mn sitemap URLs to sitemap_urls()
    # fx will ask the user to enter the URL(s) and return them as a dict
    # we then store it as the second list item in the 'sitemap_urls' field
    FIELDS['spider']['sitemap_urls'][1] = sitemap_urls(FIELDS['num_sitemap_urls'][1])
    return FIELDS

def transfer_info(ufields):
    """
    Take a user fields dict and translate it to the default json object.

    Args:
        ufields (dict): A dict of user-entered fields to be translated.

    Returns:
        (dict): A dict of user-entered fields in proper node.json format.
    """
    fields = default_json(fx='mnonboard.info_chx.transfer_info()')
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

    Args:
        fields (dict): A dict of loaded json fields to test.
    
    Returns:
        (bool): Returns True if all tests pass.
    """
    L.info('Running tests on imported json.')
    # first, test that there are the fields we need
    test_fields = default_json(fx='mnonboard.info_chx.input_test()')
    # test at nest level 1
    f = ''
    try:
        for f in test_fields:
            if fields[f] == '':
                raise ValueError('Value in field "%s" is an empty string.' % (f))
            if f in ['node_id']:
                if valid_url_prefix(fields[f], NODE_ID_PREFIX, f):
                    L.info('%s looks like a valid nodeid')
                    # could test for uniqueness as well?
            if f in ['default_owner', 'default_submitter']:
                # test orcid records while we're here
                if valid_url_prefix(fields[f], ORCID_PREFIX, f):
                    L.info('%s has a valid ORCiD url prefix' % (fields[f]))
                    if valid_orcid(fields[f].split('/')[-1]):
                        L.info('%s is a valid ORCiD URL' % (fields[f]))
                    else:
                        raise ValueError('Invalid ORCiD number "%s" in field %s' % (fields[f], f))
                else:
                    raise ValueError('Invalid value "%s" in field %s (must either be ORCiD number or "urn:node:NODE_NAME")' % (fields[f], f))
    except KeyError as e:
        L.error('No "%s" field found in json.' % f)
        print('Please add the "%s" field to the json you loaded and re-run the script.' % f)
        exit(1)
    except AssertionError as e:
        L.error('Invalid ORCiD number %s in field "%s"' % (fields[f], f))
        print('Please correct the ORCiD number in field "%s"' % (f))
        exit(1)
    except ValueError as e:
        L.error(e)
        print('Please add a supported value in field "%s" and re-run the script.' % (f))
        exit(1)
    # nest level 2
    nf = ''
    try:
        for f in ['node', 'spider']:
            for nf in test_fields[f]:
                if fields[f][nf] == '':
                    raise ValueError('Value in field "%s > %s" is an empty string.' % (f, nf))
                if 'contact_subject' in nf:
                    # test orcid record
                    if not valid_url_prefix(fields[f][nf], ORCID_PREFIX, nf):
                        raise ValueError('Invalid ORCiD URL prefix "%s" in field %s (must be "%s")' % (fields[f][nf], nf, ORCID_PREFIX))
                    if not valid_orcid(fields[f][nf].split('/')[-1]):
                        raise ValueError('Invalid ORCiD URL %s in field "%s > %s"' % (fields[f][nf], f, nf))
                if 'node_id' in nf:
                    # check that the node_id is valid and prompt user to change if it's not
                    fields[f][nf] = enter_nodeid(id=fields[f][nf])
    except KeyError as e:
        L.error('No "%s > %s" field found in json.' % (f, nf))
        print('Please add the "%s > %s" field to the json you loaded and re-run the script.' % (f, nf))
        exit(1)
    except AssertionError as e:
        L.error()
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
