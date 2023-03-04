from dateutil.relativedelta import relativedelta
from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.core.exceptions import BadRequest
from django.forms import formset_factory
from django.views.generic import DetailView, TemplateView, FormView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone

from datetime import datetime

from finances.models import User, Account, CheckingAccount, DebtAccount, Income, Expense, TradingAccount, \
    RetirementAccount, MonthlyBudget, BUDGET_GROUP_CHOICES, Transfer
from finances.forms import ExpenseByLocForm, ExpenseForUserForm, MonthlyBudgetForUserForm, UserWorkIncomeExpenseForm, \
    UserExpenseLookupForm, IncomeForUserForm, MonthlyBudgetForUserMonthYearForm, AddDebtAccountForm, \
    AddCheckingAccountForm, AddRetirementAccountForm, AddTradingAccountForm


# Create your views here.

class IndexView(TemplateView):
    template_name = 'finances/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all()
        return context


class UserView(DetailView):
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ret_tot_checking, ret_tot_retirement, ret_tot_trading, ret_net_worth = \
            self.object.return_net_worth_at_retirement()
        context['projected_net_worth'] = ret_net_worth
        context['earliest_ret_date'] = self.object.get_earliest_retirement_date()
        context['retirement_date'] = self.object.return_retirement_datetime()
        context['accounts'] = Account.objects.filter(user=self.object)
        tot_checking, tot_retirement, tot_trading, net_worth = \
            self.object.return_net_worth()
        context['net_worth'] = net_worth
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
        tot_checking, tot_retirement, tot_trading, net_worth = \
            self.object.return_net_worth_year(self.year)
        context['net_worth'] = net_worth
        context['year'] = self.year
        ret_tot_checking, ret_tot_retirement, ret_tot_trading, ret_net_worth = \
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
        tot_checking, tot_retirement, tot_trading, net_worth = \
            self.object.return_net_worth_month_year(self.month, self.year)
        context['net_worth'] = net_worth
        context['month'] = self.month
        context['year'] = self.year
        ret_tot_checking, ret_tot_retirement, ret_tot_trading, ret_net_worth = \
            self.object.return_net_worth_at_retirement()
        context['projected_net_worth'] = ret_net_worth
        date = datetime.strptime(f'{self.year}-{self.month}-01', '%Y-%B-%d')
        try:
            mbudget = MonthlyBudget.objects.get(user=self.object, month=self.month, year=self.year)
        except MonthlyBudget.DoesNotExist:
            mbudget = MonthlyBudget.objects.create(user=self.object, date=date)
            mbudget.save()
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
        context['leftover_statutory'] = round(float(mbudget.statutory - stat_exp), 2)
        context['leftover_mandatory'] = round(float(mbudget.mandatory - mand_exp), 2)
        context['leftover_mortgage'] = round(float(mbudget.mortgage - mort_exp), 2)
        context['leftover_dgr'] = round(float(mbudget.debts_goals_retirement - dgr_exp), 2)
        context['leftover_disc'] = round(float(mbudget.discretionary - disc_exp), 2)
        return context


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
    model = Expense
    template_name = 'finances/expenses_list.html'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.userpk = kwargs['pk']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        userobj = User.objects.get(pk=self.userpk)
        return Expense.objects.filter(user=userobj).order_by('-date')


class UserIncomesAvailable(ListView):
    model = Income
    template_name = 'finances/incomes_list.html'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.userpk = kwargs['pk']
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        userobj = User.objects.get(pk=self.userpk)
        return Income.objects.filter(user=userobj).order_by('-date')


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
    model = Account

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the latest incomes associated with this account
        context['incomes'] = Income.objects.filter(account=self.object).order_by('-date')
        context['expenses'] = Expense.objects.filter(account=self.object).order_by('-date')
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
                                                     url=post['Account URL'],
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
                                                     )
        newtradeacct.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class ExpenseView(DetailView):
    model = Expense


class ExpenseCreateView(CreateView):
    model = Expense
    fields = '__all__'


