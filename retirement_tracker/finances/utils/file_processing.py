from datetime import datetime
from pypdf import PdfReader
import logging
import re

from django.utils.timezone import get_current_timezone

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
    cur_tz = get_current_timezone()

    for i, line in enumerate(split_page):
        pay_date_match = pay_date_regex.match(line)
        if pay_date_match:
            pay_date = pay_date_match.group(1)
            pay_datetime = datetime.strptime(pay_date, '%m/%d/%Y')
            pay_datetime = pay_datetime.replace(tzinfo=cur_tz)
            return_dict['pay_date'] = pay_datetime
            continue
        if 'Earnings' in line:
            process_earnings(i + 2, split_page, return_dict)

        if 'Deductions' in line:
            process_deductions(i + 2, split_page, return_dict)

        if 'Taxes' == line.strip():
            # Tax, Current, YTD
            process_taxes(i + 2, split_page, return_dict)

        if 'Net Pay Distribution' in line:
            # Grab the data used to transfer to the Savings account
            process_checking_split(i+2, split_page, return_dict)

    return return_dict


def process_checking_split(i, split_lines, return_dict):
    """ Determines what amount of pay should be transferred from checking to savings account"""

    re_checking = re.compile(r'^[x\d]+\s+(?:Checking)\s+\$([\d\.,]+)', re.IGNORECASE)
    re_savings = re.compile(r'^[x\d]+\s+(?:Savings)\s+\$([\d\.,]+)', re.IGNORECASE)

    num_savings = 0
    for line in split_lines[i:]:
        match1 = re_checking.match(line)
        if match1:
            continue
        match2 = re_savings.match(line)
        if match2:
            amount = massage_float(match2.group(1))
            if 'transfer' not in return_dict.keys():
                return_dict['transfer'] = amount
            num_savings += 1
            continue
        if num_savings > 1:
            logger.warning(f'There are multiple savings accounts. Fraction of savings will not be calculated correctly.')
        return


def process_earnings(i, split_lines, return_dict):
    """ Processes earnings portion of the input file."""
    # Pay type, hours, pay rate, current, ytd
    re_earnings1 = re.compile(r'(^.*)\s[\d\.]+\s+[$\d\.,]+\s+\$([\d\.,]+)\s+[$\d\.,]+',
                              re.IGNORECASE)
    # Pay type, current, ytd
    re_earnings2 = re.compile(r'(^.*)\s\$([\d\.,]+)\s+\$[\d\.,]+', re.IGNORECASE)

    for line in split_lines[i:]:
        match1 = re_earnings1.match(line)
        if match1:
            description = match1.group(1).strip()
            amount = match1.group(2)
            amount = amount.replace(',', '')
            if 'earnings' not in return_dict.keys():
                return_dict['earnings'] = dict()
            return_dict['earnings'][description] = float(amount)
            continue
        match2 = re_earnings2.match(line)
        if match2:
            description = match2.group(1).strip()
            amount = match2.group(2)
            amount = amount.replace(',', '')
            if 'earnings' not in return_dict.keys():
                return_dict['earnings'] = dict()
            return_dict['earnings'][description] = float(amount)
            continue
        return


def process_deductions(i, split_lines, return_dict):
    """ Processes deductions portion of input file."""

    # Deduction Pre-Tax Employee Current, Employee YTD, Employer Current, Employer YTD
    re_deductions = re.compile(r'^([a-z0-9%&\s]+)(?:Yes|No)\s+\$([\d\.]+)\s+\$[\d\.]+\s+\$([\d\.\s]+)\s+\$[\d\.\s]+',
                               re.IGNORECASE)

    for line in split_lines[i:]:
        match1 = re_deductions.match(line)
        if match1:
            description = match1.group(1).strip()
            employee_cur = match1.group(2)
            employee_cur = massage_float(employee_cur)
            employer_cur = match1.group(3)
            employer_cur = massage_float(employer_cur)
            if 'deductions' not in return_dict.keys():
                return_dict['deductions'] = dict()
            if employee_cur > 0.0:
                if 'employee' not in return_dict['deductions'].keys():
                    return_dict['deductions']['employee'] = dict()
                return_dict['deductions']['employee'][description] = employee_cur
            if employer_cur > 0.0:
                if 'employer' not in return_dict['deductions'].keys():
                    return_dict['deductions']['employer'] = dict()
                return_dict['deductions']['employer'][description] = employer_cur
            continue
        return


def process_taxes(i, split_lines, return_dict):
    """ Processes tax portion of input file."""

    # Tax Current YTD
    re_taxes = re.compile(r'([a-z0-9%&\-\s]+)\$([\d\.,]+)\s+\$', re.IGNORECASE)

    for line in split_lines[i:]:
        match1 = re_taxes.match(line)
        if match1:
            description = match1.group(1).strip()
            amount = massage_float(match1.group(2))
            if 'taxes' not in return_dict.keys():
                return_dict['taxes'] = dict()
            return_dict['taxes'][description] = amount
            continue
        return


def massage_float(val_str: str):
    """ Removes spaces in the number string and also removes commas."""
    val = val_str.strip()
    val = val.replace(' ', '')
    val = val.replace(',', '')
    val = float(val)

    return val
