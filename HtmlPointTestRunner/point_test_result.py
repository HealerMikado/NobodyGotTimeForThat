import csv
import logging
import os
import traceback

from HtmlTestRunner.result import HtmlTestResult, render_html, strip_module_names
from jinja2 import Template

from .point_test_result_info import PointTestResultInfo
from .points import _parse_point, _name_test

results = []
DEFAULT_TEMPLATE = os.path.join(os.path.dirname(__file__), "template", "template/report_template.html")


def load_template(template):
    """ Try to read a file from a given path, if file
        does not exist, load default one. """
    file = None
    try:
        if template:
            with open(template, "r", encoding="utf-8") as f:
                file = f.read()
    except Exception as err:
        print("Error: Your Template wasn't loaded", err,
              "Loading Default Template", sep="\n")
    finally:
        if not file:
            with open(DEFAULT_TEMPLATE, "r", encoding="utf-8") as f:
                file = f.read()
        return file


def render_html(template, **kwargs):
    template_file = load_template(template)
    if template_file:
        template = Template(template_file)
        return template.render(**kwargs)


class PointTestResult(HtmlTestResult):
    SUCCESS, FAILURE, ERROR, SKIP = "Success", "Failure", "Error", "Skip"

    def __init__(self, stream, descriptions, verbosity, max_grade):
        super().__init__(stream, descriptions, verbosity)
        self.infoclass = PointTestResultInfo
        self._results = []
        self.max_grade = max_grade

    def addSuccess(self, test):
        super(PointTestResult, self).addSuccess(test)
        self.addResult(test, PointTestResult.SUCCESS)

    def addFailure(self, test, err):
        super(PointTestResult, self).addFailure(test, err)
        testinfo = self.infoclass(self, test, self.infoclass.FAILURE, err)
        self.addResult(test, PointTestResult.FAILURE, err)

    def addError(self, test, err):
        super(PointTestResult, self).addError(test, err)
        self.addResult(test, PointTestResult.ERROR, err)

    def addResult(self, test, status, err=None):
        points = _parse_point(test)
        message = ""
        backtrace = []
        if err is not None:
            message = str(err[1])
            backtrace = traceback.format_tb(err[2])

        details = {
            'name': _name_test(test),
            'status': status,
            'message': message,
            'passed': status == 'passed',
            'points': points,
            'backtrace': backtrace
        }
        self._results.append(details)

    def compute_grade(self, all_results):
        grade, max_grade = 0, 0
        for test_case_class_name, test_case_tests in all_results.items():
            for test in test_case_tests:
                max_grade += test.max_point
                grade += test.get_point()

        coef = self.max_grade / max_grade
        return grade, round(grade * coef, 1), max_grade, coef

    def generate_reports(self, testRunner):
        """ Generate report(s) for all given test cases that have been run. """

        status_tags = ('success', 'danger', 'warning', 'info')
        all_results = self._get_info_by_testcase()
        summaries = self._get_report_summaries(all_results, testRunner)
        raw_grade, round_grade, max_raw_grade, coef = self.compute_grade(all_results)
        self.generate_html_report(all_results, max_raw_grade, raw_grade, round_grade, status_tags, summaries,
                                  testRunner)
        self.generate_csv_report(all_results, round_grade,raw_grade,  testRunner)


    def generate_html_report(self, all_results, max_raw_grade, raw_grade, round_grade, status_tags, summaries,
                             testRunner):
        if not testRunner.combine_reports:
            for test_case_class_name, test_case_tests in all_results.items():
                header_info = self._get_header_info(test_case_tests, testRunner.start_time)
                html_file = self.generate_html_content(
                    all_results
                    , header_info
                    , max_raw_grade
                    , raw_grade
                    , round_grade
                    , status_tags
                    , summaries
                    , testRunner)
                # append test case name if multiple reports to be generated
                if testRunner.report_name is None:
                    report_name_body = self.default_prefix + test_case_class_name
                else:
                    report_name_body = "{}_{}".format(testRunner.report_name, test_case_class_name)
                self.generate_file(testRunner, report_name_body, html_file)

        else:
            header_info = self._get_header_info(
                [item for sublist in all_results.values() for item in sublist],
                testRunner.start_time
            )
            html_file = self.generate_html_content(
                all_results
                , header_info
                , max_raw_grade
                , raw_grade
                , round_grade
                , status_tags
                , summaries
                , testRunner)
            # if available, use user report name
            if testRunner.report_name is not None:
                report_name_body = testRunner.report_name
            else:
                report_name_body = self.default_prefix + "_".join(strip_module_names(list(all_results.keys())))
            self.generate_file(testRunner, report_name_body, html_file)

    def generate_html_content(
            self, all_results, header_info, max_raw_grade, raw_grade
            , round_grade, status_tags, summaries, testRunner):
        html_file = render_html(
            testRunner.template,
            title=testRunner.report_title,
            header_info=header_info,
            all_results=all_results,
            results=results,
            status_tags=status_tags,
            summaries=summaries,
            grade=round_grade,
            raw_grade=raw_grade,
            max_raw_grade=max_raw_grade,
            max_grade=self.max_grade,
            **testRunner.template_args
        )
        return html_file

    def generate_csv_report(self, all_results,round_grade,raw_grade,  testRunner):
        logging.info(f'Generating csv report...')

        dir_to = testRunner.output
        if not os.path.exists(dir_to):
            os.makedirs(dir_to)
        report_name = f"rapport.csv"
        path_file = os.path.abspath(os.path.join(dir_to, report_name))

        if not os.path.exists(path_file):
            # The file do not exist, need to write some headers
            with open(path_file, 'w', encoding="utf-8", newline='') as report_file:
                writer = csv.writer(report_file)
                headers = ["id", "mail", "raw_grade", "note"]
                for test_case_class_name, test_case_tests in all_results.items():
                    for test in test_case_tests:
                        headers.append(test.test_id.split(".")[-1])
                writer.writerow(headers)
        # Add a new line
        with open(path_file, 'a', encoding="utf-8", newline='') as report_file:
            writer = csv.writer(report_file)
            row = [testRunner.template_args["id"], testRunner.template_args["mail"], round_grade, raw_grade]
            for test_case_class_name, test_case_tests in all_results.items():
                for test in test_case_tests:
                    row.append(test.get_point())
            writer.writerow(row)
        logging.info(f'Report generate : {path_file}')


    def generate_file(self, testRunner, report_name, report):
        """ Generate the report file in the given path. """
        dir_to = testRunner.output
        if not os.path.exists(dir_to):
            os.makedirs(dir_to)

        if testRunner.timestamp:
            report_name += "_" + testRunner.timestamp
        report_name += ".html"

        path_file = os.path.abspath(os.path.join(dir_to, report_name))
        self.stream.writeln(os.path.relpath(path_file))
        self.report_files.append(path_file)
        with open(path_file, 'w', encoding="utf-8") as report_file:
            report_file.write(report)
