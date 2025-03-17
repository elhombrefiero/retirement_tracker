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

from finances.models import User, RetirementAccount, Deposit, Withdrawal, BUDGET_GROUP_DGR
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
        parser.add_argument('Checking account name', type=str, help='Checking account name (case-sensitive)')
        parser.add_argument('Savings account name', type=str, help='Savings account name (case-sensitive). Enter "None" if no savings account.')
        parser.add_argument('401k account name', type=str, help='401k account name (case-sensitive)')
        parser.add_argument('HSA account name', type=str, help='HSA account name (case-sensitive)')

    def handle(self, *args, **kwargs):
        """ Processes the work-income file and information based on user input."""
        user_input = kwargs['user']
        account_name = kwargs['account name']
        filename = kwargs['filename']
        difference = 0.0
        number_of_entries = 0
        min_date = None
        max_date = None
        try:
            user = User.objects.get(name=user_input)
        except User.DoesNotExist:
            print(f'User {user_input} does not exist. Here are the valid options: ')
            all_users = User.objects.all()
            for user in all_users:
                print(user.name)
            return

        try:
            account = RetirementAccount.objects.get(user=user, name=account_name)
        except RetirementAccount.DoesNotExist:
            print(f'Account {account_name} does not exist for user {user_input}. Here are valid options: ')
            ret_accounts = RetirementAccount.objects.filter(user=user)
            for ret_account in ret_accounts:
                print(ret_account.name)
            return

        with open(filename) as csvobj:
            dr = csv.DictReader(csvobj)
            if kwargs['lookup_date'] not in dr.fieldnames:
                print(f"ERROR: lookup for date ({kwargs['lookup_date']}) does not exist in data. Cannot continue.")
                return
            if kwargs['lookup_transaction'] not in dr.fieldnames:
                print(
                    f"ERROR: lookup for transactions ({kwargs['lookup_transaction']}) does not exist in data. Cannot continue.")
                return
            if kwargs['lookup_amount'] not in dr.fieldnames:
                print(
                    f"ERROR: lookup for amount ({kwargs['lookup_amount']}) does not exist in data. Cannot continue.")
                return

            for row in dr:
                date = row[kwargs['lookup_date']]
                date_dt = datetime.strptime(date, kwargs['lookup_date_format'])
                if min_date is None:
                    min_date = date_dt
                else:
                    min_date = min(min_date, date_dt)
                if max_date is None:
                    max_date = date_dt
                else:
                    max_date = max(max_date, date_dt)
                amount = float(row[kwargs['lookup_amount']])
                transaction = row[kwargs['lookup_transaction']]
                if transaction == kwargs['lookup_withdrawal']:
                    withdrawal, created = Withdrawal.objects.update_or_create(
                        account=account,
                        date=date_dt,
                        description=transaction,
                        amount=amount,
                        defaults={'budget_group': BUDGET_GROUP_DGR,
                                  'category': 'Retirement',
                                  'location': 'Work'}
                    )
                    if created:
                        print(f'Created withdrawal {withdrawal}')
                    withdrawal.save()
                    difference -= amount
                    number_of_entries += 1

                if transaction == kwargs['lookup_deposit']:
                    if kwargs['deposit_description']:
                        dep_description = kwargs['deposit_description']
                    else:
                        dep_description = transaction
                    deposit, created = Deposit.objects.update_or_create(account=account,
                                                                        date=date_dt,
                                                                        amount=amount,
                                                                        description=dep_description,
                                                                        defaults={'category': 'Retirement',
                                                                                  'location': 'Work'}
                                                                        )
                    if created:
                        print(f'Created deposit: {deposit}')
                    deposit.save()
                    difference += amount
                    number_of_entries += 1
        self.stdout.write(self.style.SUCCESS(
            f'Min date: {min_date}. Max date: {max_date}'))
        self.stdout.write(self.style.SUCCESS(
            f'Processed {number_of_entries} entries for {account.name}. Difference between deposits and withdrawals: {difference}'))
