from django.shortcuts import render, HttpResponseRedirect
from django.core.exceptions import BadRequest
from django.forms import formset_factory
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from finances.models import User, Account, Income, Expense, TradingAccount, RetirementAccount, MonthlyBudget
from finances.forms import ExpenseByLocForm


# Create your views here.

class UserView(DetailView):
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accounts'] = Account.objects.filter(user=self.object)
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
        context['incomes'] = Income.objects.filter(account=self.object).order_by('-date')[:10]
        context['expenses'] = Expense.objects.filter(account=self.object).order_by('-date')[:10]
        context['balance'] = self.object.return_balance()
        return context


class ExpenseView(DetailView):
    model = Expense


class ExpenseCreateView(CreateView):
    model = Expense
    fields = '__all__'


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


def index(request):
    """ Index of finance tracker. Contains a list of users. """
    users = User.objects.all()

    return render(request, 'finances/index.html', {'users': users})


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
