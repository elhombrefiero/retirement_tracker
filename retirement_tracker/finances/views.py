from dateutil.relativedelta import relativedelta
from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.core.exceptions import BadRequest
from django.forms import formset_factory
from django.views.generic import DetailView, TemplateView, FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone

from datetime import datetime

from finances.models import User, Account, Income, Expense, TradingAccount, RetirementAccount, MonthlyBudget
from finances.forms import ExpenseByLocForm, ExpenseForUserForm, MonthlyBudgetForUserForm, UserWorkIncomeExpenseForm, UserExpenseLookupForm, IncomeForUserForm


# Create your views here.
# TODO: Add views where the user can find month/year summaries and monthly budgets for user

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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


class ExpenseView(DetailView):
    model = Expense


class ExpenseCreateView(CreateView):
    model = Expense
    fields = '__all__'


class ExpenseForUserView(FormView):

    form_class = ExpenseForUserForm
    template_name = 'finances/expense_form_for_user.html'

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


class MonthlyBudgetForUserViewMonthYear(FormView):

    form_class = MonthlyBudgetForUserForm
    template_name = 'finances/monthlybudget_form_for_user.html'

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
