import logging
from d1_client.cnclient_2_0 import CoordinatingNodeClient_2_0
from d1_common.types.dataoneTypes import Subject, person
from d1_common.types import exceptions
from opersist import OPersist
from opersist.cli import getOpersistInstance
#import d1_admin_tools as d1np
from urllib.parse import quote_plus

from mnonboard.info_chx import local_subj_lookup, orcid_info, set_role
from mnonboard.defs import SUBJECT_PREFIX, SUBJECT_POSTFIX
from . import utils

def init_client(auth_token: str, cn_url: str='https://cn-stage.test.dataone.org/cn'):
    """
    Initialize a d1_client.cnclient.CoordinatingNodeClient_2_0 instance.

    :param str cn_url: The URL of the coordinating node to query (e.g. ``"https://cn-stage.test.dataone.org/cn"``)
    """
    options: dict = {"headers": {"Authorization": "Bearer " + auth_token}}
    return CoordinatingNodeClient_2_0(cn_url, **options)

def get_subjects(client: CoordinatingNodeClient_2_0, orcid: str):
    """
    Return a list of subjects queried from the CN client.

    :param d1_client.cnclient.CoordinatingNodeClient_2_0 client: The client to query
    :param str orcid: ORCiD to search for on the CN
    """
    return client.getSubjectInfo(orcid)

def get_first_subject(client: CoordinatingNodeClient_2_0, orcid: str):
    """
    Return the first subject in the list queried from the CN client.

    :param d1_client.cnclient.CoordinatingNodeClient_2_0 client: The client to use for the query
    :param str orcid: ORCiD to search for on the CN
    """
    try:
        return get_subjects(client=client, orcid=orcid)[0]
    except IndexError:
        return None

def get_subject_name(subject: Subject):
    """
    Get the name of a subject queried from the CN.

    :param d1_common.types.dataoneTypes.Subject subject: The Subject object to get the name from
    """
    first, last = subject.content()[0].content()[1], subject.content()[0].content()[2]
    return "%s %s" % (first, last)

def node_list(client: CoordinatingNodeClient_2_0):
    """
    Get a list of nodes from the CN.

    :param d1_client.cnclient.CoordinatingNodeClient_2_0 client: The CN client to use for the query
    """
    L = logging.getLogger(__name__)
    nodes = client.listNodes()
    nodeids = [node.identifier.value() for node in nodes.content()]
    L.debug(f'Nodes on {client.base_url}: {nodeids}')
    return nodeids

def get_or_create_subj(loc: str, value: str, client: CoordinatingNodeClient_2_0, title: str='unspecified subject', name: str=None):
    """
    Get an existing subject using their ORCiD or create a new one with the
    specified values. 
    Search is conducted first at the given coordinating node URL, then locally.
    If no subject is found, a new record is created in the local opersist
    instance.

    :param str loc: Location of the opersist instance
    :param str value: Subject value (unique subject id, such as orcid or member node id)
    :param str cn_url: The base URL of the rest API with which to search for the given subject
    :param str title: The subject's role in relation to the database
    :param name: Subject name (human readable)
    :type name: str or None
    """
    L = logging.getLogger(__name__)
    if name:
        # we are probably creating a node record
        L.info(f'Creating a node subject. Given node_id: {value}')
        if (not SUBJECT_PREFIX in value) and (not SUBJECT_POSTFIX in value):
            value = f"{SUBJECT_PREFIX}{value}{SUBJECT_POSTFIX}"
        L.info(f'Node subject value: "{value}"')
    else:
        # name was not given. look up the orcid record in the database
        name = cn_subj_lookup(subj=value, client=client)
        if not name:
            # if the name is not in either database, we will create it; else it's already there and we ignore it
            L.info('%s does not exist at %s. Need a name for local record creation...' % (value, client.base_url))
            # ask the user for a name with the associated position and ORCiD record
            name, email = orcid_info(value, title)
            register_user(client=client, orcid=value, name=name, email=email)
    # finally, use opersist to create the subject
    local_subj_lookup(loc=loc, subj=value, name=name)
    # then use opersist to set the subject's role
    if title in ('default_owner', 'default_submitter'):
        set_role(loc=loc, title=title, value=value)
    return name

def cn_subj_lookup(subj, cn_url='https://cn.dataone.org/cn', debug=False, client: CoordinatingNodeClient_2_0=None):
    """
    Use the DataONE API to look up whether a given ORCiD number already exists
    in the system.

    :param str subj: The subject to look up
    :param str cn_url: The URL for the DataONE api to send REST searches to (default: 'https://cn.dataone.org/cn')
    :param bool debug: Whether to include debug info in log messages (lots of text)
    :returns: Received response or False
    :rtype: str or bool
    """
    L = logging.getLogger(__name__)
    if not client:
        # Create the Member Node Client
        client = init_client(cn_url=cn_url, auth_token=D1_AUTH_TOKEN)
    try:
        # Get records
        L.info('Starting record lookup for %s from %s' % (subj, cn_url))
        subject = client.getSubjectInfo(subj)
        client._session.close()
        r = subject.content()
        name = f'{r[0].content()} {r[1].content()}' # first last
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

