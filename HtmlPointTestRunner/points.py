from inspect import isclass, isfunction
from collections import defaultdict

point_register = {'suite': defaultdict(list), 'test': defaultdict(list)}


def qualifier(test):
    return "%s.%s" % (test.__module__, test.__qualname__)


def save_points(o, point, dst):
    q = qualifier(o)
    dst[q] = point


def point(point):
    def point_wrapper(o):
        if isclass(o):
            save_points(o, point, point_register['suite'])
        elif isfunction(o):
            save_points(o, point, point_register['test'])
        else:
            raise Exception("Expected decorator object '%s' type to be Class or Function but was %s." % (o, type(o)))
        return o

    if not point:
        raise Exception("You need to define at least one max_point in the points decorator declaration")
    try:
        point = int(point)
    except:
        raise Exception("Point argument need to be int compatible")
    return point_wrapper


def _parse_point(test):
    name = _name_test(test)
    testPoints = point_register['test']
    point = testPoints[name]
    key = name[:name.rfind('.')]
    suitePoints = point_register['suite'][key]
    if suitePoints :
        point += suitePoints
    return point


def _name_test(test):
    module = test.__module__
    classname = test.__class__.__name__
    testName = test._testMethodName
    return module + '.' + classname + '.' + testName
