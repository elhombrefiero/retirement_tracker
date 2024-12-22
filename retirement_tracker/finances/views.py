#!/usr/bin/env python3

# Python Library Imports
from dateutil.relativedelta import relativedelta
import json
import pytz

# Other Imports
from django.db.models.functions import TruncDay
from django.db.models import Sum
from django.shortcuts import render, HttpResponseRedirect, HttpResponse
# from django.core.exceptions import BadRequest
from django.forms import formset_factory
from django.views.generic import DetailView, TemplateView, FormView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone

from datetime import datetime

from finances.models import User, Account, CheckingAccount, DebtAccount, TradingAccount, \
    RetirementAccount, MonthlyBudget, BUDGET_GROUP_MANDATORY, BUDGET_GROUP_MORTGAGE, BUDGET_GROUP_DGR, \
    BUDGET_GROUP_DISC, Transfer, Deposit, Withdrawal, Statutory, dt_to_milliseconds_after_epoch
from finances.forms import MonthlyBudgetForUserForm, UserWorkIncomeExpenseForm, \
    UserExpenseLookupForm, MonthlyBudgetForUserMonthYearForm, AddDebtAccountForm, \
    AddCheckingAccountForm, AddRetirementAccountForm, AddTradingAccountForm, TransferBetweenAccountsForm, \
    WithdrawalForUserForm, DepositForUserForm, StatutoryForUserForm, \
    DateLocationForm, WithdrawalByLocationFormset, UserReportSelectForm
from finances.plot_views import get_line_chart_config
from finances.utils import chartjs_utils as cjs


# Create your views here.
# TODO: Create a page where the user can input a date and have the user's accounts balance at that time.
# TODO: Update the Debt Account functions to set the minimum value of 0.0 when the account reaches zero.

# TODO: Add a projected outlook page similar to the custom report page.

def get_dt_from_month_day_year(month, day, year):
    return datetime.strptime(f'{month}-{day}-{year}', '%m-%d-%Y')


class IndexView(TemplateView):
    template_name = 'finances/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all()
        return context


class UserOverviewView(DetailView):
    model = User
    template_name = 'finances/user_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estimated_retirement_date'] = self.object.return_retirement_datetime()
        context['percent_withdrawal_at_retirement'] = round(float(self.object.percent_withdrawal_at_retirement), 2)
        return context


class UserCustomReportView(FormView):
    """ User will use a form to select a date range for the user report data.

    Relevant information:
        Total Checking Account Balance
        Total Retirement Account Balance
        Total Debt Balance
        Total Net Worth


    """
    form_class = UserReportSelectForm
    template_name = 'finances/user_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.user = User.objects.get(pk=self.kwargs['pk'])
        context['user'] = self.user
        context['form'] = UserReportSelectForm(user=self.user)
        context['report_message'] = 'Custom Report'
        return context

    def form_valid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        context['report_data'] = True
        user = context['user']
        context['user_pk'] = user.pk
        form_data = form.cleaned_data
        start_date = form_data['start_date']
        tzinfo = timezone.get_current_timezone()
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tzinfo)
        end_date = form_data['end_date']
        end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=tzinfo)
        context['create_plots'] = True

        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = end_date.strftime('%Y-%m-%d')

        time_span = end_date - start_date

        # TODO: Change the report_message based on the time span.
        # If time span is less than 31 days, then redirect to Month and Year page

        # Otherwise, print Month/year to month/year

        context['report_message'] = f'{start_date} to {end_date}'

        stat_tot, mand_tot, mort_tot, dgr_tot, disc_tot = user.return_monthly_budgets(start_date, end_date)
        context['stat_total'] = stat_tot
        context['mand_total'] = mand_tot
        context['mort_total'] = mort_tot
        context['dgr_total'] = dgr_tot
        context['disc_total'] = disc_tot

        mand_exp, mort_exp, dgr_exp, disc_exp, stat_exp = user.return_tot_expenses_by_budget_startdt_to_enddt(
            start_date, end_date)
        context['stat_exp'] = stat_exp
        context['mand_exp'] = mand_exp
        context['mort_exp'] = mort_exp
        context['dgr_exp'] = dgr_exp
        context['disc_exp'] = disc_exp

        context['leftover_statutory'] = round(stat_tot - stat_exp, 2)
        context['leftover_mand'] = round(mand_tot - mand_exp, 2)
        context['leftover_mort'] = round(mort_tot - mort_exp, 2)
        context['leftover_dgr'] = round(dgr_tot - dgr_exp, 2)
        context['leftover_disc'] = round(disc_tot - disc_exp, 2)

        account_balances = user.return_report_info_acct_balance(start_dt, end_dt)

        starting_balance = account_balances['tot_checking_start'] + \
                           account_balances['tot_retirement_start'] + \
                           account_balances['tot_trading_start'] - \
                           account_balances['tot_debt_start']

        end_balance = starting_balance + account_balances['net_diff']

        context['start_balance'] = round(starting_balance, 2)
        context['end_balance'] = round(end_balance, 2)

        user_income_tot = user.return_income_total(start_date, end_date)
        context['income'] = user_income_tot
        context['takehome_pay'] = round(user_income_tot - stat_exp, 2)

        return self.render_to_response(context)


