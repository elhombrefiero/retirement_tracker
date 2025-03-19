#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
import os
import shutil
from datetime import datetime
import subprocess as sp
import shlex
import json
import csv

from finances.models import User, RetirementAccount, Deposit, Withdrawal, BUDGET_GROUP_DGR, CheckingAccount
from finances.utils.file_processing import process_user_work_file

# Other Imports
from django.core.management.base import BaseCommand, CommandError


# Defined Functions:
# import_work_income - Imports the work-related income information

class Command(BaseCommand):
    help = 'Opens the PDF of work income info and puts that into the specified user/account'

    def add_arguments(self, parser):
        """ Add work-related incomes and deductions based on user-provided PDF file.

        Required entries:
            filename - PDF with table entries of incomes and deductions/taxes
            user - name of the User to add work-related incomes and expenses
            checking account name - account name for the checking account for the associated user
            401k retirement account name - retirement account name for the associated user to add 401k data
            HSA retirement account name - retirement account name for the associated user to add HSA data

        For the work income, the file uses Pay Date as the date to use for the addition.

        The Earnings table has the following headers : Pay Type, Hours, Pay Rate, Current, and YTD.
        Current is the column of interest.

        The Deductions table has the following headers:
            Deduction, Pre-Tax, Employee Current, Employee YTD, Employer Current, and Employer YTD.
        Capture the following:
            Deduction - the name of the deduction
            Employee Current - the amount paid by the employee
            Employer Current - the amount paid by the employer

        Anything with HSA in the deduction will count towards the HSA account
        Anything with Roth or 401k in the deduction will count towards the 401k account
        Anything else will count only if there is a non-zero value in the Employee Current column.
        Items that are only Employer Current are skipped.

        The Taxes table has: Tax, Current, and YTD
        Capture the following:
            Tax - Name of the Tax
            Current - The amount of the tax
        All non-zero taxes will be entered as Statutory entries for the user

        Net pay Distribution is going to have account numbers, account type, and the amount put into that account based on after tax and deductions.

        """
        parser.add_argument('filename', type=Path, help='Work income file.')
        parser.add_argument('user', type=str, help='User name (case-sensitive)')
        parser.add_argument('check_account', type=str, help='Checking account name (case-sensitive)')
        parser.add_argument('saving_account', type=str, help='Savings account name (case-sensitive). Enter "None" if '
                                                             'no savings account.')
        parser.add_argument('ret401k_account', type=str, help='401k account name (case-sensitive)')
        parser.add_argument('retHSA_account', type=str, help='HSA account name (case-sensitive)')

    def handle(self, *args, **kwargs):
        """ Processes the work-income file and information based on user input."""
        filename = kwargs['filename']
        user_input = kwargs['user']
        caccount_name = kwargs['check_account']
        saccount_name = kwargs['saving_account']
        ret401k_account_name = kwargs['ret401k_account']
        retHSA_account_name = kwargs['retHSA_account']

        try:
            user = User.objects.get(name=user_input)
        except User.DoesNotExist:
            print(f'User {user_input} does not exist. Here are the valid options: ')
            all_users = User.objects.all()
            for user in all_users:
                print(user.name)
            return

        try:
            caccount = CheckingAccount.objects.get(user=user, name=caccount_name)
        except CheckingAccount.DoesNotExist:
            print(f'Account {caccount_name} does not exist for user {user_input}. Here are valid options: ')
            c_accounts = CheckingAccount.objects.filter(user=user)
            for c_account in c_accounts:
                print(c_account.name)
            return

        saccount = None
        if saccount_name:
            try:
                saccount = CheckingAccount.objects.get(user=user, name=saccount_name)
            except CheckingAccount.DoesNotExist:
                print(f'Account {saccount_name} does not exist for user {user_input}. Here are valid options: ')
                c_accounts = CheckingAccount.objects.filter(user=user)
                for c_account in c_accounts:
                    print(c_account.name)
                return

        try:
            ret401kaccount = RetirementAccount.objects.get(user=user, name=ret401k_account_name)
        except RetirementAccount.DoesNotExist:
            print(f'Account {ret401k_account_name} does not exist for user {user_input}. Here are valid options: ')
            c_accounts = RetirementAccount.objects.filter(user=user)
            for c_account in c_accounts:
                print(c_account.name)
            return

        try:
            rethsaaccount = RetirementAccount.objects.get(user=user, name=retHSA_account_name)
        except RetirementAccount.DoesNotExist:
            print(f'Account {retHSA_account_name} does not exist for user {user_input}. Here are valid options: ')
            c_accounts = RetirementAccount.objects.filter(user=user)
            for c_account in c_accounts:
                print(c_account.name)
            return

        if not os.path.exists(filename):
            print(f'File {filename} does not exist.')
            return

        work_info = process_user_work_file(filename)

        self.stdout.write(self.style.SUCCESS(
            f'Processed {filename} for work income.'))
