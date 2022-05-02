import importlib
import logging
import os
import shutil
import smtplib
import unittest
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .point_test_runner import PointTestRunner

WORKING_FOLDER = "work"


class CorrectionOrchestrator:

    def __init__(self, input_folder: str, exercise_name: str
                 , exercise_correction: str
                 , sending_email: str, output_dir: str = "out"
                 , report_title: str = "Report"
                 , smtp_server: smtplib.SMTP = None
                 , mime_object: MIMEMultipart = None):
        self.exercise_correction = exercise_correction
        self.exercise_name = exercise_name
        self.input_folder = input_folder
        self.student_code = None
        self.sending_email = sending_email
        self.output_dir = output_dir
        self.report_title = report_title
        self.mime_object = mime_object
        if smtp_server:
            self.smtp_server = smtp_server

    def run_corrections(self) -> None:
        """
        Run the correction over all the student file
        """
        # Create working folder
        os.makedirs(WORKING_FOLDER, exist_ok=True)

        # Copy correction
        shutil.copyfile(self.exercise_correction
                        , f'{WORKING_FOLDER}/{self.exercise_correction}')

        logging.debug(f'Student code to process : {os.listdir(self.input_folder)}')
        for student_folder in os.listdir(self.input_folder):
            logging.info(f'Run student {student_folder}')
            # Copy student file
            shutil.copyfile(
                f'{self.input_folder}/{student_folder}/{self.exercise_name}'
                , f'{WORKING_FOLDER}/{self.exercise_name}')
            self.run_one_file()
            self.clear_workspace()
        shutil.rmtree(WORKING_FOLDER, ignore_errors=True)


    def clear_workspace(self):
        """
        Remove the student file and the __pycache__folder to the run
        the next correction in a clean folder.
        """
        os.remove(f'{WORKING_FOLDER}/{self.exercise_name}')
        shutil.rmtree(f'{WORKING_FOLDER}/__pycache__', ignore_errors=True)

    def run_one_file(self):
        """
        Run one correction
        """
        self.import_student_file()

        logging.info(f'{WORKING_FOLDER}.{self.exercise_correction.split(".")[0]}')
        test_code = importlib.import_module(f'{WORKING_FOLDER}.{self.exercise_correction.split(".")[0]}')
        # Some useful variable for the report.
        # TODO find a better way
        template_args = {
            "id": self.student_code.ID,
            "mail": self.student_code.MAIL
        }
        try:
            unittest.main(module=test_code,
                          testRunner=PointTestRunner(
                              output=self.output_dir
                              , report_title=self.report_title
                              , report_name=f"Report_Student_{self.student_code.ID}"
                              , combine_reports=True
                              , template='report_template.html'
                              , template_args=template_args),
                          exit=False)
        except Exception as e:
            logging.error(f"Error in processing student {self.student_code.ID}.")
            logging.exception(e)
        if self.smtp_server :
            self.send_mail(self.student_code.MAIL)
            logging.info(f'End processing file for student {self.student_code.ID}')

    def import_student_file(self):
        """
        Import the student file as a module to make it usable by the test class.
        There are two cases :
            - The module is imported for the first time. Use the import_module function
            - The module has been already imported by a previous correction. Use the reload function
        """
        if not self.student_code:
            self.student_code = importlib.import_module(
                f'{WORKING_FOLDER}.{self.exercise_name.split(".")[0]}'
            )
            logging.info(f'Loading module {WORKING_FOLDER}.{self.exercise_name.split(".")[0]}')
        else:
            self.student_code = importlib.reload(self.student_code)
            logging.info(f'Reloading module {WORKING_FOLDER}.{self.exercise_name.split(".")[0]}')

    def send_mail(self, student_email: str):
        """
        Send a mail with the report to a student
        :param student_email: the student email
        :type student_email: str
        """
        if not self.mime_object:
            self.generate_default_MIME()

        self.mime_object['From'] = self.sending_email
        self.mime_object = student_email

        self.attach_file_to_mail()

        self.mime_object.attach(MIMEText(self.mail_body
                                         , f'You will find in attachment your result at exercise {self.exercise_name}'
               f'<\\br> This is an automatic message.'))

        try:
            self.smtp_server.sendmail(self.sending_email, student_email, self.mime_object.as_string())
            logging.info(f"Successfully sent email to {student_email}")

        except smtplib.SMTPException as e:
            logging.exception(e)
            logging.info(f"Unable to send email to {student_email}")


    def attach_file_to_mail(self) -> None:
        """
        Attach the report to the email
        """
        part = MIMEBase('application', "octet-stream")
        # Because the report is timestamp, we cannot just get the file
        with open(f"{self.output_dir}/Report_Student_{self.student_code.ID}", 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header(f'Content-Disposition',
                        f'attachment; filename=Report_Student_{self.student_code.ID}')
        self.mime_object.attach(part)

    def generate_default_MIME(self) -> None:
        """
        Generate a default MIME object
        """
        self.mime_object = MIMEMultipart()
        self.mime_object['Subject'] = f'Automatic correction {self.exercise_name}'