class UserReportAllView(DetailView):
    """The user reports views will have all of the data for a given time span."""
    model = User
    template_name = 'finances/user_report.html'

    # TODO: Begin adding some pages where the projected net worth can be viewed
    # TODO: Add budgeted vs expense by budget group views.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_data'] = True
        context['user_pk'] = self.object.pk
        context['report_message'] = 'All'

        start_date, end_date = self.object.get_earliest_latest_dates()

        tzinfo = timezone.get_current_timezone()
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tzinfo)
        end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=tzinfo)

        context['create_plots'] = True

        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = end_date.strftime('%Y-%m-%d')

        stat_tot, mand_tot, mort_tot, dgr_tot, disc_tot = self.object.return_monthly_budgets(start_date, end_date)
        context['stat_total'] = stat_tot
        context['mand_total'] = mand_tot
        context['mort_total'] = mort_tot
        context['dgr_total'] = dgr_tot
        context['disc_total'] = disc_tot

        mand_exp, mort_exp, dgr_exp, disc_exp, stat_exp = self.object.return_tot_expenses_by_budget_startdt_to_enddt(
            start_date, end_date)
        context['stat_exp'] = stat_exp
        context['mand_exp'] = mand_exp
        context['mort_exp'] = mort_exp
        context['dgr_exp'] = dgr_exp
        context['disc_exp'] = disc_exp

        context['leftover_statutory'] = round(stat_tot - stat_exp, 2)
        context['leftover_mand'] = round(mand_tot - mand_exp, 2)
        context['leftover_mort'] = round(mort_tot - mort_exp, 2)
        context['leftover_dgr'] = round(dgr_tot - dgr_exp, 2)
        context['leftover_disc'] = round(disc_tot - disc_exp, 2)

        account_balances = self.object.return_report_info_acct_balance(start_dt, end_dt)

        starting_balance = account_balances['tot_checking_start'] + \
                           account_balances['tot_retirement_start'] + \
                           account_balances['tot_trading_start'] - \
                           account_balances['tot_debt_start']

        end_balance = starting_balance + account_balances['net_diff']

        context['start_balance'] = round(starting_balance, 2)
        context['end_balance'] = round(end_balance, 2)

        user_income_tot = self.object.return_income_total(start_date, end_date)
        context['income'] = user_income_tot
        context['takehome_pay'] = round(user_income_tot - stat_exp, 2)
        return context


class UserReportYearView(DetailView):
    model = User
    template_name = 'finances/user_report.html'

    def dispatch(self, request, *args, **kwargs):
        self.year = kwargs['year']
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_data'] = True
        context['user_pk'] = self.object.pk
        context['report_message'] = f'{self.year}'

        start_date = datetime.strptime(f'January 1, {self.year}', '%B %d, %Y')
        tzinfo = timezone.get_current_timezone()
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tzinfo)
        end_date = start_date + relativedelta(years=+1, seconds=-1)
        end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=tzinfo)

        context['create_plots'] = True

        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = end_date.strftime('%Y-%m-%d')

        stat_tot, mand_tot, mort_tot, dgr_tot, disc_tot = self.object.return_monthly_budgets(start_date, end_date)
        context['stat_total'] = stat_tot
        context['mand_total'] = mand_tot
        context['mort_total'] = mort_tot
        context['dgr_total'] = dgr_tot
        context['disc_total'] = disc_tot

        mand_exp, mort_exp, dgr_exp, disc_exp, stat_exp = self.object.return_tot_expenses_by_budget_startdt_to_enddt(
            start_date, end_date)
        context['stat_exp'] = stat_exp
        context['mand_exp'] = mand_exp
        context['mort_exp'] = mort_exp
        context['dgr_exp'] = dgr_exp
        context['disc_exp'] = disc_exp

        context['leftover_statutory'] = round(stat_tot - stat_exp, 2)
        context['leftover_mand'] = round(mand_tot - mand_exp, 2)
        context['leftover_mort'] = round(mort_tot - mort_exp, 2)
        context['leftover_dgr'] = round(dgr_tot - dgr_exp, 2)
        context['leftover_disc'] = round(disc_tot - disc_exp, 2)

        account_balances = self.object.return_report_info_acct_balance(start_dt, end_dt)

        starting_balance = account_balances['tot_checking_start'] + \
                           account_balances['tot_retirement_start'] + \
                           account_balances['tot_trading_start'] - \
                           account_balances['tot_debt_start']

        end_balance = starting_balance + account_balances['net_diff']

        context['start_balance'] = round(starting_balance, 2)
        context['end_balance'] = round(end_balance, 2)

        user_income_tot = self.object.return_income_total(start_date, end_date)
        context['income'] = user_income_tot
        context['takehome_pay'] = round(user_income_tot - stat_exp, 2)

        return context


class UserReportMonthYearView(DetailView):
    model = User
    template_name = 'finances/user_report.html'

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_data'] = True
        context['user_pk'] = self.object.pk
        context['report_message'] = f'{self.month}, {self.year}'

        start_date = datetime.strptime(f'{self.month} 1, {self.year}', '%B %d, %Y')
        tzinfo = timezone.get_current_timezone()
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tzinfo)
        end_date = start_date + relativedelta(months=+1, seconds=-1)
        end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=tzinfo)

        context['create_plots'] = True

        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = end_date.strftime('%Y-%m-%d')

        stat_tot, mand_tot, mort_tot, dgr_tot, disc_tot = self.object.return_monthly_budgets(start_date.date(),
                                                                                             end_date.date())
        context['stat_total'] = stat_tot
        context['mand_total'] = mand_tot
        context['mort_total'] = mort_tot
        context['dgr_total'] = dgr_tot
        context['disc_total'] = disc_tot

        mand_exp, mort_exp, dgr_exp, disc_exp, stat_exp = self.object.return_tot_expenses_by_budget_startdt_to_enddt(
            start_date, end_date)
        context['stat_exp'] = stat_exp
        context['mand_exp'] = mand_exp
        context['mort_exp'] = mort_exp
        context['dgr_exp'] = dgr_exp
        context['disc_exp'] = disc_exp

        context['leftover_statutory'] = round(stat_tot - stat_exp, 2)
        context['leftover_mand'] = round(mand_tot - mand_exp, 2)
        context['leftover_mort'] = round(mort_tot - mort_exp, 2)
        context['leftover_dgr'] = round(dgr_tot - dgr_exp, 2)
        context['leftover_disc'] = round(disc_tot - disc_exp, 2)

        account_balances = self.object.return_report_info_acct_balance(start_dt, end_dt)

        starting_balance = account_balances['tot_checking_start'] + \
                           account_balances['tot_retirement_start'] + \
                           account_balances['tot_trading_start'] - \
                           account_balances['tot_debt_start']

        end_balance = starting_balance + account_balances['net_diff']

        context['start_balance'] = round(starting_balance, 2)
        context['end_balance'] = round(end_balance, 2)

        user_income_tot = self.object.return_income_total(start_date, end_date)
        context['income'] = user_income_tot
        context['takehome_pay'] = round(user_income_tot - stat_exp, 2)

        return context