def register_user(client: CoordinatingNodeClient_2_0, orcid: str, name: str, email: str=None):
    """
    Register a user using the CN client.

    :param d1_client.cnclient.CoordinatingNodeClient_2_0 client: The client to use for the query
    :param str orcid: The subject's ORCiD ID
    :param str name: The name of the subject
    :param str email: The subject's email address
    """
    L = logging.getLogger(__name__)
    s = Subject(orcid)
    p = person()
    p.subject = s
    given, family = utils.parse_name(name)
    p.givenName = given
    p.familyName = family
    if email:
        p.mail = email
    try:
        client.registerAccount(p)
    except Exception as e:
        try:
            err_n = str(e).split('\n')[0]
            err_c = str(e).split('\n')[1]
            err_d = str(e).split('\n')[3]
            print('Error processing %s (%s)\n%s\n%s\n%s' % (name, orcid, err_n, err_c, err_d))
        except:
            print(e)
    
def set_nodes_properties(nodes_properties: dict, con=None):
    """
    :param dict nodes_properties: 
    :param con: 
    """

def set_obsoleted_by(client: CoordinatingNodeClient_2_0, pid: str, obsoleted_by: str):
    """
    Set the obsoletedBy property of a PID on the CN.

    :param d1_client.cnclient.CoordinatingNodeClient_2_0 client: The client to use for the query
    :param str pid: The PID to set the obsoletedBy property for
    :param str obsoleted_by: The PID to set as the obsoletedBy property
    """
    L = logging.getLogger(__name__)
    try:
        return client.setObsoletedBy(pid=pid, obsoletedByPid=obsoleted_by)
    except Exception as e:
        L.error(repr(e))


def get_objects_by_node(client: CoordinatingNodeClient_2_0, node_id: str):
    """
    Get a list of objects by node from the CN.

    :param d1_client.cnclient.CoordinatingNodeClient_2_0 client: The client to use for the query
    :param str node_id: The node ID to get the objects for
    :returns: A list of objects
    :rtype: list
    """
    L = logging.getLogger(__name__)
    objects = []
    while True:
        try:
            l = client.listObjects(nodeId=node_id, start=len(objects), count=1000).content()
            objects.append(l)
            if len(l) < 1000:
                break
        except Exception as e:
            L.error(e)
            break
    if len(objects) > 0:
        return objects


def chain_check(sid, op: OPersist, client: CoordinatingNodeClient_2_0, numstr: str):
    """
    Check the version chain of a SID on the CN.

    If the first OPersist database object in the chain has an ``obsoletes``
    property set to a CN object and the CN object has an ``obsoletedBy`` set
    to that OPersist object, then the chain should be considered intact, and no
    action should be taken on the SID chain in question. No further checks or
    modification of the chain is necessary.

    Any CN objects that originate from the OPersist database should be removed
    from the CN chain, as they are not the part of the chain that needs to be
    modified. Thus any OPersist PIDs that are found in the CN chain should be
    removed from the chain.
    
    If no link exists between the first opersist object and the last chain
    object on the CN, and more than one chain break is found, object
    modification dates should be checked to ensure that the most recently
    modified object is the one receiving the ``obsoletedBy`` value.

    Once we are sure that we can find the latest version of the object in the
    CN, we can set the ``obsoletedBy`` property of the last object in the CN
    chain to the first object with the SID in the OPersist database and the
    ``obsoletes`` property of the first object in the OPersist database to the
    CN object.

    .. note::

        This function is meant to be used in cases where a definitive link between
        old and new version chain objects is not known. In cases where a repository
        provides a version map (CSV or similar) that dictates relationships,
        please use :py:func:`chain_link`.

    :param str sid: The series ID
    :param OPersist op: The OPersist database instance
    :param d1_client.cnclient.CoordinatingNodeClient_2_0 client: The client to use for the CN query
    """
    L = logging.getLogger(__name__)
    L.info(f"({numstr}) {sid} Starting OPersist and getting version chain...")
    first_opersist = op.getThingPIDorFirstSeriesObj(sid)
    if not first_opersist:
        L.error(f"({numstr}) {sid} No OPersist object found with SID {sid}.")
        return
    L.info(f"({numstr}) {sid} Found first OPersist object in the series: {first_opersist.identifier}")
    op_chain = op.getThingsSID(sid)
    L.info(f'({numstr}) {sid} Found {op_chain.count()} series objects in the OPersist database.')
    # get the CN objects
    L.info(f"({numstr}) {sid} Getting CN head object...")
    cn_head_obj = client.getSystemMetadata(sid)
    if not cn_head_obj:
        L.error(f"({numstr}) {sid} No systemMetadata object found.")
        return
    else:
        L.info(f'({numstr}) {sid} Found systemMetadata object: {cn_head_obj.identifier.value()}')
    for obj in op_chain:
        if obj.identifier in cn_head_obj.identifier.value():
            L.info(f'({numstr}) {sid} Found in OPersist database: {obj.identifier}')
            return
    # check if the cn object is in opersist
    if cn_head_obj.obsoletedBy:
        if first_opersist.obsoletes in cn_head_obj.identifier.value():
            if cn_head_obj.obsoletedBy.__str__() == first_opersist.identifier:
                # chain is intact, no action needed
                L.info(f'({numstr}) {sid} Chain is intact.')
                return
            else:
                L.error(f'({numstr}) {sid} Version chain link only goes one way! {cn_head_obj.identifier.value()} is not obsoletedBy {first_opersist.identifier}.')
    else:
        L.info(f'({numstr}) {sid} No link exists between {first_opersist.identifier} and {cn_head_obj.identifier.value()}.')
    # Set the obsoletedBy property of the CN object
    L.info(f'({numstr}) {sid} Attempting repairs...')
    try:
        L.info(f'({numstr}) {sid} Setting obsoletedBy property of {cn_head_obj.identifier.value()} to {first_opersist.identifier}.')
        client.setObsoletedBy(pid=cn_head_obj.identifier.value(),
                              obsoletedByPid=first_opersist.identifier)
    except exceptions.NotAuthorized as e:
        L.error("Received NotAuthorized: %s" % e)
        return
    # Set the obsoletes property of the first OPersist object in the chain
    L.info(f'({numstr}) {sid} Setting obsoletes property of {first_opersist.identifier} to {cn_head_obj.identifier.value()}.')
    op.setObsoletes(sid, cn_head_obj.identifier.value())
    L.info(f'({numstr}) {sid} Done.')
    return True

