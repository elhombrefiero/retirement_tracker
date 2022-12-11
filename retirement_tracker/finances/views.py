from django.shortcuts import render

from finances.models import User, Account

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


def account_overview(request, account_id: int):
    account = Account.objects.get(id=account_id)
    balance = account.return_balance()

    return render(request, 'finances/account_overview.html', {'account': account, 'balance': balance})
