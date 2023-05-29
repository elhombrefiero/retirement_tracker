from dateutil.relativedelta import relativedelta
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
    BUDGET_GROUP_DISC, Transfer, Deposit, Withdrawal, Statutory
from finances.forms import MonthlyBudgetForUserForm, UserWorkIncomeExpenseForm, \
    UserExpenseLookupForm, MonthlyBudgetForUserMonthYearForm, AddDebtAccountForm, \
    AddCheckingAccountForm, AddRetirementAccountForm, AddTradingAccountForm, TransferBetweenAccountsForm, \
    WithdrawalForUserForm, DepositForUserForm, StatutoryForUserForm


# Create your views here.


class IndexView(TemplateView):
    template_name = 'finances/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all()
        return context


class UserView(DetailView):
    model = User
    # TODO: Begin adding some pages where the projected net worth can be viewed
    # TODO: Add budgeted vs expense by budget group views.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ret_tot_checking, ret_tot_retirement, ret_tot_trading, ret_tot_debt, ret_net_worth = \
            self.object.return_net_worth_at_retirement()
        context['projected_net_worth'] = ret_net_worth
        context['earliest_ret_date'] = self.object.get_earliest_retirement_date()
        context['retirement_date'] = self.object.return_retirement_datetime()
        context['accounts'] = Account.objects.filter(user=self.object)
        tot_checking, tot_retirement, tot_trading, tot_debt, net_worth = \
            self.object.return_net_worth()
        context['net_worth'] = net_worth
        context['checking_balance'] = tot_checking
        context['retirement_balance'] = tot_retirement
        context['trading_balance'] = tot_trading
        context['debt_balance'] = tot_debt
        context['month'] = None
        context['year'] = None
        context['report_type'] = None
        return context


class UserYearView(DetailView):
    model = User

    # TODO: Figure out any useful metrics for year view

    def dispatch(self, request, *args, **kwargs):
        self.year = kwargs['year']
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_type'] = 'year'
        context['accounts'] = Account.objects.filter(user=self.object)
        tot_checking, tot_retirement, tot_trading, tot_debt, net_worth = \
            self.object.return_net_worth_year(self.year)
        context['checking_balance'] = tot_checking
        context['retirement_balance'] = tot_retirement
        context['trading_balance'] = tot_trading
        context['debt_balance'] = tot_debt
        context['net_worth'] = net_worth
        context['year'] = self.year
        ret_tot_checking, ret_tot_retirement, ret_tot_trading, ret_tot_debt, ret_net_worth = \
            self.object.return_net_worth_at_retirement()
        context['projected_net_worth'] = ret_net_worth
        return context


class UserMonthYearView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_type'] = 'month'
        context['accounts'] = Account.objects.filter(user=self.object)
        tot_checking, tot_retirement, tot_trading, tot_debt, net_worth = \
            self.object.return_net_worth_month_year(self.month, self.year)
        context['net_worth'] = net_worth
        context['checking_balance'] = tot_checking
        context['retirement_balance'] = tot_retirement
        context['trading_balance'] = tot_trading
        context['debt_balance'] = tot_debt
        context['month'] = self.month
        context['year'] = self.year
        context['needs_monthly_budget'] = self.object.needs_monthly_budget(self.month, self.year)
        ret_tot_checking, ret_tot_retirement, ret_tot_trading, ret_tot_debt, ret_net_worth = \
            self.object.return_net_worth_at_retirement()
        context['projected_net_worth'] = ret_net_worth
        date = datetime.strptime(f'{self.year}-{self.month}-01', '%Y-%B-%d')
        try:
            mbudget = MonthlyBudget.objects.get(user=self.object, month=self.month, year=self.year)
        except MonthlyBudget.DoesNotExist:
            mbudget = MonthlyBudget.objects.create(user=self.object, date=date)
            mbudget.save()
        statutory = self.object.return_statutory_month_year(self.month, self.year)
        context['statutory'] = statutory
        context['monthly_budget'] = mbudget
        takehome_pay = self.object.return_takehome_pay_month_year(self.month, self.year)
        context['takehome_pay'] = takehome_pay
        mand_exp, mort_exp, dgr_exp, disc_exp, stat_exp = \
            self.object.return_tot_expenses_by_budget_month_year(self.month, self.year)
        context['tot_mandatory_expenses'] = mand_exp
        context['tot_mortgage_expenses'] = mort_exp
        context['tot_debts_goals_retirement_expenses'] = dgr_exp
        context['tot_discretionary_expenses'] = disc_exp
        context['tot_statutory_expenses'] = stat_exp
        context['leftover_statutory'] = round(float(statutory - stat_exp), 2)
        context['leftover_mandatory'] = round(float(mbudget.mandatory - mand_exp), 2)
        context['leftover_mortgage'] = round(float(mbudget.mortgage - mort_exp), 2)
        context['leftover_dgr'] = round(float(mbudget.debts_goals_retirement - dgr_exp), 2)
        context['leftover_disc'] = round(float(mbudget.discretionary - disc_exp), 2)
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


