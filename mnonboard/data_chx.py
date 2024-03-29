import random
from pyshacl import validate
from pyshacl.errors import ShapeLoadError, ConstraintLoadError, \
                           ReportableRuntimeError

from mnonboard import L
from mnonboard.defs import SHACL_URL, SHACL_ERRORS
from mnonboard.utils import limit_tests, save_report, ask_continue
from opersist.cli import getOpersistInstance
from opersist.models.thing import Thing
from json.decoder import JSONDecodeError

def violation_extract(viol):
    """
    A function that extracts the name of the violation from
    :py:func:`pyshacl.validate`.

    :param str viol: The result text, third item returned of a pyshacl.validate() run
    :returns: List of violation names found in the res_text
    :rtype: list[str, str, ...]
    """
    lines = ['Source Shape: ']
    end = '\n'
    vx = []
    for line in lines:
        L.info('Checking %ss' % line.split(':')[0])
        if line in viol:
            for seg in viol.split(line)[1:]:
                s = seg.split(end)[0]
                L.debug('Found violation name: %s' % (s))
                vx.append(s)
    if len(vx) > 0:
        L.info('Found violations: %s' % (vx))
        return vx
    else:
        L.warning('Violation name was not extracted. Text block follows:\n%s' % (viol))
        return vx

def violation_cat(hash, viol):
    """
    A function that returns a CSV linestring that contains the severity of a
    passed shacl violation and a comment.

    :param str hash: Path to the metadata file (based on file hash)
    :param str viol: The violation name
    :returns: Comma-separated list of: hash, violation category, violation name, comment
    :rtype: str
    """
    csvl = '%s,%s,%s,%s\n'
    cat, comment = '', ''
    if viol in SHACL_ERRORS['essential']:
        cat = 'ESSENTIAL'
        comment = SHACL_ERRORS['essential'][viol]
    elif viol in SHACL_ERRORS['optional']:
        cat = 'Optional'
        comment = SHACL_ERRORS['optional'][viol]
    elif viol in SHACL_ERRORS['internal']:
        cat = 'Internal'
        comment = SHACL_ERRORS['internal'][viol]
    else:
        cat = 'Not found'
        comment = 'Violation name %s not found in SHACL_ERRORS dictionary! Consult DataONE node admin for information.' % viol
        L.warning(comment)
    hash = hash.split('/')[-1].split('.bin')[0] # split path and file extension from string
    csvl = csvl % (hash, cat, viol, comment)
    L.debug('Violation categorization for %s: %s' % (viol, cat))
    return csvl

def violation_report(viol_dict, loc):
    """
    A function that outputs a report containing information on the violations
    found while shacl testing.

    :param dict viol_dict: Dictionary of violations compiled from this run of metadata checks
    :param str loc: Directory of the opersist instance, where the report file will be written
    """
    L.info('Creating report.')
    L.debug(viol_dict)
    L.info('Violation dictionary length: %s' % (len(viol_dict)))
    rep_str = 'Hash,Violation level,Violation name,Comment\n'
    if len(viol_dict) > 0:
        for hash in viol_dict:
            L.info('Working on hash %s' % (hash.split('/')[-1].split('.bin')[0]))
            i = 0
            while i < len(viol_dict[hash]):
                viol = violation_extract(viol_dict[hash][i][2])
                for v in viol:
                    rep_str = rep_str + violation_cat(hash, v)
                i += 1
        L.info('Report:\n%s' % (rep_str))
    else:
        rep_str = rep_str + ',,,No violations found.\n'
        L.info('No violations.')
    save_report(rep_str=rep_str, loc=loc)