class UserTransferView(FormView):
    form_class = TransferBetweenAccountsForm
    template_name = 'finances/transfer_form.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        user_accounts = self.user.return_all_accounts()
        context['accounts'] = user_accounts
        return context

    def form_valid(self, form):
        post = self.request.POST
        month = post['date_month']
        day = post['date_day']
        year = post['date_year']
        dtdate = datetime.strptime(f'{month}-{day}-{year}', '%m-%d-%Y')
        acct_from = Account.objects.get(pk=int(post['account_from']))
        acct_to = Account.objects.get(pk=int(post['account_to']))
        newtransfer = Transfer.objects.create(account_from=acct_from,
                                              account_to=acct_to,
                                              date=dtdate,
                                              budget_group=post['budget_group'],
                                              category=post['category'],
                                              location=post['location'],
                                              description=post['description'],
                                              amount=float(post['amount']),
                                              slug_field=post['slug_field'],
                                              group=post['group'])
        newtransfer.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class UserAccountsAvailable(DetailView):
    model = User
    template_name = 'finances/user_accounts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_checking_accts = CheckingAccount.objects.filter(user=context['user'])
        user_retirement_accts = RetirementAccount.objects.filter(user=context['user'])
        user_debt_accts = DebtAccount.objects.filter(user=context['user'])
        context['user_checking'] = user_checking_accts
        context['user_retirement'] = user_retirement_accts
        context['user_debt'] = user_debt_accts

        return context


class UserExpensesAvailable(ListView):
    model = Withdrawal
    template_name = 'finances/withdrawal_list.html'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.userpk = kwargs['pk']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        userobj = User.objects.get(pk=self.userpk)
        user_accts = userobj.return_all_accounts()
        return Withdrawal.objects.filter(account__in=user_accts).order_by('-date')


class UserIncomesAvailable(ListView):
    model = Deposit
    template_name = 'finances/deposit_list.html'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.userpk = kwargs['pk']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        userobj = User.objects.get(pk=self.userpk)
        user_accounts = userobj.return_all_accounts()
        return Deposit.objects.filter(account__in=user_accounts).order_by('-date')


class UserStatutoryAvailable(ListView):
    model = Statutory
    template_name = 'finances/statutory_list.html'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.userpk = kwargs['pk']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        userobj = User.objects.get(pk=self.userpk)
        return Statutory.objects.filter(user=userobj).order_by('-date')


class UserTransfersAvailable(ListView):
    model = Transfer
    template_name = 'finances/transfer_list.html'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.userpk = kwargs['pk']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        userobj = User.objects.get(pk=self.userpk)
        user_accounts = userobj.return_all_accounts()
        return Transfer.objects.filter(account_from__in=user_accounts, account_to__in=user_accounts).order_by('-date')


class UserReportsAvailable(DetailView):
    model = User
    template_name = 'finances/user_reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year_month_dict = self.object.return_year_month_for_reports()
        context['reports_year_month'] = year_month_dict
        return context


class UserMonthlyBudgetsAvailable(DetailView):
    model = User
    template_name = 'finances/user_monthly_budgets.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year_month_dict = self.object.return_year_month_for_monthly_budgets()
        context['monthly_budgets_year_month'] = year_month_dict
        return context


class UserCreateView(CreateView):
    model = User
    fields = '__all__'


class UserUpdateView(UpdateView):
    model = User
    fields = '__all__'


class UserDeleteView(DeleteView):
    model = User
    success_url = '/finances'


class AccountCreateView(CreateView):
    model = Account
    fields = '__all__'


class AccountDeleteView(DeleteView):
    model = Account
    success_url = "/finances"


class AccountUpdateView(UpdateView):
    model = Account
    fields = '__all__'


class AccountView(DetailView):
    """ View the deposits and withdrawals associated with this account.

    The template will have a redirect to see all withdrawals and deposits"""
    model = Account

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the latest incomes associated with this account
        # TODO: Add page with more deposits and withdrawals for an account(pagination?)
        context['deposits'] = Deposit.objects.filter(account=self.object).order_by('-date')[:25]
        context['withdrawals'] = Withdrawal.objects.filter(account=self.object).order_by('-date')[:25]
        context['balance'] = self.object.return_balance()
        latest_date = self.object.return_latest_date()
        one_year_later = latest_date + relativedelta(years=+1)
        five_years_later = latest_date + relativedelta(years=+5)
        one_year_balance = self.object.estimate_balance_month_year(one_year_later.strftime('%B'),
                                                                   int(one_year_later.strftime('%Y')))
        one_year_balance = round(one_year_balance, 2)
        five_year_balance = self.object.estimate_balance_month_year(five_years_later.strftime('%B'),
                                                                    int(five_years_later.strftime('%Y')))
        five_year_balance = round(five_year_balance, 2)
        context['one_year_later'] = one_year_later.strftime('%B-%Y')
        context['five_years_later'] = five_years_later.strftime('%B-%Y')
        context['one_year_balance'] = one_year_balance
        context['five_year_balance'] = five_year_balance
        return context


