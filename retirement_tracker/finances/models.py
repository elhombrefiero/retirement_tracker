from django.db import models
from django.db.models import Sum, Max
from django.utils.timezone import now
from django.utils.text import slugify
from django.shortcuts import reverse

from datetime import datetime
from dateutil.relativedelta import relativedelta

# TODO: Add a stock model, (stock name, purchase date, number of stocks)
# TODO: Add stock model to trading account.
#  Update trading account to use the stock information to determine the net worth over time.
BUDGET_GROUP_CHOICES = (
    ('Mandatory', 'Mandatory'),
    ('Mortgage', 'Mortgage'),
    ('Debts, Goals, Retirement', 'Debts, Goals, Retirement'),
    ('Discretionary', 'Discretionary'),
    ('Statutory', 'Statutory'),
)


class User(models.Model):
    """ User class for the retirement tracker.

    Attributes:
    User Name
    User DOB
    Retirement Age

    DB Related Attributes:
    Checking Accounts
    Trading Accounts (Stocks)
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
    retirement_age = models.DecimalField(verbose_name='Retirement Age', decimal_places=2, max_digits=4, default=65.0)
    percent_withdrawal_at_retirement = models.DecimalField(verbose_name='Percent withdrawal at retirement',
                                                           decimal_places=2, default=4.0, max_digits=5)

    def return_retirement_datetime(self):
        """ Returns the timestamp at retirement age. """
        num_months = int(float(self.retirement_age) * 12.0)
        ret_datetime = self.date_of_birth + relativedelta(months=num_months)
        return ret_datetime

    def return_retirement_acct_total(self):
        tot_ret_amt = 0.0
        user_ret_accts = RetirementAccount.objects.filter(user=self)

        for ret_acct in user_ret_accts:
            tot_ret_amt += ret_acct.return_balance()

        return tot_ret_amt

    def return_trading_acct_total(self):
        tot_trade_amt = 0.0
        user_trade_accts = TradingAccount.objects.filter(user=self)

        for ret_acct in user_trade_accts:
            tot_trade_amt += ret_acct.return_balance()

        return tot_trade_amt

    def estimate_retirement_finances(self):
        """ Calculate the amount each retirement account will have at the time of retirement.

        Calculates estimated retirement overview.
        """
        ret_balances = {}
        ret_date = self.return_retirement_datetime()
        ret_month = ret_date.strftime('%B')
        ret_year = ret_date.strftime('%Y')
        ret_accts = RetirementAccount.objects.filter(user=self)

        for ret_acct in ret_accts:
            name = ret_acct.name
            balance = ret_acct.return_balance_up_to_month_year(ret_month, ret_year)
            ret_balances.update({name: balance})

        return ret_balances

    def return_budget_group_balances_up_to_month_year(self, month, year):
        """ Calculates how much of each budget group is left over up to a certain month and year.

        """
        beg_of_month_year = datetime.strptime(f'{month}, 1, {year}', '%B, %d, %Y')
        # Get the expenses from checking accounts and separate them by budget groups.
        checking_accts = self.return_checking_accts()
        expenses = Expense.objects.filter(account=checking_accts, date__lt=beg_of_month_year)
        mand_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_CHOICES[0][0])
        mort_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_CHOICES[1][0])
        dgr_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_CHOICES[2][0])
        disc_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_CHOICES[3][0])
        stat_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_CHOICES[4][0])

        mand_tot = mand_exp.aggregate(total=Sum('amount'))['total']
        mort_tot = mort_exp.aggregate(total=Sum('amount'))['total']
        dgr_tot = dgr_exp.aggregate(total=Sum('amount'))['total']
        disc_tot = disc_exp.aggregate(total=Sum('amount'))['total']
        stat_tot = stat_exp.aggregate(total=Sum('amount'))['total']

        # Get the budget group totals up to current month/year
        mbudgets = MonthlyBudget.objects.filter(user=self, date__lt=beg_of_month_year)
        budget_mand_tot = mbudgets.aggregate(total=Sum('mandatory'))['total']
        budget_mort_tot = mbudgets.aggregate(total=Sum('mortgage'))['total']
        budget_dgr_tot = mbudgets.aggregate(total=Sum('debts_goals_retirement'))['total']
        budget_disc_tot = mbudgets.aggregate(total=Sum('discretionary'))['total']
        budget_stat_tot = mbudgets.aggregate(total=Sum('statutory'))['total']

        # Subtract the expenses from the budgets
        mand_balance = budget_mand_tot - mand_tot
        mort_balance = budget_mort_tot - mort_tot
        dgr_balance = budget_dgr_tot - dgr_tot
        disc_balance = budget_disc_tot - disc_tot
        stat_balance = budget_stat_tot - stat_tot

        balances = {'mandatory': mand_balance,
                    'mortgage': mort_balance,
                    'dgr': dgr_balance,
                    'discretionary': disc_balance,
                    'statutory': stat_balance}
        return balances

    def return_checking_accts(self):
        """ Returns only the checking account objects"""

        user_ret_accts = [acct.name for acct in RetirementAccount.objects.filter(user=self)]
        user_trade_accts = [acct.name for acct in TradingAccount.objects.filter(user=self)]
        user_accounts = self.account_set.all()

        user_accounts = user_accounts.exclude(name__in=user_ret_accts)
        user_accounts = user_accounts.exclude(name__in=user_trade_accts)

        return user_accounts

    def estimate_budget_for_month_year(self, month: str, year: int):
        """ Estimates and sets monthly budget values based on takehome pay and budget expenses."""

        # Get accounts associated with the user
        user_accounts = self.return_checking_accts()

        # Get the total income from base accounts for the current month/year
        total_income = 0
        statutory = 0
        for account in user_accounts:
            total_income += account.return_income_month_year(month, year)
            statutory += account.return_statutory_month_year(month, year)

        takehome = total_income - statutory
        thisdate = datetime.strptime(f'{month},{year}', '%B,%Y')
        budget_mort = takehome * self.DEFAULT_MORTGAGE_BUDGET_PCT / 100.0
        budget_mand = takehome * self.DEFAULT_MANDATORY_BUDGET_PCT / 100.0
        budget_dgr = takehome * self.DEFAULT_DGR_BUDGET_PCT / 100.0
        budget_disc = takehome * self.DEFAULT_DISC_BUDGET_PCT / 100.0

        try:
            mbudget = MonthlyBudget.objects.get(user=self, month=month, year=year)
        except MonthlyBudget.DoesNotExist:
            mbudget = MonthlyBudget.objects.create(user=self, date=thisdate)

        mbudget.mandatory = budget_mand
        mbudget.mortgage = budget_mort
        mbudget.statutory = statutory
        mbudget.debts_goals_retirement = budget_dgr
        mbudget.discretionary = budget_disc

        mbudget.save()

    def get_checking_total_month_year(self, month, year):
        """ Calculates the total balance for the given month and year"""
        tot = 0
        user_accounts = self.return_checking_accts()

        for account in user_accounts:
            tot += account.return_balance_month_year(month, year)

        return tot

    def get_ret_total_month_year(self, month, year):
        usr_ret_accts = RetirementAccount.objects.filter(user=self)
        tot = 0.0
        for account in usr_ret_accts:
            tot += account.return_balance_month_year(month, year)

        return tot

    def get_trading_total_month_year(self, month, year):
        user_trading_accts = TradingAccount.objects.filter(user=self)
        tot = 0.0
        for account in user_trading_accts:
            tot += account.return_balance_month_year(month, year)

        return tot

    def return_takehome_pay_month_year(self, month, year):
        """ Calculates the take home pay for a given month and year."""
        income = 0
        stat_expenses = 0
        user_accounts = self.return_checking_accts()
        for acct in user_accounts:
            income += acct.return_income_month_year(month, year)
            stat_expenses += acct.return_statutory_month_year(month, year)

        return income - stat_expenses

    def set_budget_month_year(self, month, year, statutory, budget_mand, budget_mort, budget_dgr, budget_disc):
        """ Set monthly budget based on user inputs."""

        month_year_dt = datetime.strptime(f'{month}-01-{year}', '%B-%d-%Y')

        try:
            mbudget = MonthlyBudget.objects.get(user=self, month=month, year=year)
        except MonthlyBudget.DoesNotExist:
            mbudget = MonthlyBudget.objects.create(user=self, date=month_year_dt)

        mbudget.mandatory = budget_mand
        mbudget.mortgage = budget_mort
        mbudget.debts_goals_retirement = budget_dgr
        mbudget.discretionary = budget_disc
        mbudget.statutory = statutory

        mbudget.save()

    def get_earliest_retirement_date(self):
        """ Returns the date at which the user is eligible for early retirement.

        Assumes the age 59.5 (i.e., 714 months) based on 2022 rules."""

        earliest_rt = self.retirement_age + relativedelta(months=+714)
        return earliest_rt

    def get_latest_retirement_date(self):
        """ Returns the latest date the user can retire.

        70 years based on ssn.gov"""

        latest_rt_dt = self.retirement_age + relativedelta(months=840)
        return latest_rt_dt

    def get_absolute_url(self):
        return reverse('finances:user_overview', args=[self.pk])

    def __str__(self):
        return self.name


class Account(models.Model):
    """ Base accounts for a given user.

    Name
    URL
    Monthly interest in percent (Use 0.0 for checking accounts)

    Database relations:
        User
        Deposits
        Withdrawals

    Functions:
        return_balance: Return the balance for all time
        return_balance_up_to_month_year: Returns the cumulative balance at the start of the month year
        return_balance_year: Return the balance for the requested year
        return_balance_month_year: Return balance for requested month/year
        estimate_balance_month_year: Performs a linear extrapolation of the balance up to the requested month/year
        return_latest_date: returns the latest database date for the account
    """
    name = models.CharField(max_length=160)
    url = models.URLField(name="Account URL", blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    monthly_interest_pct = models.DecimalField(verbose_name='Monthly interest in percent',
                                               max_digits=4, decimal_places=2, default=0.0)

    def return_balance(self):
        """ Calculates the balance for all time."""

        all_income = Deposit.objects.filter(account=self).aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0
        all_expense = Withdrawal.objects.filter(account=self).aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return float(all_income) - float(all_expense)

    def return_balance_year(self, year: int):
        start_datetime = datetime(year, 1, 1)
        end_datetime = datetime(year + 1, 1, 1) + relativedelta(seconds=-1)

        all_income = Deposit.objects.filter(account=self, date__ge=start_datetime, date__lt=end_datetime)
        all_income = all_income.aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0

        all_expense = Withdrawal.objects.filter(acount=self, date__ge=start_datetime, date__lt=end_datetime)
        all_expense = all_expense.aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return float(all_income) - float(all_expense)

    def return_balance_month_year(self, month: str, year: int):
        """ Gets the total balance of the account for a given month"""

        month_income = self.return_income_month_year(month, year)

        month_expense = self.return_expense_month_year(month, year)

        return float(month_income) - float(month_expense)

    def return_income_month_year(self, month: str, year: int):
        start_datetime = datetime.strptime(f'{month}-1-{year}', '%B-%d-%Y')
        end_datetime = start_datetime + relativedelta(months=+1, seconds=-1)

        month_income = Deposit.objects.filter(account=self, date__gte=start_datetime, date__lte=end_datetime)
        month_income = month_income.aggregate(total=Sum('amount'))['total']
        month_income = month_income if month_income is not None else 0.0

        return month_income

    def return_expense_month_year(self, month: str, year: int):
        start_datetime = datetime.strptime(f'{month}-1-{year}', '%B-%d-%Y')
        end_datetime = start_datetime + relativedelta(months=+1, seconds=-1)

        month_expense = Withdrawal.objects.filter(account=self, date__gte=start_datetime, date__lte=end_datetime)
        month_expense = month_expense.aggregate(total=Sum('amount'))['total']
        month_expense = month_expense if month_expense is not None else 0.0

        return month_expense

    def return_statutory_month_year(self, month: str, year: int):
        start_datetime = datetime.strptime(f'{month}-1-{year}', '%B-%d-%Y')
        end_datetime = start_datetime + relativedelta(months=+1, seconds=-1)

        month_expense = Withdrawal.objects.filter(account=self, date__gte=start_datetime, date__lte=end_datetime)
        month_expense.filter(budget_group='Statutory')
        month_expense = month_expense.aggregate(total=Sum('amount'))['total']
        month_expense = month_expense if month_expense is not None else 0.0

        return month_expense

    def return_balance_up_to_month_year(self, month: str, year: int):
        """ Returns the balance up to the start of the month and year.

        For example, a lookup of July, 2020 will return the balance up to 11:59pm on June, 30, 2020 """

        up_to_datetime = datetime.strptime(f'{year}-{month}-01', '%Y-%B-%d')
        up_to_datetime = up_to_datetime + relativedelta(seconds=-1)

        all_income = Deposit.objects.filter(account=self, date__lt=up_to_datetime)
        all_income = all_income.aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0

        all_expense = Withdrawal.objects.filter(acount=self, date__lt=up_to_datetime)
        all_expense = all_expense.aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return float(all_income) - float(all_expense)

    def estimate_balance_month_year(self, month: str, year: int, num_of_years=0, num_of_months=6):
        """ Performs a linear interpolation of balance vs time given the average of the last entries in the account

        By default uses data from six months before the requested month/year for the extrapolation.

         f(x) = y1 + ((x ??? x1) / (x2 ??? x1)) * (y2 ??? y1)

        """
        # TODO: Determine whether to interpolate or extrapolate based on the given month/year
        req_date = datetime.strptime(f'{month}, 1, {year}', '%B, %d, %Y')
        req_date_seconds_epoch = req_date.timestamp()  # x

        latest_date = self.return_latest_date()
        latest_date_seconds_epoch = latest_date.timestamp()  # x2
        latest_date_month = latest_date.strftime('%B')
        latest_date_year = latest_date.strftime('%Y')
        balance_at_latest_date = self.return_balance_up_to_month_year(latest_date_month, latest_date_year)  # y2

        time_prior = latest_date + relativedelta(years=-1 * num_of_years) + relativedelta(months=-1 * num_of_months)
        time_prior_seconds_epoch = time_prior.timestamp()  # x1
        time_prior_month = time_prior.strftime('%B')
        time_prior_year = time_prior.strftime('%Y')
        balance_at_time_prior = self.return_balance_up_to_month_year(time_prior_month, time_prior_year)  # y1

        estimated_balance = balance_at_time_prior + (req_date_seconds_epoch - time_prior_seconds_epoch) * (
                balance_at_latest_date - balance_at_time_prior) / (
                                    latest_date_seconds_epoch - time_prior_seconds_epoch)

        return estimated_balance

    def return_latest_date(self):
        """ Looks at all entries and determines the latest database date for the account."""
        latest_withdrawal_date = Withdrawal.objects.filter(account=self).latest('date').date
        latest_deposit_date = Deposit.objects.filter(account=self).latest('date').date

        latest_date = max(latest_deposit_date, latest_withdrawal_date)
        return latest_date

    def return_earliest_date(self):
        """ Looks at all entries and determines the latest database date for the account."""
        earliest_withdrawal_date = Withdrawal.objects.filter(account=self).earliest('date').date
        earliest_deposit_date = Deposit.objects.filter(account=self).earliest('date').date

        earliest_date = min(earliest_deposit_date, earliest_withdrawal_date)
        return earliest_date

    def return_time_to_reach_amount(self, amount: float, num_of_months=6):
        """ Calculates the time to reach a certain amount based on the trendline from the previous few months"""
        # TODO: Complete this one
        return {'time': 0.0}

    def get_absolute_url(self):
        return reverse('finances:account_overview', args=[self.pk])

    def __str__(self):
        return self.name


class Withdrawal(models.Model):
    """ Withdrawal for a given account.

    """
    date = models.DateField(default=now)
    description = models.CharField(max_length=250)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.FloatField(verbose_name='Amount')


class Deposit(models.Model):
    """ Deposit for a given account.

    """
    date = models.DateField(default=now)
    description = models.CharField(max_length=250)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.FloatField(verbose_name='Amount')


class Transfer(models.Model):
    """ Transfer of money from account 1 to account 2. """

    date = models.DateField(default=now)
    description = models.CharField(max_length=250)
    account_from = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='from_account')
    account_to = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='to_account')
    amount = models.FloatField(verbose_name='Amount')

    def save(self, *args, **kwargs):
        withdrawal_obj = Withdrawal.objects.create(date=self.date,
                                                   description=self.description,
                                                   account=self.account_from,
                                                   amount=self.amount)
        deposit_obj = Deposit.objects.create(date=self.date,
                                             description=self.description,
                                             account=self.account_to,
                                             amount=self.amount)
        withdrawal_obj.save()
        deposit_obj.save()
        self.save(*args, **kwargs)


class TradingAccount(Account):
    """ Account with trading stocks.

        Functions:
        get_roi - Calculates the return on interest based on the prior number of months.
        get_time_to_reach_amount - Calculates the date at which a goal amount is reached .
        estimate_balance_month_year - Calculates the balance the account will have a certain number of months and years
         after a certain point in time.
        """

    def get_roi(self, num_of_months=6):
        """ Calculates the return on interest based on the prior number of months.

            Returns rate of change (% / month)
        """
        # Get the rolling average of the last num_of_months worth of data
        latest_date = self.return_latest_date()
        earliest_date = latest_date + relativedelta(months=-1 * num_of_months)

        # Use that information to then calculate effective interest based on account balance
        earliest_balance = self.return_balance_up_to_month_year(earliest_date.strftime('%B'),
                                                                int(earliest_date.strftime('%Y')))
        latest_balance = self.return_balance_up_to_month_year(latest_date.strftime('%B'),
                                                              int(latest_date.strftime('%Y')))

        roi = (latest_balance - earliest_balance) / num_of_months * 100

        return roi

    def get_time_to_reach_amount(self, amount: float, num_of_months=6):
        """ Calculate the amount of time it will take to reach a financial goal.

        Defaults to using the last six months' worth of data.
            y = mx + b
        where:
            x = seconds after epoch
            y = amount
            m = amount per second
            b = amount at time 0

        b will be calculated by taking the amount at y1 and subtracting m*x1
        From there, the value of x will be determined for the requested amount
            x = (y-b)/m
            """
        balance = self.return_balance()
        epoch = datetime(1970, 1, 1)
        latest_date = self.return_latest_date()
        latest_date_to_seconds = (latest_date - epoch).total_seconds()
        previous_date = latest_date + relativedelta(months=-1 * num_of_months)
        previous_date_to_seconds = (previous_date - epoch).total_seconds()
        balance_previous = self.return_balance_up_to_month_year(previous_date.strftime('%B'),
                                                                previous_date.stftime('%Y'))
        m = (balance - balance_previous) / (latest_date_to_seconds - previous_date_to_seconds)
        b = balance_previous - m * previous_date_to_seconds
        time_to_reach = (amount - b) / m

        return time_to_reach

    def estimate_balance_month_year(self, month: str, year: int, num_of_years=0, num_of_months=6):
        """Estimates the total amount at a certain point in time based on the balance trend.

            Returns:
                dictionary with beginning date, beginning balance, end date, and end balance
        """
        balance = self.return_balance_up_to_month_year(month, year)
        roi = self.get_roi(num_of_months)
        date = datetime.strptime(f'{month}-01-{year}', '%B-%d-%Y')
        tot_months = num_of_years * 12 + num_of_months
        end_date = date + relativedelta(num_of_months=tot_months)
        json_return = {'beginning date': date, 'beginning balance': balance, 'end date': end_date}

        while date <= end_date:
            balance = balance + balance * roi / 100.0
            date = date + relativedelta(months=+1)

        json_return['end balance'] = balance

        return json_return

    def get_absolute_url(self):
        return reverse('finances:taccount_overview', args=[self.pk])

class RetirementAccount(Account):
    """ 401k, IRA, HSA

        Given that these are retirement accounts, the additional functions add withdrawal rates into the equations.

        Variables:
        yearly_withdrawal_rate - Withdrawal rate per year, in percentage (default = 4.0)
        target_amount - Target amount for account to have at retirement

        Functions:
        return_balance_month_year_with_yearly_withdrawal - Returns the balance as a function of time with a yearly withdrawal rate
    """
    yearly_withdrawal_rate = models.DecimalField(verbose_name='Withdrawal Rate in Percentage',
                                                 max_digits=5, decimal_places=2, default=4.0)
    target_amount = models.DecimalField(verbose_name='Target Amount at Retirement', max_digits=12, decimal_places=2)

    def get_roi(self, num_of_months):
        """ Calculates the return on interest based on the prior number of months.

            Returns rate of change (% / month)
        """
        # Get the rolling average of the last num_of_months worth of data
        latest_date = self.return_latest_date()
        earliest_date = latest_date + relativedelta(months=-1 * num_of_months)

        # Use that information to then calculate effective interest based on account balance
        earliest_balance = self.return_balance_up_to_month_year(earliest_date.strftime('%B'),
                                                                int(earliest_date.strftime('%Y')))
        latest_balance = self.return_balance_up_to_month_year(latest_date.strftime('%B'),
                                                              int(latest_date.strftime('%Y')))

        roi = (latest_balance - earliest_balance) / num_of_months * 100

        return roi

    def estimate_balance_month_year(self, month: str, year: int, num_of_years=0, num_of_months=6):
        """ Performs a linear interpolation of balance vs time given the average of the last entries in the account

        By default uses data from six months before the requested month/year for the extrapolation.

         f(x) = y1 + ((x ??? x1) / (x2 ??? x1)) * (y2 ??? y1)

        TODO: Account for withdrawal rate when the date is above the retirement date.
        """
        req_date = datetime.strptime(f'{month}, 1, {year}', '%B, %d, %Y')
        req_date_seconds_epoch = req_date.timestamp()  # x

        latest_date = self.return_latest_date()
        latest_date_seconds_epoch = latest_date.timestamp()  # x2
        latest_date_month = latest_date.strftime('%B')
        latest_date_year = latest_date.strftime('%Y')
        balance_at_latest_date = self.return_balance_up_to_month_year(latest_date_month, latest_date_year)  # y2

        time_prior = latest_date + relativedelta(years=-1 * num_of_years) + relativedelta(months=-1 * num_of_months)
        time_prior_seconds_epoch = time_prior.timestamp()  # x1
        time_prior_month = time_prior.strftime('%B')
        time_prior_year = time_prior.strftime('%Y')
        balance_at_time_prior = self.return_balance_up_to_month_year(time_prior_month, time_prior_year)  # y1

        estimated_balance = balance_at_time_prior + (req_date_seconds_epoch - time_prior_seconds_epoch) * (
                balance_at_latest_date - balance_at_time_prior) / (
                                    latest_date_seconds_epoch - time_prior_seconds_epoch)

        return estimated_balance

    def return_balance_month_year(self, month, year):
        """Calculates the balance at a certain point in time, but includes a withdrawal based on the user input."""
        # TODO: Fill this one
        return 0.0

    def return_withdrawal_info(self, retirement_date: datetime,
                               yearly_withdrawal_pct: float,
                               age_at_retirement=65,
                               expected_death_age=85):
        """Estimates the balance in the retirement account given a yearly withdrawal.


        """
        balances_at_date = {
            'date': [],
            'balance': []
        }
        date_after_retirement = retirement_date
        date_at_death = retirement_date + relativedelta(years=expected_death_age - age_at_retirement)
        monthly_withdrawal_pct = yearly_withdrawal_pct / 12.0
        retirement_month = retirement_date.strftime('%B')
        retirement_year = retirement_date.strftime('%Y')
        balance = self.return_balance_month_year(retirement_month, retirement_year)
        balances_at_date['date'].append(date_after_retirement)
        balances_at_date['balance'].append(balance)

        while date_after_retirement < date_at_death:
            # Balance will be reduced by the monthly withdrawal pct
            balance = (100.0 - monthly_withdrawal_pct) / 100.0 * balance

            # Balance increased by the monthly interest rate
            balance = (100.0 + self.monthly_interest_rate) / 100.0 * balance

            date_after_retirement = date_after_retirement + relativedelta(months=+1)

            balances_at_date['date'].append(date_after_retirement)
            balances_at_date['balance'].append(balance)

        return balances_at_date

    def get_time_to_reach_amount(self, amount: float):
        pass

    def get_absolute_url(self):
        return reverse('finances:raccount_overview', args=[self.pk])


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
        try:
            withdrawalobj = Withdrawal.objects.get(account=self.account,
                                                   date=self.date,
                                                   description=self.description)
        except Withdrawal.DoesNotExist:
            withdrawalobj = Withdrawal.objects.create(account=self.account,
                                                      date=self.date,
                                                      description=self.description,
                                                      amount=self.amount)
        else:
            withdrawalobj.amount = self.amount
        withdrawalobj.save()
        super(Expense, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('finances:expense_overview', args=[self.pk])

    class Meta:
        unique_together = ['account', 'date', 'description', 'amount']


class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    category = models.CharField(max_length=128)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    # Optional group for any specific purpose (e.g., vacation in Hawaii)
    group = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return "{} on {} - {}".format(self.description, self.date, self.amount)

    def save(self, *args, **kwargs):
        try:
            depositobj = Deposit.objects.get(account=self.account,
                                             date=self.date,
                                             description=self.description)
        except Deposit.DoesNotExist:
            depositobj = Deposit.objects.create(account=self.account,
                                                date=self.date,
                                                description=self.description,
                                                amount=self.amount)
        else:
            depositobj.amount = self.amount

        depositobj.save()
        super(Income, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('finances:income_overview', args=[self.pk])

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
        self.month = self.Date.strftime('%B')
        self.year = int(self.Date.strftime('%Y'))
        super(MonthlyBudget, self).save(*args, **kwargs)

    def __str__(self):
        return "{}'s budget for {}, {}".format(self.user, self.month, self.year)

    def get_absolute_url(self):
        return reverse('finances:mbudget_overview', args=[self.pk])

    class Meta:
        unique_together = ['month', 'year']