def test_mdata(loc, shp_graph=SHACL_URL, format='json-ld', num_tests=3):
    """
    Use pyshacl to test harvested metadata.

    :param str loc: The base MN folder path in which opersist keeps its data and databases
    :param str shp_graph: Shape graph to be used for testing (defaults to soso v1.2.3)
    :param str format: Format of the data graphs (default: json-ld)
    :param int num_tests: Number of metadata files to test (randomly selected; default=3)
    """
    L.info('Starting metadata checks. Shape graph: %s' % (shp_graph))
    op = getOpersistInstance(loc)
    num_things = op.countThings()
    if (num_tests == 'all') and (num_things >= 500):
        L.warning('User has chosen to shacl test all %s files in the set. Asking to limit...' % num_things)
        # 500 will take about a minute and use a bunch of resources. let's suggest keeping it shorter than that
        num_tests = limit_tests(num_things)
    num_tests = num_things if num_tests == 'all' else num_tests # still might have to test all things if (num_things < 500)
    L.info('Checking %s files.' % num_tests)
    q = op.getSession().query(Thing) # this might be too inefficient for large sets; may need to change
    i, valid_files, load_errs, tot_violations = 0, 0, 0, 0
    viol_dict = {}
    while i < num_tests:
        if i > 0:
            L.info('Continuing to next record...')
        record = ''
        violati1, violati2 = 0, 0
        # get a thing and decode its path
        L.info('Record check %s/%s...' % (i+1, num_tests))
        if num_tests != num_things:
            thing_no = random.randint(0, num_things)
        else:
            thing_no = i
        try:
            t = q[thing_no]
        except IndexError as e:
            msg = 'No records in mnlite database! Aborting checks and registrations.'
            L.error(f'{msg} Details: {e}')
            print(msg)
            exit(1)
        L.info('Selected record number %s of %s in set: %s' % (thing_no, num_things, t.content))
        pth = op.contentAbsPath(t.content)
        # read to object
        L.info('Reading binary from %s' % (pth))
        try:
            with open(pth, 'rb') as f:
                record = f.read().decode('utf-8')
            L.info('Success.')
            L.debug('Record follows:\n%s' % (record))
            conforms, res_graph, res_text = validate(data_graph=record,
                                                    data_graph_format=format,
                                                    shacl_graph=shp_graph,
                                                    shacl_graph_format='turtle',)
            viol_dict[t.content] = {0: [conforms, res_graph, res_text]}
            if not conforms:
                violati1 = int(res_text.split('\n')[2].split('(')[1].split(')')[0])
                constraint_viol = ' including Constraint Violations' if 'Constraint Violation' in res_text else ''
                L.warning('pyshacl found %s violations.' % (violati1))
                L.debug('Details:\n%s' % (res_text))
                if (violati1 == 1) and ('<http://schema.org/> not <https://schema.org/>' in res_text):
                    # under this condition there is one constraint violation where the record uses https
                    constraint_viol = ' including https vs http namespace violation'
                    # do a quick replace and test again for lower level violations
                    L.debug('Found https vs http namespace violation...replacing and testing again...')
                    record = record.replace('https://schema.org/', 'http://schema.org/')
                    conforms2, res_graph2, res_text2 = validate(data_graph=record,
                                                    data_graph_format=format,
                                                    shacl_graph=shp_graph,
                                                    shacl_graph_format='turtle',)
                    viol_dict[t.content][1] = [conforms2, res_graph2, res_text2]
                    if not conforms2:
                        violati2 = int(res_text2.split('\n')[2].split('(')[1].split(')')[0])
                        L.warning('pyshacl found %s additional violations after correcting for https/http violation.' % (violati2))
                        L.debug('Details:\n%s' % (res_text2))
                    else:
                        L.info('Namespace https/http constraint violation is the only error found')
                tot_violations = violati1 + violati2
                L.info('Total shacl violations in file: %s' % (tot_violations))
            else:
                L.info('No violations found in %s' % (pth))
                viol_dict[t.content] = {0: [True, None, 'No violations.']}
                valid_files += 1
        except ShapeLoadError as e:
            # could be an error with either data or shacl file
            L.error('pyshacl threw ShapeLoadError: %s' % e)
            viol_dict[t.content] = {0: [False, None, 'ShapeLoadError: %s' % e]}
            load_errs += 1
        except ConstraintLoadError as e:
            # I think this is only possible when loading the shacl graph (i.e. w/ constraints)
            L.error('pyshacl threw ConstraintLoadError: %s' % e)
            viol_dict[t.content] = {0: [False, None, 'ConstraintLoadError']}
            load_errs += 1
        except ReportableRuntimeError as e:
            # not exactly sure what this is
            L.error('pyshacl threw ReportableRuntimeError: %s' % e)
            viol_dict[t.content] = {0: [False, None, 'ReportableRuntimeError']}
            load_errs += 1
        except JSONDecodeError as e:
            # malformed json in the json-ld record, this is definitely related to the data graph
            L.error('JSON is malformed, this record cannot be validated. Details:\n%s' % e)
            viol_dict[t.content] = {0: [False, None, 'JSONDecodeError']}
            load_errs += 1
        except FileNotFoundError as e:
            # somehow the file we got from the database does not exist
            L.error('Could not find a file at %s' % (pth))
            viol_dict[t.content] = {0: [False, None, 'FileNotFoundError']}
            load_errs += 1
        except Exception as e:
            # this might have something to do with code in this function
            # if it's a TypeError, it could have to do with the creation of violati1/violati2
            L.error('Error validating record %s' % (pth))
            L.error('Uncaught exception (%s): %s' % (repr(e), e))
            viol_dict[t.content] = {0: [False, None, repr(e)]}
            load_errs += 1
        finally:
            i += 1
    L.info('Found %s valid records out of %s checked.' % (valid_files, i))
    L.info('%s failures due to load and/or decode errors.' % (load_errs))
    violation_report(viol_dict, loc)
    # close the opersist instance
    op.close()
    msg = f"{valid_files} fully valid records found (out of {i} checked; with {load_errs} load/decode errors). Continue?"
    ask_continue(msg)