class CheckingAccountView(DetailView):
    """ View the deposits and withdrawals associated with this account.

    The template will have a redirect to see all withdrawals and deposits"""
    model = CheckingAccount
    template_name = 'finances/checkingaccount_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the latest incomes associated with this account
        context['deposits'] = Deposit.objects.filter(account=self.object).order_by('-date')[:25]
        context['withdrawals'] = Withdrawal.objects.filter(account=self.object).order_by('-date')[:25]
        context['balance'] = self.object.return_balance()
        latest_date = self.object.return_latest_date()
        if latest_date is None:
            one_year_later = timezone.now() + relativedelta(years=+1)
            five_years_later = timezone.now() + relativedelta(years=+5)
            context['one_year_later'] = one_year_later.strftime('%B-%Y')
            context['five_years_later'] = five_years_later.strftime('%B-%Y')
            context['one_year_balance'] = self.object.return_balance()
            context['five_year_balance'] = self.object.return_balance()
            return context
        one_year_later = latest_date + relativedelta(years=+1)
        five_years_later = latest_date + relativedelta(years=+5)
        one_year_balance = self.object.estimate_balance_month_year(one_year_later.strftime('%B'),
                                                                   int(one_year_later.strftime('%Y')))
        one_year_balance = round(one_year_balance, 2)
        five_year_balance = self.object.estimate_balance_month_year(five_years_later.strftime('%B'),
                                                                    int(five_years_later.strftime('%Y')))
        five_year_balance = round(five_year_balance, 2)
        context['one_year_later'] = one_year_later.strftime('%B-%Y')
        context['five_years_later'] = five_years_later.strftime('%B-%Y')
        context['one_year_balance'] = one_year_balance
        context['five_year_balance'] = five_year_balance
        return context


class RetirementAccountView(DetailView):
    """ View the deposits and withdrawals associated with this account.

    The template will have a redirect to see all withdrawals and deposits"""
    template_name = 'finances/retirementaccount_detail.html'
    model = RetirementAccount

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the latest incomes associated with this account
        context['deposits'] = Deposit.objects.filter(account=self.object).order_by('-date')[:25]
        context['withdrawals'] = Withdrawal.objects.filter(account=self.object).order_by('-date')[:25]
        context['balance'] = self.object.return_balance()
        latest_date = self.object.return_latest_date()
        one_year_later = latest_date + relativedelta(years=+1)
        five_years_later = latest_date + relativedelta(years=+5)
        one_year_balance = self.object.estimate_balance_month_year(one_year_later.strftime('%B'),
                                                                   int(one_year_later.strftime('%Y')))
        one_year_balance = round(one_year_balance, 2)
        five_year_balance = self.object.estimate_balance_month_year(five_years_later.strftime('%B'),
                                                                    int(five_years_later.strftime('%Y')))
        five_year_balance = round(five_year_balance, 2)
        context['one_year_later'] = one_year_later.strftime('%B-%Y')
        context['five_years_later'] = five_years_later.strftime('%B-%Y')
        context['one_year_balance'] = one_year_balance
        context['five_year_balance'] = five_year_balance
        return context


class DebtAccountView(DetailView):
    """ View the deposits and withdrawals associated with this account.

    The template will have a redirect to see all withdrawals and deposits"""
    model = DebtAccount
    template_name = 'finances/debtaccount_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the latest incomes associated with this account
        context['deposits'] = Deposit.objects.filter(account=self.object).order_by('-date')[:25]
        context['withdrawals'] = Withdrawal.objects.filter(account=self.object).order_by('-date')[:25]
        context['balance'] = self.object.return_balance()
        latest_date = self.object.return_latest_date()
        one_year_later = latest_date + relativedelta(years=+1)
        five_years_later = latest_date + relativedelta(years=+5)
        one_year_balance = self.object.estimate_balance_month_year(one_year_later.strftime('%B'),
                                                                   int(one_year_later.strftime('%Y')))
        one_year_balance = round(one_year_balance, 2)
        five_year_balance = self.object.estimate_balance_month_year(five_years_later.strftime('%B'),
                                                                    int(five_years_later.strftime('%Y')))
        five_year_balance = round(five_year_balance, 2)
        context['one_year_later'] = one_year_later.strftime('%B-%Y')
        context['five_years_later'] = five_years_later.strftime('%B-%Y')
        context['one_year_balance'] = one_year_balance
        context['five_year_balance'] = five_year_balance
        return context


class CheckingAccountForUserView(FormView):
    form_class = AddCheckingAccountForm
    template_name = 'finances/account_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        context['acct_type'] = 'Checking'
        return context

    def form_valid(self, form):
        post = self.request.POST
        newchecking = CheckingAccount.objects.create(user=self.user,
                                                     name=post['name'],
                                                     starting_balance=float(post['starting_balance']),
                                                     opening_date=post['opening_date'],
                                                     url=post['url'],
                                                     monthly_interest_pct=float(post['monthly_interest_pct']))
        newchecking.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class DebtAccountForUserView(FormView):
    form_class = AddDebtAccountForm
    template_name = 'finances/account_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        return context

    def form_valid(self, form):
        post = self.request.POST
        newdebtacct = DebtAccount.objects.create(user=self.user,
                                                 name=post['name'],
                                                 starting_balance=float(post['starting_balance']),
                                                 opening_date=post['opening_date'],
                                                 url=post['url'],
                                                 yearly_interest_pct=float(post['yearly_interest_pct']))
        newdebtacct.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class RetirementAccountForUserView(FormView):
    form_class = AddRetirementAccountForm
    template_name = 'finances/account_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        return context

    def form_valid(self, form):
        post = self.request.POST
        newretacct = RetirementAccount.objects.create(user=self.user,
                                                      name=post['name'],
                                                      url=post['url'],
                                                      starting_balance=float(post['starting_balance']),
                                                      opening_date=post['opening_date'],
                                                      yearly_withdrawal_rate=float(post['yearly_withdrawal_rate']),
                                                      target_amount=post['target_amount'])
        newretacct.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class TradingAccountForUserView(FormView):
    form_class = AddTradingAccountForm
    template_name = 'finances/account_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        return context

    def form_valid(self, form):
        post = self.request.POST
        newtradeacct = TradingAccount.objects.create(user=self.user,
                                                     name=post['name'],
                                                     url=post['url'],
                                                     starting_balance=float(post['starting_balance']),
                                                     opening_date=post['opening_date'],
                                                     )
        newtradeacct.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class WithdrawalView(DetailView):
    model = Withdrawal


class WithdrawalCreateView(CreateView):
    model = Withdrawal
    fields = '__all__'


