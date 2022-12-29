import random
from pyshacl import validate

from mnonboard import L
from mnonboard.defs import SHACL_URL
from opersist.cli import getOpersistInstance
from opersist.models.thing import Thing


def test_mdata(loc, shp_graph=SHACL_URL, format='json-ld', num_tests=3):
    """
    Use pyshacl to test harvested metadata.
    """
    L.info('Starting metadata checks. Shape graph: %s' % (shp_graph))
    L.info('Checking %s files.' % num_tests)
    op = getOpersistInstance(loc)
    num_things = op.countThings()
    q = op.getSession().query(Thing) # this might be too inefficient for large sets; may need to change
    i = 0
    while i < num_tests:
        record = ''
        # get a random thing and decode its path
        L.info('Record check %s/%s...' % (i+1, num_tests))
        rand = random.randint(0, num_things)
        t = q[rand]
        L.info('Selected record number %s of %s in set: %s' % (rand, num_things, t.content))
        pth = op.contentAbsPath(t.content)
        # read to object
        L.info('Reading binary from %s' % (pth))
        try:
            with open(pth, 'rb') as f:
                record = f.read().decode('utf-8')
            L.info('Success; record follows:\n%s' % (record))
        except Exception as e:
            L.error("\nError: %s" % e)
            L.error('Error loading record %s\nSkipping to next record...' % (pth))
            continue
        try:
            conforms, res_graph, res_text = validate(data_graph=record,
                                                    data_graph_format=format,
                                                    shacl_graph=shp_graph,
                                                    shacl_graph_format='turtle',)
            if not conforms:
                num_violations = res_text.split('\n')[2].split('(')[1].split(')')[0]
                L.error('pyshacl found %s violation(s):\n%s' % (num_violations, res_text))
            else:
                L.info('No violations found in %s' % (pth))
        except Exception as e:
            # add pyshacl exceptions; perhaps consolidate try/excepts here?
            L.error('Error running pyshacl: %s' % e)
        
        i += 1
