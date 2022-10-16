#!/usr/bin/env python3

# Python Library Imports
from django.test import TestCase

# Other Imports
from finances.models import User, Account, Income, Expense, RetirementAccount, TradingAccount, Deposit, Withdrawal
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
        first_day_of_month = datetime.strptime(today_date.strftime('%Y-%m-01'), '%Y-%m-%d')
        last_day_of_month = first_day_of_month + relativedelta(months=+1, days=-1)
        first_day_next_month = first_day_of_month + relativedelta(months=+1)
        self.first_day_next_month = first_day_next_month
        last_day_next_month = first_day_next_month + relativedelta(months=+1, days=-1)
        user1_date_of_birth = (first_day_of_month + relativedelta(years=-65)).strftime('%Y-%m-%d')
        date_15years_ago = first_day_of_month + relativedelta(years=-15)
        user = User.objects.create(name=TEST_USER, date_of_birth=user1_date_of_birth, retirement_age=65.0)
        caccount = Account.objects.create(user=user, name='Test_Checking1')
        caccount2 = Account.objects.create(user=user, name='Test_Checking2')
        saccount = Account.objects.create(user=user, name='Test_Savings')
        tacct = TradingAccount.objects.create(user=user, name='Test_Brokerage')
        ret_401k = RetirementAccount.objects.create(user=user, name='Test_401k')
        Income.objects.create(user=user, account=caccount, date=first_day_of_month, category='TestCategory', description='TestDescription', amount=50.0)
        Income.objects.create(user=user, account=caccount, date=last_day_of_month, category='TestCategory', description='TestDescription', amount=75.0)
        Income.objects.create(user=user, account=caccount2, date=first_day_of_month, category='TestCategory', description='TestDescription', amount=10.0)
        Income.objects.create(user=user, account=caccount2, date=last_day_of_month, category='TestCategory', description='TestDescription', amount=10.0)
        Income.objects.create(user=user, account=caccount2, date=first_day_next_month, category='TestCategory', description='TestDescription', amount=20.0)
        Income.objects.create(user=user, account=caccount2, date=last_day_next_month, category='TestCategory', description='TestDescription', amount=20.0)
        Income.objects.create(user=user, account=saccount, date=first_day_of_month, category='TestCategory',
                              description='TestDescription', amount=35.0)
        Income.objects.create(user=user, account=tacct, date=first_day_of_month, category='TestCategory', description='TestDescription', amount=5000.0)
        Income.objects.create(user=user, account=ret_401k, date=first_day_of_month, category='TestCategory', description='TestDescription', amount=20000.0)
        Income.objects.create(user=user, account=ret_401k, date=date_15years_ago, category='TestCategory', description='TestDescription', amount=20000.0)
        #Expense.objects.create(account=account, budget_group='Mandatory', category='TestCategory',
        #                       where_bought='TestLocation', description='TestExpenseDescription', amount=100.00)

    def test_deposit_created_with_income(self):
        today_date = now()
        first_day_of_month = datetime.strptime(today_date.strftime('%Y-%m-01'), '%Y-%m-%d')
        caccount = Account.objects.get(name='Test_Checking1')
        try:
            dep_obj = Deposit.objects.get(account=caccount,
                                          date=first_day_of_month,
                                          description='TestDescription')
        except Deposit.DoesNotExist:
            dep_obj.amount = 0.0
        self.assertEqual(dep_obj.amount, 50.0)

    def test_withdrawal_created_with_expense(self):
        self.skipTest('Implement')

    def test_check_acct1_balance(self):
        """ Checks that the first account has the proper balance """
        caccount = Account.objects.get(name='Test_Checking1')
        cacct_balance = caccount.return_balance()

        self.assertEqual(cacct_balance, 125.0)

    def test_user_incomes(self):
        """ Check that all of the incomes are accounted for the Test_User.

        Total should be:

        Month 1:

            Checking Account totals:
                checking account: 125
                checking account 2: 20
                Savings 1: 35
                Total: 180
            Retirement:
                Brokerage: $5000
                401k: $20000

            Total: $25180

        Month 2:

            checking account 2: 40



        """
        user = User.objects.get(name=TEST_USER)
        today_date = now()
        month = today_date.strftime('%B')
        year = today_date.strftime('%Y')

        next_month_date = today_date + relativedelta(months=+1)
        next_month_month = next_month_date.strftime('%B')
        next_month_year = next_month_date.strftime('%Y')

        # Get today's date and get the month and year
        this_month_balance = user.get_total_for_month_year(month, year)
        self.assertEqual(this_month_balance, 180.0)

        next_month_balance = user.get_total_for_month_year(next_month_month, next_month_year)
        self.assertEqual(next_month_balance, 40.0)

    def test_account_balances(self):
        """ Check the correct balances of the different accounts.

        Total(s) should be:


        """
        self.skipTest('Implement later')

    def test_no_duplicate_income(self):
        """ Try to add an identical entry to an account and verify the error.

        Try to add an identical entry to a different account and verify that it goes through.
        """
        self.skipTest('Implement later')

    def test_get_attribute_total(self):
        """ Add two entries with the same category name in the same month/year and verify their total is captured. """
        self.skipTest('Implement later')

    def test_cumulative_income_expense(self):
        self.skipTest('Implement later')

    def test_get_latest_date(self):
        """ Check the latest date of each account."""
        self.skipTest('Implement later')
