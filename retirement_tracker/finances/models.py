from django.db import models


class User(models.Model):
    """ User class for the retirement tracker.

    Attributes:
    User Name
    User DOB
    Retirement Age

    DB Related Attributes:
    Checking Accounts
    Saving Accounts / Stocks
    Retirement Account
    Incomes
    Expenses
    Monthly Budgets

    Functions:
    return_retirement_timestamp
    estimate_retirement_finances
    estimate_budget_for_month_year
    get_total_for_month_year
    """

    name = models.CharField(max_length=160)
    date_of_birth = models.DateField(name='Date of Birth')
    retirement_age = models.DecimalField(name='Retirement Age', decimal_places=2)

    def return_retirement_timestamp(self):
        """ Returns the timestamp at retirement age. """
        pass

    def estimate_retirement_finances(self):
        """ Calculates estimated retirement overview. """
        pass

    def estimate_budget_for_month_year(self, month, year):
        """ Returns estimated budget values based on takehome pay and budget expenses."""
        pass

    def get_total_for_month_year(self, month, year):
        """ Calculates the total balance for the given month and year"""
        pass


class Account(models.Model):
    """ Base accounts for a given user.

    Name
    URL

    Deposits
    Withdrawals

    Return the balance for all time
    Return balance for given month/year
    Estimate balance at month/year
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def return_balance(self):
        pass

    def return_balance_month_year(self):
        pass

    def estimate_balance_month_year(self):
        pass


class Withdrawal(models.Model):
    """ Withdrawal for a given account.

    """
    account = models.ForeignKey(Account)
    amount = models.FloatField(verbose_name='Amount')


class Deposit(models.Model):
    """ Deposit for a given account.

    """
    account = models.ForeignKey(Account)
    amount = models.FloatField(verbose_name='Amount')


class SavingsAccount(Account):
    pass


class RetirementAccount(Account):
    """ 401k, IRA"""
    interest_rate = models.FloatField(verbose_name='Monthly Interest')
    pass


class Expense(models.Model):
    pass


class Income(models.Model):
    pass


class MonthlyBudget(models.Model):
    """ The monthly budgets set for a given user."""
    pass
