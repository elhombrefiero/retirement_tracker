from django.db import models
from django.db.models import Sum, Max, F, Window
from django.db.models.functions import TruncDay
from django.utils.timezone import now, get_current_timezone
from django.utils.text import slugify
from django.shortcuts import reverse
import numpy as np
import scipy.interpolate

from datetime import date, timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta

BUDGET_GROUP_CHOICES = (
    ('Mandatory', 'Mandatory'),
    ('Mortgage', 'Mortgage'),
    ('Debts, Goals, Retirement', 'Debts, Goals, Retirement'),
    ('Discretionary', 'Discretionary'),
)
BUDGET_GROUP_MANDATORY = BUDGET_GROUP_CHOICES[0][0]
BUDGET_GROUP_MORTGAGE = BUDGET_GROUP_CHOICES[1][0]
BUDGET_GROUP_DGR = BUDGET_GROUP_CHOICES[2][0]
BUDGET_GROUP_DISC = BUDGET_GROUP_CHOICES[3][0]

def dt_to_milliseconds_after_epoch(dt):
    """ Converts a given datetime to milliseconds after epoch.
    This is used in place of timestamp due to limitations on RPi
    """
    # In case dt does not have timezone information
    cur_tz = get_current_timezone()
    dt_ = dt.replace(tzinfo=cur_tz)
    epoch_dt = datetime.fromtimestamp(0, tz=cur_tz)
    tdelta = dt_ - epoch_dt
    return tdelta.total_seconds()*1000