class UserAccountsAvailable(ListView):
    model = Account
    template_name = 'finances/user_accounts.html'

    def dispatch(self, request, *args, **kwargs):
        self.userpk = kwargs['pk']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        userobj = User.objects.get(pk=self.userpk)
        return Account.objects.filter(user=userobj)


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
    template_name = 'finances/user_transfers'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.userpk = kwargs['pk']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        userobj = User.objects.get(pk=self.userpk)
        return Transfer.objects.filter(user=userobj).order_by('-date')


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
        context['deposits'] = Deposit.objects.filter(account=self.object).order_by('-date')[:25]
        context['withdrawals'] = Withdrawal.objects.filter(account=self.object).order_by('-date')[:25]
        context['balance'] = self.object.return_balance()
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
        newexpense = Withdrawal.objects.create(account=account,
                                               date=post['date'],
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


class UserWorkRelatedIncomeView(FormView):
    form_class = UserWorkIncomeExpenseForm
    template_name = 'finances/user_work_income_form.html'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def form_valid(self, form):
        post = self.request.POST
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
        fed_exp = Statutory.objects.create(user=self.user,
                                           date=date,
                                           category='Taxes',
                                           location='Work',
                                           description='Federal Income Tax',
                                           amount=fed_income_tax,
                                           )
        fed_exp.save()
        ss_exp = Statutory.objects.create(user=self.user,
                                          date=date,
                                          category='Taxes',
                                          location='Work',
                                          description='Social Security Tax',
                                          amount=social_security_tax,
                                          )
        ss_exp.save()
        medicare_exp = Statutory.objects.create(user=self.user,
                                                date=date,
                                                category='Taxes',
                                                location='Work',
                                                description='Medicare Tax',
                                                amount=medicare,
                                                )
        medicare_exp.save()
        if state_income_tax > 0.0:
            state_income_exp = Statutory.objects.create(user=self.user,
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
            ret_401k_inc = Deposit.objects.create(user=self.user,
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
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class MonthlyBudgetForUserView(FormView):
    """ View an existing Monthly Budget for a User."""
    form_class = MonthlyBudgetForUserForm
    template_name = 'finances/monthlybudget_form_for_user.html'
    success_url = '/finances'
    # TODO: Figure out how to pre-fill form with existing month/year data

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

    def form_valid(self, form):
        post = self.request.POST
        dtdate = datetime.strptime(f'{self.month}-{self.year}', '%B-%Y')
        newmb, created = MonthlyBudget.objects.get_or_create(user=self.user, month=self.month, year=self.year,
                                                             defaults={'date': dtdate,
                                                                       'mandatory': post['mandatory'],
                                                                       'mortgage': post['mortgage'],
                                                                       'debts_goals_retirement': post[
                                                                           'debts_goals_retirement'],
                                                                       'discretionary': post['discretionary']
                                                                       })
        if not created:
            newmb.date = dtdate
            newmb.mandatory = post['mandatory']
            newmb.mortgage = post['mortgage']
            newmb.debts_goals_retirement = post['debts_goals_retirement']
            newmb.discretionary = post['discretionary']
            newmb.save()
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
        newdeposit = Deposit.objects.create(account=account,
                                            date=post['date'],
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
    template_name = 'finances/income_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        post = self.request.POST
        newstatutory = Statutory.objects.create(user=self.user,
                                                date=post['date'],
                                                category=post['category'],
                                                location=post['location'],
                                                description=post['description'],
                                                amount=float(post['amount']))

        newstatutory.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class DepositUpdateView(UpdateView):
    model = Deposit
    fields = '__all__'


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
                                                                        'debts_goals_retirement': post['debts_goals_retirement'],
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
    template_name = 'account_confirm_delete.html'


class TradingAccountUpdateView(UpdateView):
    model = TradingAccount
    fields = '__all__'


class RetirementAccountView(DetailView):
    model = RetirementAccount

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the latest incomes associated with this account
        context['incomes'] = Deposit.objects.filter(account=self.object).order_by('-date')[:10]
        context['expenses'] = Withdrawal.objects.filter(account=self.object).order_by('-date')[:10]
        context['balance'] = self.object.return_balance()
        return context


class RetirementAccountCreateView(CreateView):
    model = RetirementAccount
    fields = '__all__'


class RetirementAccountDeleteView(DeleteView):
    model = RetirementAccount
    success_url = '/finances'
    template_name = 'account_confirm_delete.html'


class RetirementAccountUpdateView(UpdateView):
    model = RetirementAccount
    fields = '__all__'


# class MultipleWithdrawalsForUser(FormView):
#     template_name = 'mult_withdrawal.html'
#     form_class =


def add_expense_by_location_user_account(request, user_id: int, account_id: int, extrarows: int = 0):
    """ For a given user and associated account, add one or more expenses to add to the database."""

    try:
        user = User.objects.get(id=user_id)
    except:
        pass
        # return BadRequest('User does not exist')
    try:
        account = Account.objects.get(id=account_id, user=user)
    except:
        pass
        # return BadRequest(f'Account is not for {user.name}')

    initial_dict = {'user': user, 'account': account}
    initial_dicts = [initial_dict]
    if extrarows > 0:
        for i in range(0, extrarows):
            initial_dicts.append(initial_dict)
    ExpenseFormSet = formset_factory(ExpenseByLocForm, extra=0)
    formset = ExpenseFormSet(initial=initial_dicts)

    if request.method == 'POST':
        formset = ExpenseFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                new_expense = Withdrawal.objects.create(user=user, account=account,
                                                        date=form.cleaned_data['date'],
                                                        budget_group=form.cleaned_data['budget_group'],
                                                        category=form.cleaned_data['category'],
                                                        location=form.cleaned_data['location'],
                                                        description=form.cleaned_data['description'],
                                                        amount=form.cleaned_data['amount'],
                                                        slug_field=form.cleaned_data['slug_field'],
                                                        group=form.cleaned_data['group']
                                                        )
                new_expense.save()
            return HttpResponseRedirect(f'/finances/user={user.id}/account={account.id}/enter_expense_by_location'
                                        f'/extra=0')
        else:
            return render(request, 'finances/add_exp_loc_user_acct.html',
                          {'user': user, 'account': account, 'formset': formset, 'extra': extrarows})
    return render(request, 'finances/add_exp_loc_user_acct.html',
                  {'user': user, 'account': account, 'formset': formset, 'extra': extrarows})
