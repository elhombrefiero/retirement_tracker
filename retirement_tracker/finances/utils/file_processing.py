
from datetime import datetime
from pypdf import PdfReader
import logging
import re

logger = logging.getLogger(__name__)


def process_user_work_file(user_work_file):
    """ Reads in a user pay stub.
        Processes:
            earnings,
            deductions, and
            taxes.
        Returns a dictionary with the information, which can then be fed into another view. """

    pay_date_regex = re.compile(r'Pay Date ([0-9]{2}/[0-9]{2}/[0-9]{4})')

    return_dict = dict()

    pdf_obj = PdfReader(user_work_file)
    page = pdf_obj.pages[0]
    split_page = page.extract_text().split('\n')

    for i, line in enumerate(split_page):
        pay_date_match = pay_date_regex.match(line)
        if pay_date_match:
            pay_date = pay_date_match.group(1)
            pay_datetime = datetime.strptime(pay_date, '%m/%d/%Y')  # TODO: Apply the time zone
            print(f'Found Pay date: {pay_datetime}')
            continue
        if 'Earnings' in line:
            # Pay type, hours, pay rate, current, ytd

            # Go through the following earnings lines and pull the Current values
            pass

        if 'Deductions' in line:
            # Deduction, Pre-Tax, Employee Current, Employee YTD, Employer Current, Employer YTD
            pass

        if 'Taxes' in line:
            # Tax, Current, YTD
            pass

        if 'Net Pay Distribution' in line:
            # Grab the data used to transfer to the Savings account
            pass


        print(line)

    # Earnings

    # Deductions

    # Taxes

    return return_dict