def chain_link(sid: str, old_id: str, op: OPersist, client: CoordinatingNodeClient_2_0, numstr: str):
    """
    Add an obsoletes relationship to the first object in an OPersist version chain
    where the relationship to the old CN object is known.
    
    :param str sid: The series ID
    :param str old_id: The old CN object ID
    :param OPersist op: The OPersist database instance
    :param d1_client.cnclient.CoordinatingNodeClient_2_0 client: The client to use for the CN query
    :param str numstr: The number of the current operation
    :returns: True if the operation was successful, False otherwise
    :rtype: bool
    """

    L = logging.getLogger(__name__)
    L.info(f"({numstr}) {sid} Getting OPersist version chain...")
    first_opersist = op.getThingPIDorFirstSeriesObj(sid)
    if not first_opersist:
        L.error(f"({numstr}) {sid} No OPersist object found with SID {sid}.")
        return False
    L.info(f"({numstr}) {sid} Found first OPersist object in the series: {first_opersist.identifier}")
    op_chain = op.getThingsSID(sid)
    L.info(f'({numstr}) {sid} Found {op_chain.count()} series objects in the OPersist database.')
    # get the CN objects
    L.info(f"({numstr}) {sid} Getting CN head object...")
    try:
        cn_head_obj = client.getSystemMetadata(old_id)
    except exceptions.NotFound as e:
        L.error(f"({numstr}) {old_id} No systemMetadata found for this PID on the CN.")
        return False
    if cn_head_obj:
        L.info(f'({numstr}) {sid} Found systemMetadata object: {cn_head_obj.identifier.value()}')
    # check if the cn object is in opersist
    if cn_head_obj.obsoletedBy:
        if first_opersist.obsoletes in cn_head_obj.identifier.value():
            if cn_head_obj.obsoletedBy.__str__() == first_opersist.identifier:
                # chain is intact, no action needed
                L.info(f'({numstr}) {sid} Chain is intact.')
                return False
            else:
                L.error(f'({numstr}) {sid} Version chain link only goes one way! {cn_head_obj.identifier.value()} is not obsoletedBy {first_opersist.identifier}.')
    else:
        L.info(f'({numstr}) {sid} No link exists between {first_opersist.identifier} and {cn_head_obj.identifier.value()}.')
    # Set the obsoletedBy property of the CN object
    L.info(f'({numstr}) {sid} Attempting repairs...')
    try:
        L.info(f'({numstr}) {sid} Setting obsoletedBy property of {cn_head_obj.identifier.value()} to {first_opersist.identifier}.')
        client.setObsoletedBy(pid=cn_head_obj.identifier.value(),
                              obsoletedByPid=first_opersist.identifier,
                              serialVersion=cn_head_obj.serialVersion)
    except exceptions.NotAuthorized as e:
        L.error("Received %s" % e)
        return
    # Set the obsoletes property of the first OPersist object in the chain
    L.info(f'({numstr}) {sid} Setting obsoletes property of {first_opersist.identifier} to {cn_head_obj.identifier.value()}.')
    op.setObsoletes(sid, cn_head_obj.identifier.value())
    op_old = op.getThingPIDorFirstSeriesObj(old_id)
    if op_old:
        L.info(f'({numstr}) {sid} Found old OPersist object: {op_old.identifier}')
        L.info(f'({numstr}) {sid} Setting obsoletedBy property of {op_old.identifier} to {sid}.')
        op.setObsoletedBy(old_id, sid)
        L.info(f'({numstr}) {sid} Done.')
    else:
        L.error(f'({numstr}) {sid} No OPersist object found with PID {old_id}.')
    L.info(f'({numstr}) {sid} Done.')
    return True
