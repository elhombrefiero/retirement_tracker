#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
import glob
import os

from finances.models import User, RetirementAccount, Deposit, CheckingAccount, BUDGET_GROUP_DGR, Transfer, Statutory
from finances.utils.file_processing import process_user_work_file

# Other Imports
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError


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

        Deductions are entered as Debts, Goals, Retirement because they are all 401k or HSA related

        """
        parser.add_argument('filename', type=Path,
                            help='Work income file.')
        parser.add_argument('user', type=str, help='User name (case-sensitive)')
        parser.add_argument('check_account', type=str, help='Checking account name (case-sensitive)')
        parser.add_argument('saving_account', type=str, help='Savings account name (case-sensitive). Enter "None" if '
                                                             'no savings account.')
        parser.add_argument('ret401k_account', type=str, help='401k account name (case-sensitive)')
        parser.add_argument('retHSA_account', type=str, help='HSA account name (case-sensitive)')

    def handle(self, *args, **kwargs):
        """ Processes the work-income file and information based on user input."""
        input_file = kwargs['filename']
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

        caccount = None
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

        files = list()
        if not os.path.exists(input_file):
            print(f'File {input_file} does not exist.')
            return

        if os.path.isdir(input_file):
            files = glob.glob(os.path.join(input_file, '*.pdf'))
        else:
            files.append(input_file)

        self.stdout.write(self.style.SUCCESS(f'Found {len(files)} pdf files to process.'))

        for filename in files:
            self.stdout.write(self.style.SUCCESS(f'Processing {filename}.'))
            work_info = process_user_work_file(filename)

            if work_info:
                self.stdout.write(self.style.SUCCESS(f'Contents of the work_info file:'))
                for key1, value1 in work_info.items():
                    self.stdout.write(self.style.SUCCESS(f'{key1}'))
                    if type(value1) == dict:
                        for key2, value2 in value1.items():
                            self.stdout.write(self.style.SUCCESS(f'{key2}: {value2}'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'{key1}: {value1}'))
                try:
                    pdate = work_info['pay_date']
                except:
                    self.stdout.write(self.style.ERROR(f'Could not extract pay date from {filename}.'))
                    return
                self.stdout.write(self.style.SUCCESS(f'Pay date is {pdate}.'))

                if 'earnings' in work_info.keys():
                    for description in work_info['earnings'].keys():
                        if work_info['earnings'][description] > 0.0:
                            try:
                                deposit, created = Deposit.objects.update_or_create(account=caccount,
                                                                                    date=pdate,
                                                                                    description=description,
                                                                                    amount=work_info['earnings'][description],
                                                                                    defaults={'category': 'Work',
                                                                                              'location': 'Work'})
                                if created:
                                    self.stdout.write(self.style.SUCCESS(f'Created Deposit {deposit}'))
                                else:
                                    self.stdout.write(self.style.SUCCESS(f'Updated Deposit {deposit}'))
                                deposit.save()
                            except IntegrityError as e:
                                self.stdout.write(self.style.ERROR(f'Error updating Deposit {description} on {pdate}: {e}'))
                                continue
                            deposit.save()

                # TODO: Determine if deductions should come through income file or through associated account files.
                # if 'deductions' in work_info.keys():
                #     for description in work_info['deductions'].keys():
                #         if 'employee' in work_info['deductions'][description].keys():
                #             withdrawal, created = Withdrawal.objects.update_or_create(account=caccount,
                #                                       date=pdate,
                #                                       description=description,
                #                                       amount=work_info['deductions'][description]['employee'],
                #                                       defaults={'budget_group': 'BUDGET_GROUP',
                #                                                 'category': 'Work',
                #                                                 'location': 'Work'})
                if 'taxes' in work_info.keys():
                    for description in work_info['taxes'].keys():
                        try:
                            statutory, created = Statutory.objects.update_or_create(amount=work_info['taxes'][description],
                                                                                    date=pdate,
                                                                                    description=description,
                                                                                    defaults={'user': user,
                                                                                              'category': 'Work',
                                                                                              'location': 'Work'})
                            if created:
                                self.stdout.write(self.style.SUCCESS(f'Created Statutory {statutory}'))
                            else:
                                self.stdout.write(self.style.SUCCESS(f'Updated Statutory {statutory}'))
                        except IntegrityError as e:
                            self.stdout.write(self.style.ERROR(f'Error updating Statutory {description} on {pdate}: {e}'))
                            continue
                        statutory.save()
                if 'transfer' in work_info.keys():
                    try:
                        transfer, created = Transfer.objects.update_or_create(account_from=caccount,
                                                                              account_to=saccount,
                                                                              date=pdate,
                                                                              budget_group=BUDGET_GROUP_DGR,
                                                                              amount=work_info['transfer'],
                                                                              defaults={'category': 'Transfer',
                                                                                        'description': 'Work Income',
                                                                                        'location': 'Work'})

                        if created:
                            self.stdout.write(self.style.SUCCESS(
                                f'Transfered ${work_info["transfer"]} from {caccount_name} to {saccount_name}'))
                            transfer.save()
                    except IntegrityError as e:
                        self.stdout.write(self.style.ERROR(
                            f'Error updating Transfer of {work_info["transfer"]} from {caccount_name} to {saccount_name}: {e}'))
            else:
                self.stdout.write(self.style.ERROR(f'No information found for {filename}'))

        self.stdout.write(self.style.SUCCESS(
            f'Completed processing import_worK_incomes.'))