class WithdrawalForUserView(FormView):
    form_class = WithdrawalForUserForm
    template_name = 'finances/withdrawal_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        timezone.activate(timezone.get_current_timezone())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        six_months_prior = timezone.now() + relativedelta(months=-6)
        user_accounts = self.user.return_all_accounts()
        expenses_six_mo_prior = Withdrawal.objects.filter(account__in=user_accounts, date__gte=six_months_prior)
        distinct_cat = list(expenses_six_mo_prior.values_list('category', flat=True).distinct())
        distinct_desc = list(expenses_six_mo_prior.values_list('description', flat=True).distinct())
        distinct_where = list(expenses_six_mo_prior.values_list('location', flat=True).distinct())
        distinct_group = list(expenses_six_mo_prior.values_list('group', flat=True).distinct())
        context['user'] = self.user
        context['distinct_cat'] = distinct_cat
        context['distinct_desc'] = distinct_desc
        context['distinct_where'] = distinct_where
        context['distinct_group'] = distinct_group
        return context

    def form_valid(self, form):
        post = self.request.POST
        account = Account.objects.get(pk=post['account'])
        dtdate = get_dt_from_month_day_year(post['date_month'], post['date_day'], post['date_year'])
        newexpense = Withdrawal.objects.create(account=account,
                                               date=dtdate,
                                               budget_group=post['budget_group'],
                                               category=post['category'],
                                               location=post['location'],
                                               description=post['description'],
                                               amount=post['amount'],
                                               slug_field=post['slug_field'],
                                               group=['group'],
                                               )
        newexpense.save()
        self.success_url = f'/finances/user/{self.user.pk}/add_withdrawal'
        return super().form_valid(form)


class ExpenseLookupForUserView(FormView):
    form_class = UserExpenseLookupForm
    template_name = 'finances/expense_lookup_form_for_user.html'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def form_valid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        user_accts = self.user.return_all_accounts()
        withdrawals = Withdrawal.objects.filter(account__in=user_accts).order_by('date')
        title_txt = ''
        if form.cleaned_data['start_year']:
            title_txt += f'Start date: '
            if form.cleaned_data['start_month']:
                title_txt += f'{form.cleaned_data["start_month"]} 1, '
                start_dt = datetime.strptime(f'{form.cleaned_data["start_month"]} 1, {form.cleaned_data["start_year"]}',
                                             '%B %d, %Y')
            else:
                title_txt += f'January 1, '
                start_dt = datetime.strptime(f'January 1, {form.cleaned_data["start_year"]}', '%B %d, %Y')
            title_txt += f'{form.cleaned_data["start_year"]} '
            withdrawals = withdrawals.filter(date__gte=start_dt)

        if form.cleaned_data['end_year']:
            title_txt += f'End date: '
            if form.cleaned_data['end_month']:
                # Get end day of the end month
                end_dt = datetime.strptime(f'{form.cleaned_data["end_month"]} 1, {form.cleaned_data["end_year"]}',
                                           '%B %d, %Y')
                end_dt = end_dt + relativedelta(months=+1)
                end_dt = end_dt + relativedelta(days=-1)
                title_txt += f'{form.cleaned_data["end_month"]} {datetime.strftime(end_dt, "%d")}, '
            else:
                title_txt += f'{form.cleaned_data["end_month"]} 31, '
                end_dt = datetime.strptime(f'December 31, {form.cleaned_data["end_year"]}', '%B %d, %Y')
            withdrawals = withdrawals.filter(date__lte=end_dt)
            title_txt += f'{form.cleaned_data["end_year"]} '

        if form.cleaned_data['category']:
            title_txt += f'Category: {form.cleaned_data["category"]} '
            withdrawals = withdrawals.filter(category=form.cleaned_data['category'])

        if form.cleaned_data['budget_group']:
            title_txt += f'Budget Group: {form.cleaned_data["budget_group"]} '
            withdrawals = withdrawals.filter(budget_group=form.cleaned_data['budget_group'])

        if form.cleaned_data['description']:
            title_txt += f'Description: {form.cleaned_data["description"]} '
            withdrawals = withdrawals.filter(description=form.cleaned_data['description'])

        if form.cleaned_data['where_bought']:
            title_txt += f'Location: {form.cleaned_data["where_bought"]} '
            withdrawals = withdrawals.filter(location=form.cleaned_data['where_bought'])

        title_txt = title_txt.strip()

        if len(withdrawals) > 2:
            context['chart_data'] = True
            datasets = list()
            xydata = list()
            summed_withdrawals = withdrawals.annotate(day=TruncDay('date')).values('day').annotate(cumsum=Sum('amount'))
            total = 0.0
            for withdrawal in summed_withdrawals:
                total += withdrawal['cumsum']
                withdrawal_dt = datetime.combine(withdrawal['day'], datetime.min.time())
                wdate = dt_to_milliseconds_after_epoch(withdrawal_dt)
                xydata.append({'x': wdate, 'y': total})
            datasets.append({
                'data': xydata,
                'backgroundColor': cjs.get_color('red', 0.5),
                'borderColor': cjs.get_color('red'),
                'fill': False,
            })
            data = {
                'datasets': datasets
            }
            context['data'] = json.dumps(data)
            config = get_line_chart_config(title_txt)
            context['options'] = json.dumps(config['options'])
        else:
            context['chart_data'] = False

        context['table_data'] = False
        if len(withdrawals) > 2:
            total = 0.0
            context['include_table'] = True
            context['table_data'] = list()
            table_withdrawals = withdrawals.annotate(day=TruncDay('date')).annotate(cumsum=Sum('amount'))
            for twithdrawal in table_withdrawals:
                total += twithdrawal.amount
                context['table_data'].append(
                    {'date': twithdrawal.day, 'category': twithdrawal.category,
                     'description': twithdrawal.description, 'withdrawal_id': twithdrawal.id,
                     'amount': twithdrawal.amount, 'cumulative': round(total,2)})

        return self.render_to_response(context)


