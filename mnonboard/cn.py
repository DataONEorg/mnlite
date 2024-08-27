import logging
from d1_client.cnclient import CoordinatingNodeClient
from d1_common.types.dataoneTypes import Subject, person
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
