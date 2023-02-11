#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
import os
import json
import datetime

# Other Imports
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from finances.models import User, MonthlyBudget

# Defined Functions:
#   load_old_db - Takes in the old data from the original finances (i.e., money) project and adds the information for a given user


class Command(BaseCommand):
    help = 'Loads the old database into the new format'

    def add_arguments(self, parser):
        parser.add_argument('monthlybudget_old', type=Path)
        parser.add_argument('budget_old', type=Path)
        parser.add_argument('user', type=str)
        parser.add_argument('--update_existing', type=bool)

    def handle(self, *args, **options):
        mb_old = options['monthlybudget_old']
        budget_old = options['budget_old']
        input_user = options['user']

        update_existing = False
        if 'update_existing' in options:
            update_existing = options['update_existing']

        if not os.path.exists(mb_old):
            print(f'Old monthly budget file {mb_old} does not exist. ')
            return

        if not os.path.exists(budget_old):
            print(f'Old budget file {budget_old} does not exist.')
            return

        # Check if the user exists or create a new one.
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
            y_n = input(f'Insert monthly budgets from {os.path.basename(budget_old)} for {user}? ([y]es or [n]o)')
            if not y_n.lower().startswith('y'):
                return

        with open(mb_old) as fileobj:
            monthly_budgets = json.load(fileobj)
        with open(budget_old) as fileobj:
            budgets = json.load(fileobj)
        for monthly_budget in monthly_budgets:
            # TODO: Try to find a more elegant solution here
            for budget in budgets:
                budget_dict = budget
                if monthly_budget['id'] not in budget:
                    continue
            try:
                mbudget_new = MonthlyBudget.objects.get(month=monthly_budget['month'], year=monthly_budget['year'])
                if not update_existing:
                    yn = input(f'{mbudget_new.name} already exists and update_existing is false. Overwrite? ([y]es or [n]o or [q]uit )')
                    if yn.lower().startswith('q'):
                        return
                    if yn.lower().startwith('n'):
                        continue
            except MonthlyBudget.DoesNotExist:
                mbudget_new = MonthlyBudget.objects.create(date=monthly_budget["date"])

            print(monthly_budget['id'])