class UserWorkRelatedIncomeView(FormView):
    form_class = UserWorkIncomeExpenseForm
    template_name = 'finances/user_work_income_form.html'

    def get(self, request, *args, **kwargs):
        self.user = User.objects.get(pk=kwargs['pk'])
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = User.objects.get(pk=self.kwargs['pk'])
        kwargs['user'] = user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = User.objects.get(pk=self.kwargs['pk'])
        context['user'] = user
        return context

    def form_valid(self, form):
        post = self.request.POST
        user = User.objects.get(pk=self.kwargs['pk'])
        account = CheckingAccount.objects.get(pk=post['checking_account'])
        account_401k = RetirementAccount.objects.get(pk=post['account_401k'])
        account_HSA = RetirementAccount.objects.get(pk=post['account_HSA'])
        day = post['date_day']
        month = post['date_month']
        year = post['date_year']
        date = datetime.strptime(f'{year}-{month}-{day}', '%Y-%m-%d')
        gross_income = float(post['gross_income'])
        fed_income_tax = float(post['fed_income_tax'])
        social_security_tax = float(post['social_security_tax'])
        medicare = float(post['medicare'])
        state_income_tax = float(post['state_income_tax'])
        dental = float(post['dental'])
        medical = float(post['medical'])
        vision = float(post['vision'])
        retirement_401k = float(post['retirement_401k'])
        retirement_hsa = float(post['retirement_HSA'])

        new_inc = Deposit.objects.create(account=account,
                                         date=date,
                                         category='Gross Income',
                                         description='Gross Income',
                                         amount=gross_income)
        new_inc.save()
        fed_exp = Statutory.objects.create(user=user,
                                           date=date,
                                           category='Taxes',
                                           location='Work',
                                           description='Federal Income Tax',
                                           amount=fed_income_tax,
                                           )
        fed_exp.save()
        ss_exp = Statutory.objects.create(user=user,
                                          date=date,
                                          category='Taxes',
                                          location='Work',
                                          description='Social Security Tax',
                                          amount=social_security_tax,
                                          )
        ss_exp.save()
        medicare_exp = Statutory.objects.create(user=user,
                                                date=date,
                                                category='Taxes',
                                                location='Work',
                                                description='Medicare Tax',
                                                amount=medicare,
                                                )
        medicare_exp.save()
        if state_income_tax > 0.0:
            state_income_exp = Statutory.objects.create(user=user,
                                                        date=date,
                                                        category='Taxes',
                                                        location='Work',
                                                        description='State Income Tax',
                                                        amount=state_income_tax,
                                                        )
            state_income_exp.save()
        if dental > 0.0:
            dental_exp = Withdrawal.objects.create(account=account,
                                                   date=date,
                                                   budget_group=BUDGET_GROUP_MANDATORY,
                                                   category='Mandatory',
                                                   location='Work',
                                                   description='Dental',
                                                   amount=dental,
                                                   )
            dental_exp.save()
        if medical > 0.0:
            medical_exp = Withdrawal.objects.create(account=account,
                                                    date=date,
                                                    budget_group=BUDGET_GROUP_MANDATORY,
                                                    category='Mandatory',
                                                    location='Work',
                                                    description='Medical',
                                                    amount=medical,
                                                    )
            medical_exp.save()
        if vision > 0.0:
            vision_exp = Withdrawal.objects.create(account=account,
                                                   date=date,
                                                   budget_group=BUDGET_GROUP_MANDATORY,
                                                   category='Mandatory',
                                                   location='Work',
                                                   description='Vision',
                                                   amount=vision,
                                                   )
            vision_exp.save()
        if account != account_401k:
            ret_401k_trans = Transfer.objects.create(account_from=account,
                                                     account_to=account_401k,
                                                     date=date,
                                                     budget_group=BUDGET_GROUP_DGR,
                                                     category='Retirement',
                                                     location='Work',
                                                     description='401k Contribution',
                                                     amount=retirement_401k,
                                                     )
            ret_401k_trans.save()
        else:
            ret_401k_inc = Deposit.objects.create(user=user,
                                                  account=account_401k,
                                                  date=date,
                                                  category='401k',
                                                  description='401k Contirbution',
                                                  location='Work',
                                                  amount=retirement_401k)
            ret_401k_inc.save()
        if account != account_HSA:
            ret_hsa_trans = Transfer.objects.create(account_from=account,
                                                    account_to=account_HSA,
                                                    date=date,
                                                    budget_group=BUDGET_GROUP_DGR,
                                                    category='Retirement',
                                                    location='Work',
                                                    description='HSA Contribution',
                                                    amount=retirement_hsa
                                                    )
            ret_hsa_trans.save()
        else:
            ret_hsa_inc = Deposit.objects.create(account=account_HSA,
                                                 date=date,
                                                 category='HSA',
                                                 description='HSA Contribution',
                                                 location='Work',
                                                 amount=retirement_hsa)
            ret_hsa_inc.save()
        self.success_url = f'/finances/user/{user.pk}'
        return super().form_valid(form)


