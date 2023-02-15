#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
import os
import json
import datetime

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

        acct_id = None
        for acct in acct_json:
            acct_id = acct['id']
            if acct['name'] == old_acct_name:
                break
        if acct['name'] != old_acct_name or acct_id is None:
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
            incomes = json.load(fileobj)
        with open(expense_file) as fileobj:
            expenses = json.load(fileobj)

        for income in incomes:
            if not income['account_id'] == acct_id:
                continue
            inc_date = datetime.datetime.strptime(income['income_date'], '%Y-%m-%d')
            obj, created = Income.objects.update_or_create(
                user=user,
                account=acct,
                date=inc_date,
                description=income['description'],
                defaults={'amount': income['amount'],
                          'category': income['category'],
                          'group': income['group']
                          }
            )
            obj.save()
            num_of_incomes += 1

        for expense in expenses:
            if not expense['account_id'] == acct_id:
                continue
            exp_date = datetime.datetime.strptime(expense['expense_date'], '%Y-%m-%d')
            obj, created = Expense.objects.update_or_create(
                user=user,
                account=acct,
                date=exp_date,
                description=expense['description'],
                defaults={'amount': expense['amount'],
                          'budget_group': expense['budget_group'],
                          'category': expense['category'],
                          'where_bought': expense['where_bought'],
                          'group': expense['group']}
            )
            obj.save()
            num_of_expenses += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully added {num_of_incomes} incomes and {num_of_expenses} expenses for {user}'))