class User(models.Model):
    """ User class for the retirement tracker.

    Attributes:
    Username
    User DOB
    Retirement Age

    DB Related Attributes:
    Checking Accounts
    Trading Accounts (Stocks)
    Retirement Account
    Debt Account
    Monthly Budgets

    Functions:
    return_retirement_timestamp
    estimate_retirement_finances
    estimate_budget_for_month_year
    get_total_for_month_year
    get_cumulative_incomes_expenses
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

    # TODO: Determine way to generate input files for sankey diagram and add button to open sankey page with the
    #  inputs. Or through monthly budget portions and expenses.

    def return_net_worth(self) -> (float, float, float, float, float):
        """ Returns the user net worth and totals for all accounts:
            -checking,
            -retirement, and
            -trading accounts

            All are calculated up to today's date
        """

        today = now()
        month = today.strftime('%B')
        year = today.strftime('%Y')

        tot_checking, tot_retirement, tot_trading, tot_debt, net_worth = self.return_net_worth_month_year(month, year)

        return round(tot_checking, 2), round(tot_retirement, 2), round(tot_trading, 2), round(tot_debt, 2), round(
            net_worth, 2)

    def needs_monthly_budget(self, month, year):
        """ Checks whether the user should update a monthly budget at the given month/year combo.

        Returns True if no monthly budget exists or if any monthly budget designations are 0.0."""

        try:
            mb_check = MonthlyBudget.objects.get(user=self, month=month, year=year)
        except MonthlyBudget.DoesNotExist:
            return True

        if mb_check.mandatory == 0.0 or mb_check.mortgage == 0.0 or mb_check.debts_goals_retirement == 0.0 or mb_check.discretionary == 0.0:
            return True

        return False

    def return_net_worth_month_year(self, month: str, year: int) -> (float, float, float, float):
        """ Returns the net worth of the user at a given point in time."""
        tot_checking = 0.0
        tot_retirement = 0.0
        tot_trading = 0.0
        tot_debt = 0.0

        user_checking_accts = self.return_checking_accts()
        user_ret_accts = [acct for acct in RetirementAccount.objects.filter(user=self)]
        user_trade_accts = [acct for acct in TradingAccount.objects.filter(user=self)]
        user_debt_accts = [acct for acct in DebtAccount.objects.filter(user=self)]

        for account in user_checking_accts:
            tot_checking += account.return_balance_including_month_year(month, year)

        for account in user_ret_accts:
            tot_retirement += account.return_balance_including_month_year(month, year)

        for account in user_trade_accts:
            tot_trading += account.return_balance_including_month_year(month, year)

        for account in user_debt_accts:
            tot_debt += account.return_balance_including_month_year(month, year)

        net_worth = tot_checking + tot_retirement + tot_trading - tot_debt

        return round(tot_checking, 2), round(tot_retirement, 2), round(tot_trading, 2), round(tot_debt, 2), round(
            net_worth, 2)

    def estimate_net_worth_month_year(self, month: str, year: int) -> (float, float, float, float):
        """ Returns the net worth of the user at a given point in time."""
        tot_checking = 0.0
        tot_retirement = 0.0
        tot_trading = 0.0
        tot_debt = 0.0

        user_checking_accts = [acct for acct in CheckingAccount.objects.filter(user=self)]
        user_ret_accts = [acct for acct in RetirementAccount.objects.filter(user=self)]
        user_trade_accts = [acct for acct in TradingAccount.objects.filter(user=self)]
        user_debt_accts = [acct for acct in DebtAccount.objects.filter(user=self)]

        for account in user_checking_accts:
            tot_checking += account.estimate_balance_month_year(month, year)

        for account in user_ret_accts:
            tot_retirement += account.estimate_balance_month_year(month, year)

        for account in user_trade_accts:
            tot_trading += account.estimate_balance_month_year(month, year)

        for account in user_debt_accts:
            tot_debt += account.estimate_balance_month_year(month, year)

        net_worth = tot_checking + tot_retirement + tot_trading - tot_debt

        return round(tot_checking, 2), round(tot_retirement, 2), round(tot_trading, 2), \
            round(tot_debt, 2), round(net_worth, 2)

    def return_statutory_including_month_year(self, month, year):
        """ Returns the total statutory for the user up to the end of the requested month and year"""

        datetime_inclusive = datetime.strptime(f'{year}-{month}-01', '%Y-%B-%d')
        datetime_inclusive = datetime_inclusive + relativedelta(months=+1)

        all_stat = self.return_statutory_up_to_month_year(datetime_inclusive.strftime('%B'), datetime_inclusive.year)

        return all_stat

    def return_statutory_up_to_month_year(self, month, year):
        """ Returns the statutory up to the end of the month and year"""

        up_to_datetime = datetime.strptime(f'{year}-{month}-01', '%Y-%B-%d')
        up_to_datetime = up_to_datetime + relativedelta(seconds=-1)

        all_stat = Statutory.objects.filter(user=self, date__lt=up_to_datetime)
        all_stat = all_stat.aggregate(total=Sum('amount'))['total']
        all_stat = all_stat if all_stat is not None else 0.0

        return round(float(all_stat), 2)

    def return_net_worth_year(self, year: int):

        tot_checking, tot_retirement, tot_trading, tot_debt, net_worth = self.return_net_worth_month_year('December',
                                                                                                          year)
        return tot_checking, tot_retirement, tot_trading, tot_debt, net_worth

    def return_net_worth_at_retirement(self):
        ret_date = self.return_retirement_datetime()
        ret_date = ret_date + relativedelta(months=+1)

        ret_month = ret_date.strftime('%B')
        ret_year = int(ret_date.strftime('%Y'))

        tot_checking, tot_retirement, tot_trading, tot_debt, net_worth = self.return_net_worth_month_year(ret_month,
                                                                                                          ret_year)

        return tot_checking, tot_retirement, tot_trading, tot_debt, net_worth

    def estimate_net_worth_at_retirement(self):
        ret_date = self.return_retirement_datetime()
        ret_date = ret_date + relativedelta(months=+1)

        ret_month = ret_date.strftime('%B')
        ret_year = int(ret_date.strftime('%Y'))

        tot_checking, tot_retirement, tot_trading, tot_debt, net_worth = self.estimate_net_worth_month_year(ret_month,
                                                                                                            ret_year)

        return tot_checking, tot_retirement, tot_trading, tot_debt, net_worth
    def return_retirement_datetime(self):
        """ Returns the timestamp at retirement age. """
        num_months = int(float(self.retirement_age) * 12.0)
        ret_datetime = self.date_of_birth + relativedelta(months=num_months)
        return ret_datetime

    def return_checking_acct_total(self):
        tot_checking_amt = 0.0
        checking_accounts = self.return_checking_accts()

        for account in checking_accounts:
            tot_checking_amt += account.return_balance()

        return tot_checking_amt

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

    def return_debt_acct_total(self):
        tot_debt_amt = 0.0
        user_debt_accts = DebtAccount.objects.filter(user=self)

        for acct in user_debt_accts:
            tot_debt_amt += acct.return_balance()

        return tot_debt_amt

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
        expenses = Withdrawal.objects.filter(account=checking_accts, date__lt=beg_of_month_year)
        mand_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_MANDATORY)
        mort_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_MORTGAGE)
        dgr_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_DGR)
        disc_exp = expenses.filter(user=self, budget_group__eq=BUDGET_GROUP_DISC)

        mand_tot = mand_exp.aggregate(total=Sum('amount'))['total']
        mort_tot = mort_exp.aggregate(total=Sum('amount'))['total']
        dgr_tot = dgr_exp.aggregate(total=Sum('amount'))['total']
        disc_tot = disc_exp.aggregate(total=Sum('amount'))['total']

        # Get the budget group totals up to current month/year
        mbudgets = MonthlyBudget.objects.filter(user=self, date__lt=beg_of_month_year)
        budget_mand_tot = mbudgets.aggregate(total=Sum('mandatory'))['total']
        budget_mort_tot = mbudgets.aggregate(total=Sum('mortgage'))['total']
        budget_dgr_tot = mbudgets.aggregate(total=Sum('debts_goals_retirement'))['total']
        budget_disc_tot = mbudgets.aggregate(total=Sum('discretionary'))['total']

        # Subtract the expenses from the budgets
        mand_balance = budget_mand_tot - mand_tot
        mort_balance = budget_mort_tot - mort_tot
        dgr_balance = budget_dgr_tot - dgr_tot
        disc_balance = budget_disc_tot - disc_tot

        balances = {'mandatory': mand_balance,
                    'mortgage': mort_balance,
                    'dgr': dgr_balance,
                    'discretionary': disc_balance}
        return balances

    def return_checking_accts(self):
        """ Returns only the checking account objects"""

        user_accounts = CheckingAccount.objects.filter(user=self)

        return user_accounts

    def return_all_accounts(self):

        all_accounts = Account.objects.filter(user=self)
        return all_accounts

    def return_top_items(self, month, year, expense_filter, num_of_entries=5):
        """ Returns the top expenses from the checking accounts based on given input parameters. """
        checking_accounts = self.return_checking_accts()
        beg_of_month = datetime.strptime(f'{month}, 1, {year}', '%B, %d, %Y')
        end_of_month = beg_of_month + relativedelta(months=+1, seconds=-1)
        expenses = Withdrawal.objects.filter(account__in=checking_accounts,
                                             date__gte=beg_of_month, date__lt=end_of_month)
        expenses = expenses.exclude(budget_group=BUDGET_GROUP_MORTGAGE)
        filtered_expenses = expenses.values(expense_filter).distinct().annotate(sum=Sum('amount'))
        filtered_expenses = filtered_expenses.order_by('-sum')[:num_of_entries]
        return filtered_expenses

    def return_top_category(self, month, year, num_of_entries=5):
        """ Finds the maximum expenses by category. By default, finds the top five for a given month/year"""
        category_expenses = self.return_top_items(month, year, 'category', num_of_entries)

        return category_expenses

    def return_top_description(self, month, year, num_of_entries=5):
        """ Finds the maximum expenses by category. By default, finds the top five for a given month/year"""
        description_expenses = self.return_top_items(month, year, 'description', num_of_entries)

        return description_expenses

    def return_top_location(self, month, year, num_of_entries=5):
        """ Finds the maximum expenses by category. By default, finds the top five for a given month/year"""
        location_expenses = self.return_top_items(month, year, 'location', num_of_entries)

        return location_expenses

    def return_tot_expenses_by_budget_month_year(self, month, year) -> (float, float, float, float, float):
        """ Returns the checking expenses segregated by budget group.

        """
        checking_accts = self.return_checking_accts()
        beg_of_month = datetime.strptime(f'{month}, 1, {year}', '%B, %d, %Y')
        end_of_month = beg_of_month + relativedelta(months=+1, seconds=-1)

        expenses = Withdrawal.objects.filter(account__in=checking_accts,
                                             date__gte=beg_of_month, date__lt=end_of_month)

        mand_exp = expenses.filter(budget_group__contains=BUDGET_GROUP_MANDATORY).aggregate(total=Sum('amount'))[
            'total']
        mand_exp = float(mand_exp) if mand_exp is not None else 0.0
        mort_exp = expenses.filter(budget_group__contains=BUDGET_GROUP_MORTGAGE).aggregate(total=Sum('amount'))[
            'total']
        mort_exp = float(mort_exp) if mort_exp is not None else 0.0
        dgr_exp = expenses.filter(budget_group__contains=BUDGET_GROUP_DGR).aggregate(total=Sum('amount'))[
            'total']
        dgr_exp = float(dgr_exp) if dgr_exp is not None else 0.0
        disc_exp = expenses.filter(budget_group__contains=BUDGET_GROUP_DISC).aggregate(total=Sum('amount'))[
            'total']
        disc_exp = float(disc_exp) if disc_exp is not None else 0.0
        stat_exp = \
            Statutory.objects.filter(user=self, date__gte=beg_of_month, date__lt=end_of_month).aggregate(
                total=Sum('amount'))[
                'total']
        stat_exp = float(stat_exp) if stat_exp is not None else 0.0

        return round(mand_exp, 2), round(mort_exp, 2), \
            round(dgr_exp, 2), round(disc_exp, 2), \
            round(stat_exp, 2)

    def estimate_budget_for_month_year(self, month: str, year: int):
        """ Estimates and sets monthly budget values based on takehome pay and budget expenses."""

        # Get accounts associated with the user
        user_accounts = self.return_checking_accts()
        statutory = self.return_statutory_month_year(month, year)

        # Get the total income from base accounts for the current month/year
        total_income = 0.0
        for account in user_accounts:
            total_income += account.return_income_month_year(month, year)

        takehome = total_income - statutory
        budget_mort = takehome * self.DEFAULT_MORTGAGE_BUDGET_PCT / 100.0
        budget_mand = takehome * self.DEFAULT_MANDATORY_BUDGET_PCT / 100.0
        budget_dgr = takehome * self.DEFAULT_DGR_BUDGET_PCT / 100.0
        budget_disc = takehome * self.DEFAULT_DISC_BUDGET_PCT / 100.0

        return round(float(budget_mand), 2), round(float(budget_mort), 2), round(float(statutory), 2), round(
            float(budget_dgr), 2), round(float(budget_disc), 2)

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
        stat_expenses = self.return_statutory_month_year(month, year)
        user_accounts = self.return_checking_accts()
        for acct in user_accounts:
            income += acct.return_income_month_year(month, year)

        return round(income - stat_expenses, 2)

    def return_statutory_month_year(self, month: str, year: int):
        start_datetime = datetime.strptime(f'{month}-1-{year}', '%B-%d-%Y')
        end_datetime = start_datetime + relativedelta(months=+1, seconds=-1)

        month_expense = Statutory.objects.filter(user=self, date__gte=start_datetime, date__lte=end_datetime)
        month_expense = month_expense.aggregate(total=Sum('amount'))['total']
        month_expense = month_expense if month_expense is not None else 0.0

        return float(month_expense)

    def set_budget_month_year(self, month, year, budget_mand, budget_mort, budget_dgr, budget_disc):
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

        mbudget.save()

    def get_earliest_retirement_date(self):
        """ Returns the date at which the user is eligible for early retirement.

        Assumes the age 59.5 (i.e., 714 months) based on 2022 rules."""

        earliest_rt = self.date_of_birth + relativedelta(months=+714)
        return earliest_rt

    def get_latest_retirement_date(self):
        """ Returns the latest date the user can retire.

        70 years based on ssn.gov"""

        latest_rt_dt = self.date_of_birth + relativedelta(months=840)
        return latest_rt_dt

    def get_absolute_url(self):
        return reverse('user_overview', args=[self.pk])

    def get_earliest_latest_dates(self):
        all_user_accts = self.return_all_accounts()
        user_expenses = Withdrawal.objects.filter(account__in=all_user_accts)
        user_incomes = Deposit.objects.filter(account__in=all_user_accts)
        user_earliest = min(user_expenses.earliest('date').date,
                            user_incomes.earliest('date').date)
        user_latest = max(user_expenses.latest('date').date,
                          user_incomes.latest('date').date)

        return user_earliest, user_latest

    def return_year_month_for_reports(self):
        """ Returns a dictionary of months and years for the user reports

            year_date = {
                2022 = [November, December]
                2023 = [January, February, March]
                }
        """
        earliest, latest = self.get_earliest_latest_dates()
        mydate = earliest
        return_dates = {}
        while mydate <= latest:
            year = mydate.year
            month = datetime.strptime(str(mydate.month), '%m').strftime('%B')
            if year not in return_dates.keys():
                return_dates[year] = []
            return_dates[year].append(month)
            mydate = mydate + relativedelta(months=+1)

        return return_dates

    def return_year_month_for_monthly_budgets(self):
        """ Returns a dictionary of months and years for the user's monthly budgets.
        The return data is formatted as such:

        year_month = {
            year<int>: [
                month: {name: January}
                ]
            }
        """
        user_monthly_budgets = MonthlyBudget.objects.filter(user=self)
        earliest = user_monthly_budgets.earliest('date').date
        latest = user_monthly_budgets.latest('date').date
        year_month = {}
        mydate = earliest
        while mydate <= latest:
            year = mydate.year
            month = datetime.strptime(str(mydate.month), '%m').strftime('%B')
            if year not in year_month:
                year_month[year] = []
            year_month[year].append({'name': month})
            mydate = mydate + relativedelta(months=+1)
        return year_month

    def get_month_year_date_range(self):
        """ Used to get month/year pairings for the income/expense date range.

            Used to lookup user information for a specific year
        """
        earliest, latest = self.get_earliest_latest_dates()
        latest = latest + relativedelta(months=+1)  # Add month to encapsulate

        date_json = {}
        search_date = earliest

        while search_date <= latest:
            if search_date.year not in date_json:
                date_json[search_date.year] = list()
            date_json[search_date.year].append(search_date.strftime('%B'))

            search_date = search_date + relativedelta(months=+1)

        return date_json

    def return_cumulative_expenses(self, start_date, end_date, budget_group=None):
        """ Returns the cumulative expenses of all the checking accounts within a date range.

        The start date is inclusive whereas the end_date is not.
        Optional budget_group argument lets the user filter by budget_group.
        """
        # TODO: Account for the statutory expenses, if desired.

        user_checking = CheckingAccount.objects.filter(user=self)
        expenses = Withdrawal.objects.filter(account__in=user_checking,
                                             date__gte=start_date, date__lt=end_date)
        if budget_group:
            expenses = expenses.filter(budget_group=budget_group)

        summed_expenses = expenses.annotate(day=TruncDay('date')).values('day').annotate(cumsum=Sum('amount')).order_by(
            'date')
        total = 0.0
        cumulative_balance = dict()
        for summed_expense in summed_expenses:
            total += summed_expense['cumsum']
            cumulative_balance[summed_expense['day']] = total

        return cumulative_balance

    def return_cumulative_incomes(self, start_date, end_date):
        """ Returns the cumulative incomes of all the checking accounts within a date range.

        The start date is inclusive whereas the end_date is not.
        """

        user_checking = CheckingAccount.objects.filter(user=self)
        incomes = Deposit.objects.filter(account__in=user_checking,
                                         date__gte=start_date, date__lt=end_date)

        summed_incomes = incomes.annotate(day=TruncDay('date')).values('day').annotate(cumsum=Sum('amount')).order_by(
            'date')
        total = 0.0
        cumulative_balance = dict()
        for summed_income in summed_incomes:
            total += summed_income['cumsum']
            cumulative_balance[summed_income['day']] = total
        # cumulative_balance = incomes.annotate(cumsum=Window(Sum('amount'),
        #                                                     order_by=F('date').asc())).order_by('date', 'cumsum')

        return cumulative_balance

    def return_cumulative_total(self, start_date, end_date):
        """ Returns the cumulative total (income - expenses) of all the checking accounts within a date range.

        Start date is inclusive whereas the end_date is not.

        Return structure will be in the form of:
            cumulative[datetime]['cumulative'] = cumulative_amount
        """
        user_checking = CheckingAccount.objects.filter(user=self)
        incomes = Deposit.objects.filter(account__in=user_checking,
                                         date__gte=start_date, date__lt=end_date).order_by('date')
        expenses = Withdrawal.objects.filter(account__in=user_checking,
                                             date__gte=start_date, date__lt=end_date).order_by('date')

        # Put all incomes and expenses in a dictionary
        all_income_exp = {}
        for income in incomes:
            if income.date not in all_income_exp:
                all_income_exp[income.date] = dict()
                all_income_exp[income.date]['income'] = income.amount
            else:
                if 'income' not in all_income_exp[income.date]:
                    all_income_exp[income.date]['income'] = income.amount
                else:
                    all_income_exp[income.date]['income'] = all_income_exp[income.date]['income'] + income.amount

        for expense in expenses:
            if expense.date not in all_income_exp:
                all_income_exp[expense.date] = dict()
                all_income_exp[expense.date]['expense'] = expense.amount
            else:
                if 'expense' not in all_income_exp[expense.date]:
                    all_income_exp[expense.date]['expense'] = expense.amount
                else:
                    all_income_exp[expense.date]['expense'] = all_income_exp[expense.date]['expense'] + expense.amount

        # Iterate through the dictionary and add a total amount
        total = 0.0
        for date_key in sorted(all_income_exp.keys()):
            if 'income' in all_income_exp[date_key]:
                total = total + all_income_exp[date_key]['income']
            if 'expense' in all_income_exp[date_key]:
                total = total - all_income_exp[date_key]['expense']
            all_income_exp[date_key]['cumulative'] = total

        return all_income_exp

    def __str__(self):
        return self.name


class Account(models.Model):
    """ Base accounts for a given user.

    Name
    URL

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
    starting_balance = models.DecimalField(verbose_name='Starting balance in dollars', max_digits=9, decimal_places=2,
                                           default=0.0)
    monthly_interest_pct = models.DecimalField(verbose_name='Monthly interest in percent',
                                               max_digits=4, decimal_places=2, default=0.0)
    opening_date = models.DateField(verbose_name='Date where starting balance starts')
    url = models.URLField(verbose_name="Account URL", blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def return_balance(self):
        """ Calculates the balance for all time."""

        all_income = Deposit.objects.filter(account=self).aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0
        all_expense = Withdrawal.objects.filter(account=self).aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return round(float(self.starting_balance) + float(all_income) - float(all_expense), 2)

    def return_balance_year(self, year: int):
        start_datetime = datetime(year, 1, 1)
        end_datetime = datetime(year + 1, 1, 1) + relativedelta(seconds=-1)

        all_income = Deposit.objects.filter(account=self, date__ge=start_datetime, date__lt=end_datetime)
        all_income = all_income.aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0

        all_expense = Withdrawal.objects.filter(account=self, date__ge=start_datetime, date__lt=end_datetime)
        all_expense = all_expense.aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return round(float(self.starting_balance) + float(all_income) - float(all_expense), 2)

    def return_balance_month_year(self, month: str, year: int):
        """ Gets the total balance of the account for a given month"""

        month_income = self.return_income_month_year(month, year)

        month_expense = self.return_expense_month_year(month, year)

        return round(float(month_income) - float(month_expense), 2)

    def return_income_month_year(self, month: str, year: int):
        start_datetime = datetime.strptime(f'{month}-1-{year}', '%B-%d-%Y')
        end_datetime = start_datetime + relativedelta(months=+1, seconds=-1)

        month_income = Deposit.objects.filter(account=self, date__gte=start_datetime, date__lte=end_datetime)
        month_income = month_income.aggregate(total=Sum('amount'))['total']
        month_income = month_income if month_income is not None else 0.0

        return float(month_income)

    def return_expense_month_year(self, month: str, year: int):
        start_datetime = datetime.strptime(f'{month}-1-{year}', '%B-%d-%Y')
        end_datetime = start_datetime + relativedelta(months=+1, seconds=-1)

        month_expense = Withdrawal.objects.filter(account=self, date__gte=start_datetime, date__lte=end_datetime)
        month_expense = month_expense.aggregate(total=Sum('amount'))['total']
        month_expense = month_expense if month_expense is not None else 0.0

        return float(month_expense)

    def return_balance_up_to_month_year(self, month: str, year: int):
        """ Returns the balance up to the start of the given month and year.

        For example, a lookup of July 2020 will return the balance up to 11:59pm on June, 30, 2020 """

        up_to_datetime = datetime.strptime(f'{year}-{month}-01', '%Y-%B-%d')
        up_to_datetime = up_to_datetime + relativedelta(seconds=-1)

        all_income = Deposit.objects.filter(account=self, date__lt=up_to_datetime)
        all_income = all_income.aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0

        all_expense = Withdrawal.objects.filter(account=self, date__lt=up_to_datetime)
        all_expense = all_expense.aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return round(float(self.starting_balance) + float(all_income) - float(all_expense), 2)

    def return_balance_including_month_year(self, month: str, year: int):
        """ Returns the balance up to the end of the requested month/year"""
        datetime_inclusive = datetime.strptime(f'{year}-{month}-01', '%Y-%B-%d')
        datetime_inclusive = datetime_inclusive + relativedelta(months=+1)

        balance = self.return_balance_up_to_month_year(datetime_inclusive.strftime('%B'), datetime_inclusive.year)

        return balance

    def return_time_vs_value_function(self, num_of_years=0, num_of_months=6, kind='slinear', fill_value='extrapolate'):
        """ Returns a function of time vs cumulative amount for the given account.

        """

        dates = np.empty(0)
        balances = np.empty(0)

        latest_date = self.return_latest_date()
        if latest_date is None:  # Not enough data to calculate a trend, so just return a function that always returns zero
            dates = np.arange(1, 10)
            balances = dates * 0.0
            f = scipy.interpolate.interp1d(balances, dates, kind=kind, fill_value=fill_value)
            return f
        first_date = latest_date + relativedelta(years=-1 * num_of_years, months=-1 * num_of_months)

        current_date = first_date

        # Captures the balance up to the end of the month for the month selected
        while current_date <= latest_date:
            month_name = datetime.strptime(str(current_date.month), '%m').strftime('%B')
            year = current_date.year
            balance = self.return_balance_up_to_month_year(month_name, year)
            # Avoid duplicate x values
            if balance not in balances:
                dtime = datetime.strptime(f'{month_name}-1-{year}', '%B-%d-%Y')
                dt_ts = dt_to_milliseconds_after_epoch(dtime)
                dates = np.append(dates, dt_ts)
                balances = np.append(balances, balance)
            current_date = current_date + relativedelta(months=+1)

        # Once all data is filled, calculate the balance as a function of ordinal
        f = scipy.interpolate.interp1d(balances, dates, kind=kind, fill_value=fill_value)

        return f

    def return_value_vs_time_function(self, num_of_years=0, num_of_months=6, kind='slinear', fill_value='extrapolate',
                                      months_into_future=None):
        """ Returns a function of cumulative amount vs time for the given account.

            Looks at the final data entry and then traverses back depending on the input arguments.

            Fills two numpy arrays (dates and balances) with data based on the input arguments.

            Uses the data with the scipy interpolate interp1d to return a function that
            can be called to extrapolate the balance up to a certain point in time.
        """

        dates = np.empty(0)
        balances = np.empty(0)

        latest_date = self.return_latest_date()
        if latest_date is None:  # Not enough data to calculate a trend, so just return a function that always returns zero
            dates = np.arange(1, 10)
            balances = dates * 0.0
            f = scipy.interpolate.interp1d(dates, balances, kind=kind, fill_value=fill_value)
            return f

        first_date = latest_date + relativedelta(years=-1 * num_of_years, months=-1 * num_of_months)

        if months_into_future:
            latest_date += relativedelta(months=months_into_future)

        current_date = first_date

        # Captures the balance up to the end of the month for the month selected
        while current_date <= latest_date:
            month_name = datetime.strptime(str(current_date.month), '%m').strftime('%B')
            year = current_date.year
            balance = self.return_balance_up_to_month_year(month_name, year)
            dtime = datetime.strptime(f'{month_name}-1-{year}', '%B-%d-%Y')
            dt_ts = dt_to_milliseconds_after_epoch(dtime)
            dates = np.append(dates, dt_ts)
            balances = np.append(balances, balance)
            current_date = current_date + relativedelta(months=+1)

        # Once all data is filled, calculate the balance as a function of ordinal
        f = scipy.interpolate.interp1d(dates, balances, kind=kind, fill_value=fill_value)

        return f

    def estimate_balance_month_year(self, month: str, year: int, num_of_years=0, num_of_months=6, kind='slinear',
                                    fill_value='extrapolate'):
        """ Performs an interpolation of balance vs time using the data of the last entries in the account

        By default, uses data from six months before the requested month/year for the extrapolation.

        """

        req_date_dt = datetime.strptime(f'{month}, 1, {year}', '%B, %d, %Y')
        req_date_ts = dt_to_milliseconds_after_epoch(req_date_dt)

        f = self.return_value_vs_time_function(num_of_years, num_of_months, kind=kind, fill_value=fill_value)

        y = float(f(req_date_ts))

        return y

    def return_latest_date(self):
        """ Looks at all entries and determines the latest database date for the account."""
        try:
            latest_withdrawal_date = Withdrawal.objects.filter(account=self).latest('date').date
        except Withdrawal.DoesNotExist:
            latest_withdrawal_date = None
        try:
            latest_deposit_date = Deposit.objects.filter(account=self).latest('date').date
        except Deposit.DoesNotExist:
            latest_deposit_date = None

        if latest_withdrawal_date and latest_deposit_date:
            return max(latest_deposit_date, latest_withdrawal_date)
        if latest_withdrawal_date is None:
            return latest_deposit_date
        else:
            return latest_withdrawal_date

    def return_earliest_date(self):
        """ Looks at all entries and determines the latest database date for the account."""
        earliest_withdrawal_date = Withdrawal.objects.filter(account=self).earliest('date').date
        earliest_deposit_date = Deposit.objects.filter(account=self).earliest('date').date

        earliest_date = min(earliest_deposit_date, earliest_withdrawal_date)
        return earliest_date

    def return_time_to_reach_amount(self, amount: float, num_of_years=0, num_of_months=6):
        """ Calculates the time to reach a certain amount based on the trendline from the previous few months

        Uses the scipy.interp.interp1d to perform a linear interpolation of time vs account balance

        """

        f = self.return_time_vs_value_function(num_of_years=num_of_years, num_of_months=num_of_months)

        time_to_reach = f(amount)  # This is in milliseconds after epoch

        time_to_reach_secs = time_to_reach / 1000

        time_to_reach_dt = datetime.fromtimestamp(time_to_reach_secs)

        return time_to_reach_dt

    def get_absolute_url(self):
        return reverse('account_overview', args=[self.pk])

    def __str__(self):
        return self.name


class CheckingAccount(Account):
    """ Checking account for User"""


class DebtAccount(Account):
    """ Debt Account for User

        Similar to a trading account.
    """
    yearly_interest_pct = models.DecimalField(verbose_name='Yearly interest in percent',
                                              max_digits=4, decimal_places=2, default=0.0)

    def return_date_debt_paid(self):
        return self.return_time_to_reach_amount(0.0)

    def return_balance(self):
        all_income = Deposit.objects.filter(account=self).aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0
        all_expense = Withdrawal.objects.filter(account=self).aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return max(round(float(self.starting_balance) - float(all_income) + float(all_expense), 2), 0)

    def return_balance_year(self, year: int):
        start_datetime = datetime(year, 1, 1)
        end_datetime = datetime(year + 1, 1, 1) + relativedelta(seconds=-1)

        all_income = Deposit.objects.filter(account=self, date__ge=start_datetime, date__lt=end_datetime)
        all_income = all_income.aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0

        all_expense = Withdrawal.objects.filter(account=self, date__ge=start_datetime, date__lt=end_datetime)
        all_expense = all_expense.aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return max(round(float(self.starting_balance) - float(all_income) + float(all_expense), 2), 0)

    def return_balance_up_to_month_year(self, month: str, year: int):
        """ Returns the balance up to the end of the given month and year.

        For example, a lookup of July 2020 will return the balance up to 11:59pm on June, 30, 2020 """

        up_to_datetime = datetime.strptime(f'{year}-{month}-01', '%Y-%B-%d')
        up_to_datetime = up_to_datetime + relativedelta(seconds=-1)

        all_income = Deposit.objects.filter(account=self, date__lt=up_to_datetime)
        all_income = all_income.aggregate(total=Sum('amount'))['total']
        all_income = all_income if all_income is not None else 0.0

        all_expense = Withdrawal.objects.filter(account=self, date__lt=up_to_datetime)
        all_expense = all_expense.aggregate(total=Sum('amount'))['total']
        all_expense = all_expense if all_expense is not None else 0.0

        return max(round(float(self.starting_balance) - float(all_income) + float(all_expense), 2), 0)


class Withdrawal(models.Model):
    """ Withdrawal for a given account.

    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    budget_group = models.CharField(max_length=200, choices=BUDGET_GROUP_CHOICES)
    category = models.CharField(max_length=200)
    location = models.CharField(max_length=64)
    description = models.CharField(max_length=250)
    amount = models.FloatField(verbose_name='Amount')
    slug_field = models.SlugField(null=True, blank=True)
    # Optional group for any specific purpose (e.g., vacation in Hawaii)
    group = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ['account', 'date', 'amount', 'description']

    def __str__(self):
        return f"{self.description} at {self.location} on {self.date} - Account: {self.account.name} {self.budget_group} ${self.amount}"

    def save(self, *args, **kwargs):
        if not self.slug_field:
            self.slug_field = slugify(self.description)
        super(Withdrawal, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('withdrawal_overview', args=[self.pk])


class Deposit(models.Model):
    """ Deposit for a given account.

    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    category = models.CharField(max_length=128)
    description = models.CharField(max_length=250)
    location = models.CharField(max_length=64)
    amount = models.FloatField(verbose_name='Amount')
    slug_field = models.SlugField(null=True, blank=True)
    # Optional group for any specific purpose (e.g., vacation in Hawaii)
    group = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ['account', 'date', 'amount', 'description']

    def __str__(self):
        return f"{self.description} at {self.location} on {self.date} - Account: {self.account.name} ${self.amount}"

    def save(self, *args, **kwargs):
        if not self.slug_field:
            self.slug_field = slugify(self.description)
        super(Deposit, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('deposit_overview', args=[self.pk])


class Transfer(models.Model):
    """ Transfer of money from account 1 to account 2. """

    account_from = models.ForeignKey(Account, verbose_name='Account for Withdrawal (money coming from)',
                                     on_delete=models.CASCADE, related_name='from_account')
    account_to = models.ForeignKey(Account, verbose_name='Account for Deposit (money going to)',
                                   on_delete=models.CASCADE, related_name='to_account')
    date = models.DateField(default=now)
    budget_group = models.CharField(max_length=200, choices=BUDGET_GROUP_CHOICES)
    category = models.CharField(max_length=128)
    location = models.CharField(max_length=64)
    description = models.CharField(max_length=250)
    amount = models.FloatField(verbose_name='Amount')
    slug_field = models.SlugField(null=True, blank=True)
    # Optional group for any specific purpose (e.g., vacation in Hawaii)
    group = models.CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs):
        withdrawal_obj, created = Withdrawal.objects.get_or_create(account=self.account_from,
                                                                   date=self.date,
                                                                   amount=self.amount,
                                                                   description=self.description,
                                                                   defaults={'budget_group': self.budget_group,
                                                                             'category': self.category,
                                                                             'location': self.location,
                                                                             'slug_field': self.slug_field,
                                                                             'group': self.group})

        if not created:
            withdrawal_obj.budget_group = self.budget_group
            withdrawal_obj.category = self.category
            withdrawal_obj.location = self.location
            withdrawal_obj.slug_field = self.slug_field
            withdrawal_obj.group = self.group
            withdrawal_obj.save()

        deposit_obj, created = Deposit.objects.get_or_create(account=self.account_to,
                                                             date=self.date,
                                                             description=self.description,
                                                             amount=self.amount,
                                                             defaults={
                                                                 'category': self.category,
                                                                 'location': self.location,
                                                                 'slug_field': self.slug_field,
                                                                 'group': self.group
                                                             }
                                                             )
        if not created:
            deposit_obj.category = self.category
            deposit_obj.location = self.location
            deposit_obj.slug_field = self.slug_field
            deposit_obj.group = self.group
            deposit_obj.save()
        super(Transfer, self).save(*args, **kwargs)


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
        end_date = date + relativedelta(months=tot_months)
        json_return = {'beginning date': date, 'beginning balance': balance, 'end date': end_date}

        while date <= end_date:
            balance = balance + balance * roi / 100.0
            date = date + relativedelta(months=+1)

        json_return['end balance'] = balance

        return json_return

    def get_absolute_url(self):
        return reverse('taccount_overview', args=[self.pk])


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

    def estimate_balance_month_year(self, month: str, year: int, num_of_years=1, num_of_months=0,
                                    kind='cubic', fill_value='extrapolate', months_into_future=12):
        """ Performs a cubic interpolation of balance vs time given the average of the last entries in the account."""
        req_dt = datetime.strptime(f'{month}, 1, {year}', '%B, %d, %Y')
        req_date_ts = dt_to_milliseconds_after_epoch(req_dt)

        f = self.return_value_vs_time_function(num_of_years=num_of_years, num_of_months=num_of_months,
                                               kind=kind, fill_value=fill_value, months_into_future=months_into_future)

        y = float(f(req_date_ts))

        return y

    def return_balance_up_to_month_year(self, month: str, year: int):
        """ Returns the balance up to the end of the given month and year.

        If the request date is less than the latest date, then treat it like normal

        If the request date is greater than the latest date, but less than the retirement date,
            then account for any interest gained

        If the request date is greater than the retirement date, then account for withdrawals

        """
        # Latest account date
        latest_date = self.return_latest_date()
        if latest_date is None:
            return 0.0

        # Retirement date
        ret_date = self.user.get_latest_retirement_date()

        # Request date
        req_date = datetime.strptime(f'{month}-01-{year}', '%B-%d-%Y').date()

        today_date = now().date()
        if req_date <= today_date:  # Assume interest occurs any time after today.
            return super().return_balance_up_to_month_year(month, year)

        today_dt = datetime.strptime(f'{today_date.year}-{today_date.month}', '%Y-%m')
        today_month = today_dt.strftime('%B')
        today_year = today_dt.strftime('%Y')
        total = super().return_balance_up_to_month_year(today_month, today_year)
        current_date = today_date + relativedelta(months=+1)

        while current_date <= req_date:
            # Capture the incomes and withdrawals for the given month
            current_date_start_of_month = datetime.strptime(f'{current_date.strftime("%Y")}-{current_date.strftime("%B")}-1', '%Y-%B-%d')
            current_date_end_of_month = current_date_start_of_month + relativedelta(months=+1) + relativedelta(seconds=-1)
            # Use the previous total to calculate the compound interest
            current_income = Deposit.objects.filter(account=self, date__gte=current_date_start_of_month,
                                                    date__lt=current_date_end_of_month)
            current_income = current_income.aggregate(total=Sum('amount'))['total']
            current_income = current_income if current_income is not None else 0.0

            current_expense = Withdrawal.objects.filter(account=self, date__gte=current_date_start_of_month,
                                                        date__lt=current_date_end_of_month)
            current_expense = current_expense.aggregate(total=Sum('amount'))['total']
            current_expense = current_expense if current_expense is not None else 0.0

            balance = round(float(current_income - current_expense), 2)
            total += balance
            interest = total * float(self.monthly_interest_pct) / 100

            total += interest

            if current_date > ret_date:
                ret_withdrawal = total * self.yearly_withdrawal_rate / 12
                total -= ret_withdrawal

            current_date += relativedelta(months=+1)

        return total

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

    def return_time_to_reach_goal(self):
        return self.return_time_to_reach_amount(self.target_amount)

    def get_absolute_url(self):
        return reverse('raccount_overview', args=[self.pk])


class MonthlyBudget(models.Model):
    """ The monthly budgets set for a given user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    month = models.CharField(max_length=18, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)

    mandatory = models.FloatField(default=0.0)
    mortgage = models.FloatField(default=0.0)
    debts_goals_retirement = models.FloatField(default=0.0)
    discretionary = models.FloatField(default=0.0)

    def save(self, *args, **kwargs):
        self.month = self.date.strftime('%B')
        self.year = int(self.date.strftime('%Y'))
        super(MonthlyBudget, self).save(*args, **kwargs)

    def __str__(self):
        return "{}'s budget for {}, {}".format(self.user, self.month, self.year)

    def get_absolute_url(self):
        return reverse('mbudget-update', args=[self.pk])

    class Meta:
        unique_together = ['user', 'month', 'year']


class Interest(models.Model):
    """ Interest tracking for individual accounts.

    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    amount = models.DecimalField(max_digits=8, decimal_places=2)


class Statutory(models.Model):
    """ Tracking of statutory spending to simplify take home pay calculation.

    Essentially, this tracks is the "ether" where statutory spending comes out of gross income.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=now)
    category = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    description = models.CharField(max_length=250)
    amount = models.FloatField(verbose_name='Amount')

    def __str__(self):
        return f'{self.date} {self.description} {self.amount}'

    class Meta:
        unique_together = ['user', 'date', 'description', 'amount']