class MonthlyBudgetForUserView(FormView):
    """ View an existing Monthly Budget for a User."""
    form_class = MonthlyBudgetForUserForm
    template_name = 'finances/monthlybudget_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.month = kwargs.get('month')
        self.year = kwargs.get('year')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['month'] = self.month
        context['year'] = self.year
        context['user'] = self.user
        takehome = self.user.return_takehome_pay_month_year(self.month, self.year)
        budget_mand, budget_mort, statutory, budget_dgr, budget_disc = \
            self.user.estimate_budget_for_month_year(self.month, self.year)
        context['takehome'] = takehome
        context['statutory'] = statutory
        context['gross_income'] = takehome + statutory
        context['est_mand'] = budget_mand
        context['est_mort'] = budget_mort
        context['est_dgr'] = budget_dgr
        context['est_disc'] = budget_disc
        context['est_total'] = statutory + budget_mand + budget_mort + budget_dgr + budget_disc
        actual_mand, actual_mort, actual_dgr, actual_disc, actual_statutory = \
            self.user.return_tot_expenses_by_budget_month_year(self.month, self.year)
        context['current_mand'] = actual_mand
        context['current_mort'] = actual_mort
        context['current_dgr'] = actual_dgr
        context['current_disc'] = actual_disc
        context['actual_statutory'] = actual_statutory
        context['current_total'] = actual_mand + actual_mort + actual_dgr + actual_disc + actual_statutory
        return context

    def get_form(self, form_class=None):
        # Populate with the current date and user information for that given month
        form = super().get_form(form_class)
        if self.request.method == 'GET':
            user = User.objects.get(pk=self.kwargs['pk'])
            start_date = datetime.strptime(f'{self.month}-01-{self.year}', '%B-%d-%Y')
            end_date = start_date + relativedelta(months=+1, seconds=-1)
            stat_tot, mand_tot, mort_tot, dgr_tot, disc_tot = user.return_monthly_budgets(start_date, end_date)

            init_date = datetime.strptime(f'{self.month}, {self.year}', '%B, %Y').date()
            form.initial.update({'date': init_date, 'mandatory': mand_tot, 'mortgage': mort_tot,
                                 'debts_goals_retirement': dgr_tot, 'discretionary': disc_tot})
        return form

    def form_valid(self, form):
        post = self.request.POST
        mandatory = round(float(post['mandatory']), 2)
        mortgage = round(float(post['mortgage']), 2)
        dgr = round(float(post['debts_goals_retirement']), 2)
        disc = round(float(post['discretionary']), 2)
        dt = datetime.strptime(f'{self.month}-{self.year}', '%B-%Y')
        date = dt.date()
        try:
            monthly_budget = MonthlyBudget.objects.get(user=self.user, month=self.month, year=self.year)
            monthly_budget.mandatory = mandatory
            monthly_budget.mortgage = mortgage
            monthly_budget.debts_goals_retirement = dgr
            monthly_budget.discretionary = disc

        except MonthlyBudget.DoesNotExist:
            monthly_budget = MonthlyBudget.objects.create(user=self.user, date=date, mandatory=mandatory,
                                                          mortgage=mortgage, disc=disc, debts_goals_retirement=dgr)
        finally:
            monthly_budget.save()

        self.success_url = f'/finances/user/{self.user.pk}/{self.month}/{self.year}'  # Redirect to monthly report
        return super().form_valid(form)


class ExpenseUpdateView(UpdateView):
    model = Withdrawal
    fields = '__all__'


class DepositUpdateView(UpdateView):
    model = Deposit
    fields = '__all__'


class DepositDeleteView(DeleteView):
    model = Deposit
    template_name = 'finances/object_confirm_delete.html'
    success_url = '/finances'


class WithdrawalDeleteView(DeleteView):
    model = Withdrawal
    template_name = 'finances/object_confirm_delete.html'
    success_url = '/finances'


class StatutoryDeleteView(DeleteView):
    model = Statutory
    template_name = 'finances/object_confirm_delete.html'
    success_url = '/finances'


class DepositView(DetailView):
    model = Deposit
    template_name = 'finances/deposit_detail.html'


class StatutoryView(DetailView):
    model = Statutory
    template_name = 'finances/statutory_detail.html'


class TransferView(DetailView):
    model = Transfer
    template_name = 'finances/transfer_detail.html'


class TransferUpdateView(UpdateView):
    model = Transfer
    fields = '__all__'


class TransferDeleteView(DeleteView):
    model = Transfer
    template_name = 'finances/object_confirm_delete.html'
    success_url = '/finances'


class DepositForUserView(FormView):
    """ Input a deposit for a user. """
    form_class = DepositForUserForm
    template_name = 'finances/deposit_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        six_months_prior = timezone.now() + relativedelta(months=-6)
        user_accounts = self.user.return_all_accounts()
        incomes_six_months_prior = Deposit.objects.filter(account__in=user_accounts, date__gte=six_months_prior)
        distinct_cat = list(incomes_six_months_prior.values_list('category', flat=True).distinct())
        distinct_desc = list(incomes_six_months_prior.values_list('description', flat=True).distinct())
        distinct_where = list(incomes_six_months_prior.values_list('location', flat=True).distinct())
        distinct_group = list(incomes_six_months_prior.values_list('group', flat=True).distinct())
        context['user'] = self.user
        context['distinct_cat'] = distinct_cat
        context['distinct_desc'] = distinct_desc
        context['distinct_where'] = distinct_where
        context['distinct_group'] = distinct_group

        return context

    def form_valid(self, form):
        post = self.request.POST
        account = Account.objects.get(pk=post['account'])
        dtdate = get_dt_from_month_day_year(post['date_month'], post['date_day'], post['date_year'])
        newdeposit = Deposit.objects.create(account=account,
                                            date=dtdate,
                                            category=post['category'],
                                            description=post['description'],
                                            location=post['location'],
                                            amount=post['amount'],
                                            slug_field=post['slug_field'],
                                            group=post['group']
                                            )
        newdeposit.save()
        self.success_url = f'/finances/user/{self.user.pk}/add_deposit'
        return super().form_valid(form)


class StatutoryForUserView(FormView):
    form_class = StatutoryForUserForm
    template_name = 'finances/statutory_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        return context

    def form_valid(self, form):
        post = self.request.POST
        dtdate = get_dt_from_month_day_year(post['date_month'], post['date_day'], post['date_year'])
        newstatutory = Statutory.objects.create(user=self.user,
                                                date=dtdate,
                                                category=post['category'],
                                                location=post['location'],
                                                description=post['description'],
                                                amount=float(post['amount']))

        newstatutory.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class WithdrawalUpdateView(UpdateView):
    model = Withdrawal
    fields = '__all__'


class StatutoryUpdateView(UpdateView):
    model = Statutory
    fields = '__all__'


class MonthlyBudgetView(DetailView):
    model = MonthlyBudget


