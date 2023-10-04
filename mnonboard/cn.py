from os import environ
from d1_client.cnclient import CoordinatingNodeClient
from d1_common.types.dataoneTypes import Subject, person
#import d1_admin_tools as d1np

from . import defs

def init_client(cn_url: str, auth_token: str):
    """
    Initialize a d1_client.cnclient.CoordinatingNodeClient instance.

    :param str cn_url: The URL 
    """
    options: dict = {"headers": {"Authorization": "Bearer " + auth_token}}
    return CoordinatingNodeClient(cn_url, **options)

def get_subjects(client: CoordinatingNodeClient, orcid: str):
    """
    """
    return client.getSubjectInfo(orcid)

def get_first_subject(client: CoordinatingNodeClient, orcid: str):
    """
    """
    try:
        return get_subjects(client=client, orcid=orcid)[0]
    except IndexError:
        return None

def get_subject_name(subject: Subject):
    """
    """
    first, last = subject.content()[0].content()[1], subject.content()[0].content()[2]
    return "%s %s" % (first, last)

def node_list(client: CoordinatingNodeClient):
    """
    """
    nodes = client.listNodes()
    for node in nodes.content():
        print(node.name)
    return nodes

def register_user(client: CoordinatingNodeClient, orcid: str, name: str, email: str=None):
    """
    """
    
def set_nodes_properties(nodes_properties: dict, con=None):
    """
    """
