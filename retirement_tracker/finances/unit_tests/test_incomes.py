#!/usr/bin/env python3

# Python Library Imports
from django.test import TestCase

# Other Imports
from finances.models import User, Account, Income, Expense
from django.utils.timezone import now
from datetime import datetime
from dateutil.relativedelta import relativedelta


TEST_USER = 'TestUser'


class IncomeTestCase(TestCase):
    """ Test for various things in user,income. """
    def setUp(self) -> None:
        today_date = now()
        first_day_of_month = datetime.strptime(today_date.strftime('%Y-%m-01'))
        user1_date_of_birth = (first_day_of_month + relativedelta(years=-65)).strftime('%Y-%m-%d')
        user = User.objects.create(name=TEST_USER, date_of_birth=user1_date_of_birth, retirement_age=65.0)
        account = Account.objects.create(user=user, name='TestAccount')
        Income.objects.create(account=account, category='TestCategory', description='TestDescription', amount=520.69)
        Expense.objects.create(account=account, budget_group='Mandatory', category='TestCategory',
                               where_bought='TestLocation', description='TestExpenseDescription', amount=100.00)

    def test_user_balance(self):
        user = User.objects.get(name=TEST_USER)

        # Get today's date and get the month and year
        balance = user.return_takehome_pay_month_year('January', 2022)
        self.assertEqual(balance, 420.69)

    def test_no_duplicate_income(self):
        pass

    def test_get_attribute_total(self):
        """ Add two entries with the same category name in the same month/year and verify their total is captured. """
        pass

    def test_cumulative_income_expense(self):
        pass