class ExpenseForUserView(FormView):
    form_class = ExpenseForUserForm
    template_name = 'finances/expense_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        six_months_prior = timezone.now() + relativedelta(months=-6)
        expenses_six_mo_prior = Expense.objects.filter(user=self.user, date__gte=six_months_prior)
        distinct_cat = list(expenses_six_mo_prior.values_list('category', flat=True).distinct())
        distinct_desc = list(expenses_six_mo_prior.values_list('description', flat=True).distinct())
        distinct_where = list(expenses_six_mo_prior.values_list('where_bought', flat=True).distinct())
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
        newexpense = Expense.objects.create(user=self.user,
                                            account=account,
                                            date=post['date'],
                                            budget_group=post['budget_group'],
                                            category=post['category'],
                                            where_bought=post['where_bought'],
                                            description=post['description'],
                                            amount=post['amount'],
                                            slug_field=post['slug_field'],
                                            group=['group'],
                                            )
        newexpense.save()
        self.success_url = f'/finances/user/{self.user.pk}'
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
        print(f"account: {account.name}, {account.pk}")
        print(f"account_401k: {account_401k.name}, {account_401k.pk}")
        print(f"account_HSA: {account_HSA.name}, {account_HSA.pk}")
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

        new_inc = Income.objects.create(user=self.user,
                                        account=account,
                                        date=date,
                                        category='Gross Income',
                                        description='Gross Income',
                                        amount=gross_income)
        new_inc.save()
        fed_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[4][0],
                                         category='Taxes',
                                         where_bought='Work',
                                         description='Federal Income Tax',
                                         amount=fed_income_tax,
                                         )
        fed_exp.save()
        ss_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[4][0],
                                         category='Taxes',
                                         where_bought='Work',
                                         description='Social Security Tax',
                                         amount=social_security_tax,
                                         )
        ss_exp.save()
        medicare_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[4][0],
                                         category='Taxes',
                                         where_bought='Work',
                                         description='Medicare Tax',
                                         amount=medicare,
                                         )
        medicare_exp.save()
        state_income_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[4][0],
                                         category='Taxes',
                                         where_bought='Work',
                                         description='State Income Tax',
                                         amount=state_income_tax,
                                         )
        state_income_exp.save()
        dental_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[0][0],
                                         category='Mandatory',
                                         where_bought='Work',
                                         description='Dental',
                                         amount=dental,
                                         )
        dental_exp.save()
        medical_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[0][0],
                                         category='Mandatory',
                                         where_bought='Work',
                                         description='Medical',
                                         amount=medical,
                                         )
        medical_exp.save()
        vision_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[0][0],
                                         category='Mandatory',
                                         where_bought='Work',
                                         description='Vision',
                                         amount=vision,
                                         )
        vision_exp.save()
        ret_401k_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[2][0],
                                         category='Retirement',
                                         where_bought='Work',
                                         description='401k Contribution',
                                         amount=retirement_401k,
                                         )
        ret_401k_exp.save()
        ret_401k_inc = Income.objects.create(user=self.user,
                                             account=account_401k,
                                             date=date,
                                             category='401k',
                                             description='401k Contirbution',
                                             amount=retirement_401k)
        ret_401k_inc.save()
        ret_hsa_exp = Expense.objects.create(user=self.user,
                                         account=account,
                                         date=date,
                                         budget_group=BUDGET_GROUP_CHOICES[2][0],
                                         category='Retirement',
                                         where_bought='Work',
                                         description='HSA Contribution',
                                         amount=retirement_hsa,
                                         )
        ret_hsa_exp.save()
        ret_hsa_inc = Income.objects.create(user=self.user,
                                            account=account_HSA,
                                            date=date,
                                            category='HSA',
                                            description='HSA Contribution',
                                            amount=retirement_hsa)
        ret_hsa_inc.save()
        self.success_url = f'/finances/user/{self.user.pk}'
        return super().form_valid(form)


