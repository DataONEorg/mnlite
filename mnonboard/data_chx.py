import random
from pyshacl import validate
from pyshacl.errors import ShapeLoadError, ConstraintLoadError, \
                           ReportableRuntimeError
from mnonboard import L
from mnonboard.defs import SHACL_URL
from opersist.cli import getOpersistInstance
from opersist.models.thing import Thing
from json.decoder import JSONDecodeError

def test_mdata(loc, shp_graph=SHACL_URL, format='json-ld', num_tests=3):
    """
    Use pyshacl to test harvested metadata.
    """
    L.info('Starting metadata checks. Shape graph: %s' % (shp_graph))
    L.info('Checking %s files.' % num_tests)
    op = getOpersistInstance(loc)
    num_things = op.countThings()
    q = op.getSession().query(Thing) # this might be too inefficient for large sets; may need to change
    i, valid_files, load_errs = 0, 0, 0
    viol_dict = {}
    while i < num_tests:
        record = ''
        violati1, violati2 = 0, 0
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
            conforms, res_graph, res_text = validate(data_graph=record,
                                                    data_graph_format=format,
                                                    shacl_graph=shp_graph,
                                                    shacl_graph_format='turtle',)
            if not conforms:
                violati1 = int(res_text.split('\n')[2].split('(')[1].split(')')[0])
                constraint_viol = ' including Constraint Violation(s)' if 'Constraint Violation' in res_text else ''
                L.error('pyshacl found %s violation(s):\n%s' % (violati1, res_text))
                if (violati1 == 1) and ('<http://schema.org/> not <https://schema.org/>' in res_text):
                    # under this condition there is one constraint violation where the record uses https
                    constraint_viol = ' including https vs http namespace violation'
                    # do a quick replace and test again for lower level violations
                    L.info('Found https vs http namespace violation...replacing and testing again...')
                    record = record.replace('https://schema.org/', 'http://schema.org/')
                    conforms2, res_graph2, res_text2 = validate(data_graph=record,
                                                    data_graph_format=format,
                                                    shacl_graph=shp_graph,
                                                    shacl_graph_format='turtle',)
                    if not conforms2:
                        violati2 = int(res_text2.split('\n')[2].split('(')[1].split(')')[0])
                        L.error('pyshacl found %s additional violation(s):\n%s' \
                                % (violati2, res_text))
                tot_violations = violati1 + violati2
                L.info('Total shacl violations in file: %s' % (tot_violations))
                viol_dict[t.content] = 'shacl violations%s (%s total)' % (constraint_viol, tot_violations, )
            else:
                L.info('No violations found in %s' % (pth))
                viol_dict[t.content] = None
                valid_files += 1
        except ShapeLoadError as e:
            # could be an error with either data or shacl file
            L.error('pyshacl threw ShapeLoadError: %s' % e)
            viol_dict[t.content] = 'ShapeLoadError'
            load_errs += 1
        except ConstraintLoadError as e:
            # I think this is only possible when loading the shacl graph (i.e. w/ constraints)
            L.error('pyshacl threw ConstraintLoadError: %s' % e)
            viol_dict[t.content] = 'ConstraintLoadError'
            load_errs += 1
        except ReportableRuntimeError as e:
            # not exactly sure what this is
            L.error('pyshacl threw ReportableRuntimeError: %s' % e)
            viol_dict[t.content] = 'ReportableRuntimeError'
            load_errs += 1
        except JSONDecodeError as e:
            # malformed json in the json-ld record, this is definitely related to the data graph
            L.error('JSON is malformed, this record cannot be validated. Details:\n%s' % e)
            viol_dict[t.content] = 'JSONDecodeError'
            load_errs += 1
        except FileNotFoundError as e:
            # somehow the file we got from the database does not exist
            L.error('Could not find a file at %s' % (pth))
        except Exception as e:
            # this might have something to do with code in this function
            # if it's a TypeError, it could have to do with the creation of violati1/violati2
            L.error('Error validating record %s' % (pth))
            L.error("Uncaught exception (%s): %s" % (repr(e), e))
            viol_dict[t.content] = repr(e)
            load_errs += 1
        finally:
            L.info('Continuing to next record...')
            i += 1
    L.info('Found %s valid records out of %s checked.' % (valid_files, i))
    L.info('Could not check %s records due to load and/or decode errors.' % (load_errs))
    rep_str = 'Validation report (sha256 - violations or error):\n'
    for v in viol_dict:
        rep_str = rep_str + '%s - %s\n' % (v, viol_dict[v])
    L.info(rep_str)
