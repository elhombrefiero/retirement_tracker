#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
from datetime import datetime
import csv

from finances.models import User, RetirementAccount, Deposit, Withdrawal, BUDGET_GROUP_DGR

# Other Imports
from django.core.management.base import BaseCommand

# Defined Functions:
# import_anthem_hsa_info - Imports the Anthem information based on the exported

class Command(BaseCommand):
    help = 'Reads the Anthem account info and puts that into the specified account'

    def add_arguments(self, parser):
        parser.add_argument('user', type=str, help='User name (case-sensitive)')
        parser.add_argument('account name', type=str, help='Account name (case-sensitive)')
        parser.add_argument('filename', type=Path, help='CSV of Anthem information..')
        parser.add_argument('--lookup_date', type=str, help='Header text to find dates', default='Transaction Date')
        parser.add_argument('--lookup_date_format', type=str, help='Format for the date parser', default='%m/%d/%Y')
        parser.add_argument('--lookup_transaction', type=str, default='Description',
                            help='Header item containing withdrawal or deposit items.')
        parser.add_argument('--lookup_amount', type=str, help='Header text for the amount', default='Amount')


    def handle(self, *args, **kwargs):
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
                amount_text = row[kwargs['lookup_amount']].strip()
                amount = float(amount_text)
                amount_input = abs(amount)
                transaction = row[kwargs['lookup_transaction']]

                if amount < 0.0:
                    withdrawal, created = Withdrawal.objects.update_or_create(
                        account=account,
                        date=date_dt,
                        description=transaction,
                        amount=amount_input,
                        defaults={'budget_group': BUDGET_GROUP_DGR,
                                  'category': 'Retirement',
                                  'location': 'Work'}
                    )
                    withdrawal.save()
                    difference -= amount
                    number_of_entries += 1

                if amount >= 0.0:
                    deposit, created = Deposit.objects.update_or_create(account=account,
                                                                        date=date_dt,
                                                                        amount=amount_input,
                                                                        description=transaction,
                                                                        defaults={'category': 'Retirement',
                                                                                  'location': 'Work'}
                                                                        )
                    deposit.save()
                    difference += amount
                    number_of_entries += 1
        self.stdout.write(self.style.SUCCESS(
            f'Min date: {min_date}. Max date: {max_date}'))
        self.stdout.write(self.style.SUCCESS(
            f'Processed {number_of_entries} entries for {account.name}. Difference between deposits and withdrawals: {difference}'))

