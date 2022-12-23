from django.shortcuts import render, HttpResponseRedirect
from django.core.exceptions import BadRequest
from django.forms import formset_factory

from finances.models import User, Account, Expense
from finances.forms import UserForm, ExpenseByLocForm


# Create your views here.


def index(request):
    """ Index of finance tracker. Contains a list of users. """
    users = User.objects.all()

    return render(request, 'finances/index.html', {'users': users})


def user_main(request, user_id: int):
    """ Contains links for each account for the user. """
    user = User.objects.get(id=user_id)
    user_accounts = Account.objects.filter(user=user)

    return render(request, 'finances/user_overview.html', {'user': user,
                                                           'accounts': user_accounts})


def add_user(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        if user_form.is_valid():
            user = User.objects.create(name=user_form.cleaned_data['name'],
                                       date_of_birth=user_form.cleaned_data['date_of_birth'],
                                       retirement_age=user_form.cleaned_data['retirement_age'],
                                       percent_withdrawal_at_retirement=user_form.cleaned_data[
                                           'percent_withdrawal_at_retirement'])
            user.save()
            return HttpResponseRedirect(f'/finances/user_overview={user.id}')
    else:
        userform = UserForm()
        return render(request, 'finances/add_user.html', {'form': userform})


def account_overview(request, account_id: int):
    account = Account.objects.get(id=account_id)
    balance = account.return_balance()

    return render(request, 'finances/account_overview.html', {'account': account, 'balance': balance})


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
