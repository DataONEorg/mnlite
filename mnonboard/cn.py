import logging
from d1_client.cnclient import CoordinatingNodeClient
from d1_common.types.dataoneTypes import Subject, person
from opersist import OPersist
from opersist.cli import getOpersistInstance
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

def get_cn_version_chain(cn_client, sid):
    """
    Get the objects in the version chain on the CN with the given Series ID.
    
    Parameters:
    cn_client (CoordinatingNodeClient): The CN client to use for querying.
    sid (str): The Series ID to search for.
    
    Returns:
    list: A list of objects in the version chain with the given Series ID.
    """
    version_chain = []
    try:
        # Query the CN for objects with the given Series ID
        object_list = cn_client.listObjects(seriesId=sid, start=0, count=1000)
        for obj_info in object_list.objectInfo:
            version_chain.append(obj_info)
        if len(object_list.objectInfo) == 1000:
            # If there are more objects to query, continue until all objects are retrieved
            while True:
                object_list = cn_client.listObjects(seriesId=sid, start=len(version_chain), count=1000)
                for obj_info in object_list.objectInfo:
                    version_chain.append(obj_info)
                if len(object_list.objectInfo) < 1000:
                    break
    except Exception as e:
        print(f"Error querying CN: {e}")
    return version_chain

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

def chain_check(sid, loc, client: CoordinatingNodeClient):
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

    :param list objects: The list of objects to search
    :param str pid: The PID to check the version chain for
    :param opersist.OPersist op: The OPersist instance to check for the obsoletedBy PID
    """
    L = logging.getLogger(__name__)
    if not cn_chain:
        return
    L.info(f"{sid} Starting OPersist and getting version chain...")
    op: OPersist = getOpersistInstance(loc)
    first_opersist = op.getThingPIDorFirstSeriesObj(sid)
    op_chain = op.getThingsSID(sid)
    L.debug(f'{sid} Found {len(op_chain)} version chain objects in the OPersist database.')
    # get the CN objects in the version chain
    L.debug(f"{sid} Getting CN version chain and filtering out OPersist objects...")
    cn_chain = get_cn_version_chain(client, sid)
    tot_cn = len(cn_chain)
    cn_chain = [obj for obj in cn_chain if obj.identifier.value() not in [o.identifier for o in op_chain]]
    L.debug(f'{sid} Found {len(cn_chain)} CN objects. ' +
           f'Removed {tot_cn - len(cn_chain)} objects that originate from OPersist.')
    latest_cn = max(cn_chain, key=lambda x: x.modification_date)
    L.debug(f'Latest object in the CN chain: {latest_cn.identifier}')
    # check if the first OPersist object has an obsoletes property set to a CN object
    if hasattr(first_opersist, 'obsoletes') and first_opersist.obsoletes in cn_chain:
        if hasattr(latest_cn, 'obsoletedBy') and latest_cn.obsoletedBy.value() == first_opersist.identifier:
            # chain is intact, no action needed
            L.info(f'{sid} Chain is intact.')
            return True
        else:
            L.error(f'{sid} Link only goes one way! {latest_cn.identifier.value()} is not obsoletedBy {first_opersist.identifier}.')
    else:
        L.info(f'{sid} No link exists between {first_opersist.identifier} and {latest_cn.identifier.value()}.')
    # check for chain breaks and modification dates
    chain_breaks = 0
    for obj in cn_chain:
        if not hasattr(obj, 'obsoletedBy') or obj.obsoletedBy not in cn_chain:
            chain_breaks += 1
    L.info(f'Found {chain_breaks} chain breaks in the CN chain.')
    if chain_breaks > 1:
        # Ensure obsoletedBy is not set on the latest CN object
        if hasattr(latest_cn, 'obsoletedBy') and obj.obsoletedBy != first_opersist.identifier:
            # Invalid chain, handle accordingly
            return False            
    # Set the obsoletedBy property of the last CN object in the chain
    try:
        client.setObsoletedBy(latest_cn.identifier.value(), first_opersist.identifier)
        cn_chain[-1].obsoletedBy = first_opersist.identifier
    except Exception as e:
        L.error(repr(e))
        return
    # Set the obsoletes property of the first OPersist object in the chain
    first_opersist = op.getThingPIDorFirstSeriesObj(first_opersist)
    first_opersist.obsoletes = latest_cn
    op.commit()
    op.close()
    return True