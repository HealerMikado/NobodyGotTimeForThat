import sys
from itertools import chain
import json
from unittest import TestLoader

from HtmlTestRunner import HTMLTestRunner

from .point_test_result import PointTestResult
from .points import _parse_point, _name_test


class PointTestRunner(HTMLTestRunner):
    """A test runner for TMC exercises.
    """

    resultclass = PointTestResult

    def __init__(self, max_grade=20, output="./reports/", verbosity=2
                 , stream=sys.stderr, descriptions=True
                 , failfast=False, buffer=False, report_title=None
                 , report_name=None, template=None
                 , resultclass=None, add_timestamp=True
                 , open_in_browser=False
                 , combine_reports=False, template_args=None):

        if not resultclass:
            resultclass = PointTestRunner.resultclass
        else:
            resultclass = resultclass

        self.max_grade = max_grade

        super().__init__(output, verbosity, stream, descriptions
                         , failfast, buffer, report_title, report_name
                         , template, resultclass, add_timestamp
                         , open_in_browser, combine_reports
                         , template_args)

    def run(self, test):
        return super(PointTestRunner, self).run(test)

    def _make_result(self):
        """ Create a TestResult object which will be used to store
        information about the executed tests. """
        return self.resultclass(self.stream, self.descriptions, self.verbosity, self.max_grade)

    def available_points(self):
        testLoader = TestLoader()
        tests = testLoader.discover('.', '*test.py', None)
        try:
            tests = list(chain(*chain(*tests._tests)))
        except Exception as error:
            print("Received following Exception:", error)
            tests.debug()

        points = map(_parse_point, tests)
        names = map(_name_test, tests)

        result = dict(zip(names, points))

        with open('.available_points.json', 'w') as f:
            json.dump(result, f, ensure_ascii=False)


if __name__ == "__main__":
    ptr = PointTestRunner()
    ptr.available_points()