class MonthlyBudgetForUserView(FormView):
    form_class = MonthlyBudgetForUserForm
    template_name = 'finances/monthlybudget_form_for_user.html'
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
        dtdate = datetime.strptime(post['date'], '%Y-%d-%m')
        newmb = MonthlyBudget.objects.create(user=self.user,
                                             date=dtdate,
                                             mandatory=post['mandatory'],
                                             mortgage=post['mortgage'],
                                             debts_goals_retirement=post['debts_goals_retirement'],
                                             discretionary=post['discretionary'],
                                             statutory=post['statutory']
                                             )
        newmb.save()
        # self.success_url = 'user_monthly_budget'
        return super().form_valid(form)


class MonthlyBudgetForUserViewMonthYear(FormView):
    form_class = MonthlyBudgetForUserMonthYearForm
    template_name = 'finances/monthlybudget_form_for_user.html'
    success_url = f'/finances/'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.month = kwargs.get('month')
        self.year = kwargs.get('year')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        context['month'] = self.month
        context['year'] = self.year
        budget_mand, budget_mort, statutory, budget_dgr, budget_disc = \
            self.user.estimate_budget_for_month_year(self.month, self.year)
        context['est_mand'] = budget_mand
        context['est_mort'] = budget_mort
        context['statutory'] = statutory
        context['est_dgr'] = budget_dgr
        context['est_disc'] = budget_disc

        return context


class ExpenseDeleteView(DeleteView):
    model = Expense
    success_url = '/finances'


class ExpenseUpdateView(UpdateView):
    model = Expense
    fields = '__all__'


class IncomeView(DetailView):
    model = Income


class IncomeCreateView(CreateView):
    model = Income
    fields = '__all__'


class IncomeForUserView(FormView):
    """ Input an income for a user. """
    form_class = IncomeForUserForm
    template_name = 'finances/income_form_for_user.html'
    success_url = '/finances'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.user = User.objects.get(pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        six_months_prior = timezone.now() + relativedelta(months=-6)
        incomes_six_months_prior = Income.objects.filter(user=self.user, date__gte=six_months_prior)
        distinct_cat = list(incomes_six_months_prior.values_list('category', flat=True).distinct())
        distinct_desc = list(incomes_six_months_prior.values_list('description', flat=True).distinct())
        distinct_group = list(incomes_six_months_prior.values_list('group', flat=True).distinct())
        context['user'] = self.user
        context['distinct_cat'] = distinct_cat
        context['distinct_desc'] = distinct_desc
        context['distinct_group'] = distinct_group

        return context


class IncomeDeleteView(DeleteView):
    model = Income
    success_url = '/finances'


class IncomeUpdateView(UpdateView):
    model = Income
    fields = '__all__'


class MonthlyBudgetView(DetailView):
    model = MonthlyBudget


class MonthlyBudgetCreateView(CreateView):
    model = MonthlyBudget
    fields = '__all__'


class MonthlyBudgetDeleteView(DeleteView):
    model = MonthlyBudget
    success_url = '/finances'


class MonthlyBudgetUpdateView(UpdateView):
    model = MonthlyBudget
    fields = '__all__'


class TradingAccountView(DetailView):
    model = TradingAccount

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the latest incomes associated with this account
        context['incomes'] = Income.objects.filter(account=self.object).order_by('-date')[:10]
        context['expenses'] = Expense.objects.filter(account=self.object).order_by('-date')[:10]
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
        context['incomes'] = Income.objects.filter(account=self.object).order_by('-date')[:10]
        context['expenses'] = Expense.objects.filter(account=self.object).order_by('-date')[:10]
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


def add_expense_by_location_user_account(request, user_id: int, account_id: int, extrarows: int = 0):
    """ For a given user and associated account, add one or more expenses to add to the database."""

    try:
        user = User.objects.get(id=user_id)
    except:
        return BadRequest('User does not exist')
    try:
        account = Account.objects.get(id=account_id, user=user)
    except:
        return BadRequest(f'Account is not for {user.name}')

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
                new_expense = Expense.objects.create(user=user, account=account,
                                                     date=form.cleaned_data['date'],
                                                     budget_group=form.cleaned_data['budget_group'],
                                                     category=form.cleaned_data['category'],
                                                     where_bought=form.cleaned_data['where_bought'],
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
