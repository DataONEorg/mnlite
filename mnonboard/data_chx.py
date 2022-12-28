import os
import glob
import random
from pyshacl import validate

from mnonboard import L
from mnonboard.defs import SHACL_URL

def test_mdata(loc, shp_graph=SHACL_URL, format='nquads', num_tests=3):
    """
    Using pyshacl to test harvested metadata.
    """
    L.info('Starting metadata checks. Shape graph: %s' % (shp_graph))
    L.info('Checking %s files.' % num_tests)
    dirlist0, dirlist1, dirlist2 = [], [], []
    file_list = []
    i = 0
    while i < num_tests:
        try:
            for d in os.listdir(loc):
                if os.path.isdir(os.path.join(loc, d)):
                    dirlist0.append(d)
            d0 = random.choice(dirlist0)
            for d in os.listdir(d0):
                if os.path.isdir(os.path.join(d0, d)):
                    dirlist1.append(d)
            d1 = random.choice(dirlist1)
            for d in os.listdir(d1):
                if os.path.isdir(os.path.join(d1, d)):
                    dirlist2.append(d)
            d2 = random.choice(dirlist2)
            L.info('File %s: %s' % (str(i).zfill(3), ))
            f = random.choice(glob.glob(os.path.join(d2, '*.bin')))
            file_list.append(f)
            i += 1
        except Exception as e:
            print("\nError: %s" % e)
            return
    for f in file_list:
        try:
            L.info('Checking file %s/%s: %s' % (i, num_tests, f))
            validate(data_graph=f,
                    shacl_graph=shp_graph,
                    data_graph_format=format,
                    shacl_graph_format='json-ld',
                    )
        except Exception as e:
            L.error('Error running pyshacl: %s' % e)
