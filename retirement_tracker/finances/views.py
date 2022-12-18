from django.shortcuts import render, HttpResponseRedirect

from finances.models import User, Account
from finances.forms import UserForm


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
