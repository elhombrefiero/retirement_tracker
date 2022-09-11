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
    """ Test for various things in user,income.
    User is named TestUser, aged 65 (about to retire)
        Has two checking accounts, one savings account, one brokerage account, one stock account, one IRA, and one 401k

    Test_Checking1 has two incomes:
        $50 at start of the month. $75 at end of the month.
    Test_Checking2 has four incomes:
        $10 at start of the month. $10 at the end of the month.
        $20 at the start of the next month. $20 at the end of the next month.
    Test_Saving1 has one income:
        $35 at the start of the month
    Test_Brokerage (TradingAccount) has one income:
        $5000 at the time of retirement
    Test_401k (RetirementAccount) has two incomes:
        $20k at age 40
        $20k at age 65
    TestUser will withdraw 4% from Retirement Accounts at the time of retirement


    """
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
        """ Check that all of the incomes are accounted for the Test_User.

        Total should be:

        """
        user = User.objects.get(name=TEST_USER)

        # Get today's date and get the month and year
        balance = user.return_takehome_pay_month_year('January', 2022)
        self.assertEqual(balance, 420.69)

    def test_account_balances(self):
        """ Check the correct balances of the different accounts.

        Total(s) should be:


        """

    def test_no_duplicate_income(self):
        """ Try to add an identical entry to an account and verify the error.

        Try to add an identical entry to a different account and verify that it goes through.
        """
        pass

    def test_get_attribute_total(self):
        """ Add two entries with the same category name in the same month/year and verify their total is captured. """
        pass

    def test_cumulative_income_expense(self):
        pass

    def test_get_latest_date(self):
        """ Check the latest date of each account."""
        pass
