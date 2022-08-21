from django.db import models
from django.utils.timezone import now
from django.utils.text import slugify


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

    # Budget percentages for blank budgets
    DEFAULT_MANDATORY_BUDGET_PCT = 16.0
    DEFAULT_MORTGAGE_BUDGET_PCT = 29.0
    DEFAULT_DGR_BUDGET_PCT = 25.0
    DEFAULT_DISC_BUDGET_PCT = 100 - DEFAULT_MANDATORY_BUDGET_PCT - DEFAULT_MORTGAGE_BUDGET_PCT - DEFAULT_DGR_BUDGET_PCT

    name = models.CharField(max_length=160)
    date_of_birth = models.DateField(verbose_name='Date of Birth')
    retirement_age = models.DecimalField(verbose_name='Retirement Age', decimal_places=2, max_digits=4)
    percent_withdrawal_at_retirement = models.DecimalField(verbose_name='Percent withdrawal at retirement',
                                                           decimal_places=2, default=4.0, max_digits=5)

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

    def return_takehome_pay_month_year(self, month, year):
        """ Calculates the take home pay for a given month and year."""
        user_accounts = Account.objects.filter(user=self)
        #incomes_for_acct = Income.objects.filter()
        return 420.69

    def set_budget_month_year(self, month, year):
        """ Set monthly budget based on default percentages given the take home income."""

        # Get the
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
    name = models.CharField(max_length=160)
    url = models.URLField(name="Account URL", blank=True)
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
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.FloatField(verbose_name='Amount')


class Deposit(models.Model):
    """ Deposit for a given account.

    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.FloatField(verbose_name='Amount')


class SavingsAccount(Account):
    pass


class RetirementAccount(Account):
    """ 401k, IRA"""
    monthly_interest_rate = models.FloatField(verbose_name='Monthly Interest')

    def get_roi(self):
        pass

    def calculate_total_at_date(self):
        """Estimates the total amount at a certain point in time based on the monthly interest rate."""
        pass


class Expense(models.Model):
    BUDGET_GROUP_CHOICES = (
        ('Mandatory', 'Mandatory'),
        ('Mortgage', 'Mortgage'),
        ('Debts, Goals, Retirement', 'Debts, Goals, Retirement'),
        ('Discretionary', 'Discretionary'),
        ('Statutory', 'Statutory'),
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    budget_group = models.CharField(max_length=200, choices=BUDGET_GROUP_CHOICES)
    category = models.CharField(max_length=200)
    where_bought = models.CharField(max_length=64)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    slug_field = models.SlugField(null=True, blank=True)
    # Optional group for any specific purpose (e.g., vacation in Hawaii)
    group = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return "{}\t{}\t{:50}\t{}\t{}\t{}".format(self.date,
                                                  self.account.name,
                                                  self.budget_group,
                                                  self.where_bought,
                                                  self.description,
                                                  self.amount)

    def save(self, *args, **kwargs):
        if not self.slug_field:
            self.slug_field = slugify(self.description)
        super(Expense, self).save(*args, **kwargs)

    class Meta:
        unique_together = ['account', 'date', 'description', 'amount']


class Income(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    category = models.CharField(max_length=128)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    # Optional group for any specific purpose (e.g., vacation in Hawaii)
    group = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return "{} on {} - {}".format(self.description, self.date, self.amount)

    class Meta:
        unique_together = ['account', 'date', 'description', 'amount']


class MonthlyBudget(models.Model):
    """ The monthly budgets set for a given user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(name='Date', default=now)
    month = models.CharField(max_length=18, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)

    mandatory = models.FloatField()
    statutory = models.FloatField()
    mortgage = models.FloatField()
    debts_goals_retirement = models.FloatField()
    discretionary = models.FloatField()

    def save(self, *args, **kwargs):
        self.month = self.date.strftime('%B')
        self.year = int(self.date.strftime('%Y'))
        super(MonthlyBudget, self).save(*args, **kwargs)

    def __str__(self):
        return "Budget for {}, {}".format(self.month, self.year)

    class Meta:
        unique_together = ["month", "year"]