class MonthlyBudgetCreateView(FormView):
    """ Creates a new Monthly Budget for a User."""
    form_class = MonthlyBudgetForUserForm
    template_name = 'finances/monthlybudget_form_for_user_new.html'
    success_url = '/finances'

    fields = ['date', 'mandatory', 'mortgage', 'debts_goals_retirement', 'discretionary']

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        return context

    def form_valid(self, form):
        post = self.request.POST
        month = post['date_month']
        day = post['date_day']
        year = post['date_year']
        dtdate = datetime.strptime(f'{month}-{day}-{year}', '%m-%d-%Y')
        month_name = dtdate.strftime('%B')
        mb_obj, created = MonthlyBudget.objects.get_or_create(user=self.user,
                                                              month=month_name,
                                                              year=year,
                                                              defaults={'date': dtdate,
                                                                        'mandatory': post['mandatory'],
                                                                        'mortgage': post['mortgage'],
                                                                        'debts_goals_retirement': post[
                                                                            'debts_goals_retirement'],
                                                                        'discretionary': post['discretionary']})
        if not created:
            mb_obj.mandatory = post['mandatory']
            mb_obj.mortgage = post['mortgage']
            mb_obj.debts_goals_retirement = post['debts_goals_retirement']
            mb_obj.discretionary = post['discretionary']
            mb_obj.save()
        self.success_url = f'/finances/user/{self.user.pk}/{month_name}/{year}'
        return super().form_valid(form)


class MonthlyBudgetDeleteView(DeleteView):
    model = MonthlyBudget
    success_url = '/finances'


class MonthlyBudgetUpdateView(UpdateView):
    model = MonthlyBudget
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        user_for_budget = self.object.user
        takehome = user_for_budget.return_takehome_pay_month_year(self.object.month, self.object.year)
        context['takehome'] = takehome
        budget_mand, budget_mort, statutory, budget_dgr, budget_disc = \
            user_for_budget.estimate_budget_for_month_year(self.object.month, self.object.year)
        context['user'] = user_for_budget
        context['statutory'] = statutory
        context['est_mand'] = budget_mand
        context['est_mort'] = budget_mort
        context['est_dgr'] = budget_dgr
        context['est_disc'] = budget_disc
        context['est_total'] = statutory + budget_mand + budget_mort + budget_dgr + budget_disc
        actual_mand, actual_mort, actual_dgr, actual_disc, actual_statutory = \
            user_for_budget.return_tot_expenses_by_budget_month_year(self.object.month, self.object.year)
        context['current_mand'] = actual_mand
        context['current_mort'] = actual_mort
        context['current_dgr'] = actual_dgr
        context['current_disc'] = actual_disc
        context['actual_statutory'] = actual_statutory
        context['current_total'] = actual_mand + actual_mort + actual_dgr + actual_disc + actual_statutory
        context['month'] = self.object.month
        context['year'] = self.object.year
        return context


class TradingAccountView(DetailView):
    model = TradingAccount

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the latest incomes associated with this account
        context['incomes'] = Deposit.objects.filter(account=self.object).order_by('-date')[:10]
        context['expenses'] = Withdrawal.objects.filter(account=self.object).order_by('-date')[:10]
        context['balance'] = self.object.return_balance()
        return context


class TradingAccountCreateView(CreateView):
    model = TradingAccount
    fields = '__all__'


class TradingAccountDeleteView(DeleteView):
    model = TradingAccount
    success_url = '/finances'
    template_name = 'finances/account_confirm_delete.html'


class TradingAccountUpdateView(UpdateView):
    model = TradingAccount
    fields = '__all__'


class RetirementAccountCreateView(CreateView):
    model = RetirementAccount
    fields = '__all__'


class RetirementAccountDeleteView(DeleteView):
    model = RetirementAccount
    success_url = '/finances'
    template_name = 'finances/account_confirm_delete.html'


class RetirementAccountUpdateView(UpdateView):
    model = RetirementAccount
    fields = '__all__'
    success_url = f'/finances/'


class CheckingAccountUpdateView(UpdateView):
    model = CheckingAccount
    fields = '__all__'
    success_url = f'/finances/'


class DebtAccountUpdateView(UpdateView):
    model = DebtAccount
    fields = '__all__'
    success_url = f'/finances/'


class WithdrawalForUserByLocation(CreateView):
    model = User
    success_url = '/finances'
    form_class = WithdrawalForUserForm
    template_name = 'finances/user_withdrawal_by_location_form.html'
    extra = 1

    # TODO: Check why the dates show up in this form
    # TODO: Check why the location is not put into a Withdrawal

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mywithdrawalbylocationformset = WithdrawalByLocationFormset(queryset=Withdrawal.objects.none())
        mywithdrawalbylocationformset.extra = self.extra
        context['formset'] = mywithdrawalbylocationformset
        context['date_location_form'] = DateLocationForm(user=self.user)
        context['extra'] = self.extra
        context['user'] = self.user
        return context

    def get(self, request, *args, **kwargs):
        self.user = User.objects.get(pk=kwargs['pk'])
        self.success_url = f'/finances/user/{self.user.pk}'
        if 'extra' in request.GET:
            try:
                self.extra = int(request.GET['extra'])
            except:
                self.extra = 1
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        formset = WithdrawalByLocationFormset(request.POST)
        date_location_form = DateLocationForm(data=request.POST)
        if formset.is_valid() and date_location_form.is_valid():
            return self.form_valid(formset, date_location_form)
        self.object = User.objects.get(pk=kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['formset'] = formset
        context['date_location_form'] = date_location_form
        return self.render_to_response(context)

    def form_valid(self, formset, date_location_form, **kwargs):
        userpk = self.kwargs['pk']
        user = User.objects.get(pk=userpk)
        self.success_url = f'/finances/user/{user.pk}/add_withdrawals_by_loc'
        dt = datetime.combine(date_location_form.cleaned_data['date'], datetime.min.time())
        location = date_location_form.cleaned_data['where_bought']
        instances = formset.save(commit=False)
        for instance in instances:
            instance.date = dt
            instance.where_bought = location
            instance.save()
        return HttpResponseRedirect(self.success_url)
