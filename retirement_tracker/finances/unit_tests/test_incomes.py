#!/usr/bin/env python3

# Python Library Imports
from django.test import TestCase

# Other Imports
from finances.models import User, Account, Income


class IncomeTestCase(TestCase):

    def setUp(self) -> None:
        user = User.objects.create(name='TestUser', date_of_birth='01/01/1975', retirement_age=65.0)
        account = Account.objects.create(user=user, name='TestAccount')
        Income.objects.create(account=account, category='TestCategory', description='TestDescription', amount=420.69)

    def test_user_balance(self):
        user = User.objects.get(name='TestUser')
        account = Account.objects.get(name='TestAccount')
        income = Income.objects.get(description='TestDescription')

        # Get today's date and get the month and year
        balance = user.return_takehome_pay_month_year('January', 2022)
        self.assertEqual(balance, 420.69)

