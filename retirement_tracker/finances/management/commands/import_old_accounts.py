#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
import os
import json

# Other Imports
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from finances.models import User, Expense, Income, CheckingAccount, RetirementAccount, DebtAccount

# Defined Functions:
#   import_old_accounts - Imports the old income, expenses, and account info from the money project

class Command(BaseCommand):
    help = 'Loads the data from the money format to the new format.'

    def add_arguments(self, parser):
        parser.add_argument('user_name', type=str)
        parser.add_argument('old_account_name', type=str)
        parser.add_argument('new_account_name', type=str)
        parser.add_argument('account_type', type=str)
        parser.add_argument('account_json', type=Path)
        parser.add_argument('income_json', type=Path)
        parser.add_argument('expense_json', type=Path)

    def handle(self, *args, **options):
        num_of_incomes = 0
        num_of_expenses = 0

        input_user = options['user_name']
        old_acct_name = options['old_account_name']
        new_acct_name = options['new_account_name']
        acct_type = options['account_type']

        acct_file = options['account_json']
        income_file = options['income_json']
        expense_file = options['expense_json']

        # Get the user associated with the username
        try:
            user = User.objects.get(name=input_user)
        except User.DoesNotExist:
            y_n = input(f'User with name {input_user} does not exist in database. Create new user? ([y]es or [n]o)')
            if not y_n.lower().startswith('y'):
                return
            else:
                print("Creating new user. Update DOB in main app page.")
                user = User.objects.create(name=input_user, date_of_birth=now)
        finally:
            y_n = input(f'Importing account incomes and expenses using {os.path.basename(acct_file)}, {os.path.basename(income_file)}, and {os.path.basename(expense_file)} for {user}. Type "[y]es" to continue.')
            if not y_n.lower().startswith('y'):
                return

        # Find the old account name using the user input and check if new account exists
        with open(acct_file) as fileobj:
            acct_json = json.load(fileobj)

        for acct in acct_json:
            acct_id = acct['id']
            if acct['name'] == old_acct_name:
                break
        if acct['name'] != old_acct_name:
            print(f'Could not find matching old account name {old_acct_name}')
            return

        if acct_type == 'Checking':
            try:
                acct = CheckingAccount.objects.get(user=user, name=new_acct_name)
            except CheckingAccount.DoesNotExist:
                yn = input(f"No existing checking account with name {new_acct_name} exists for {user}. Create new? [y]es to continue")
                if not yn.lower().startswith('y'):
                    return
                acct = CheckingAccount.objects.create(user=user, name=new_acct_name)
        elif acct_type == 'Debt':
            try:
                acct = DebtAccount.objects.get(user=user, name=new_acct_name)
            except DebtAccount.DoesNotExist:
                yn = input(f"No existing debt account with name {new_acct_name} exists for {user}. Create new? [y]es to continue")
                if not yn.lower().startswith('y'):
                    return
                acct = DebtAccount.objects.create(user=user, name=new_acct_name)
        elif acct_type == 'Retirement':
            try:
                acct = RetirementAccount.objects.get(user=user, name=new_acct_name)
            except RetirementAccount.DoesNotExist:
                yn = input(f"No existing retirement account with name {new_acct_name} exists for {user}. Create new? [y]es to continue")
                if not yn.lower().startswith('y'):
                    return
                acct = RetirementAccount.objects.create(user=user, name=new_acct_name, target_amount=9999999)
        else:
            print(f'Incorrect account type option: {acct_type}')
            return

        with open(income_file) as fileobj:
            income_json = json.load(fileobj)
        with open(expense_file) as fileobj:
            expense_json = json.load(fileobj)


