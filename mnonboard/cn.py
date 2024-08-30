import logging
from d1_client.cnclient import CoordinatingNodeClient
from d1_common.types.dataoneTypes import Subject, person
from opersist import OPersist
#import d1_admin_tools as d1np

from . import defs, utils

def init_client(cn_url: str, auth_token: str):
    """
    Initialize a d1_client.cnclient.CoordinatingNodeClient instance.

    :param str cn_url: The URL of the coordinating node to query (e.g. ``"https://cn-stage.test.dataone.org/cn"``)
    """
    options: dict = {"headers": {"Authorization": "Bearer " + auth_token}}
    return CoordinatingNodeClient(cn_url, **options)

def get_subjects(client: CoordinatingNodeClient, orcid: str):
    """
    Return a list of subjects queried from the CN client.

    :param d1_client.cnclient.CoordinatingNodeClient client: The client to query
    :param str orcid: ORCiD to search for on the CN
    """
    return client.getSubjectInfo(orcid)

def get_first_subject(client: CoordinatingNodeClient, orcid: str):
    """
    Return the first subject in the list queried from the CN client.

    :param d1_client.cnclient.CoordinatingNodeClient client: The client to use for the query
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

def node_list(client: CoordinatingNodeClient):
    """
    Get a list of nodes from the CN.

    :param d1_client.cnclient.CoordinatingNodeClient client: The CN client to use for the query
    """
    nodes = client.listNodes()
    for node in nodes.content():
        print(node.name)
    return nodes

def register_user(client: CoordinatingNodeClient, orcid: str, name: str, email: str=None):
    """
    Register a user using the CN client.

    :param d1_client.cnclient.CoordinatingNodeClient client: The client to use for the query
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

def set_obsoleted_by(client: CoordinatingNodeClient, pid: str, obsoleted_by: str):
    """
    Set the obsoletedBy property of a PID on the CN.

    :param d1_client.cnclient.CoordinatingNodeClient client: The client to use for the query
    :param str pid: The PID to set the obsoletedBy property for
    :param str obsoleted_by: The PID to set as the obsoletedBy property
    """
    L = logging.getLogger(__name__)
    try:
        return client.setObsoletedBy(pid=pid, obsoletedByPid=obsoleted_by)
    except Exception as e:
        L.error(repr(e))

def get_objects_by_node(client: CoordinatingNodeClient, node_id: str):
    """
    Get a list of objects by node from the CN.

    :param d1_client.cnclient.CoordinatingNodeClient client: The client to use for the query
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

def get_last_object_in_series(objects: list, series_id: str):
    """
    Get the last object in a series from the CN.

    Assumes the version chain is intact.

    :param list objects: The list of objects to search
    :param str series_id: The series ID
    """
    if objects:
        for obj in objects:
            if obj.seriesId == series_id:
                if obj.obsoletedBy:
                    continue
                else:
                    return obj.identifier

def chain_check(objects: list, sid: str, op: OPersist):
    """
    Check the version chain of a SID on the CN.
    If

    :param list objects: The list of objects to search
    :param str pid: The PID to check the version chain for
    """
    L = logging.getLogger(__name__)
    chain = []
    for obj in objects:
        if obj.seriesId == sid:
            chain.append(obj)
    brk = False
    L.info(f'{sid} checking {len(chain)} objects in version chain')
    if len(chain) > 0:
        pids = [x.identifier for x in chain]
        for i in range(len(chain)):
            if chain[i].obsoletedBy:
                if chain[i].obsoletedBy in pids:
                    continue
                else:
                    L.info('CN version chain broken at %s' % chain[i].identifier)
                    # check if the obsoletedBy pid is in the OPersist instance
                    thing = op.getThing(chain[i].obsoletedBy)
                    if thing:
                        L.info(f'CN object {chain[i].obsoletedBy} is obsoletedBy OPersist object {thing}')
                    else:
                        L.error(f'OPersist object {chain[i].obsoletedBy} not found!')
            else:
                L.info(f'{sid} version chain broken at {chain[i].identifier}')
                if brk:
                    L.error(f'{sid} version chain broken again at {chain[i].identifier}')
                else:
                    brk = True

