#!/usr/bin/env python3

# Python Library Imports

# Other Imports
from django.urls import path
from django.views.generic import TemplateView

from finances import views

app_name = 'finances'

urlpatterns = [
    # Ex. /finances/
    path('', views.index, name='index'),
    # Ex. /finances/user_overview=id
    path('user_overview/<int:pk>/', views.UserView.as_view(), name='user_overview'),
    # Ex. /finances/account_overview=id
    path('account_overview/<int:pk>/', views.AccountView.as_view(), name='account_overview'),
    # Ex. /finances/add_user
    path('add_user/', views.UserCreateView.as_view(), name='add_user'),
    # Ex. /finances/add_account
    path('add_account/', views.AccountCreateView.as_view(), name='account-add'),
    # Ex. /finances/update_user/1
    path('update_user/<int:pk>', views.UserUpdateView.as_view(), name='user-update'),
    # Ex. /finances/update_account/1
    path('update_account/<int:pk>', views.AccountUpdateView.as_view(), name='account-update'),
    # Ex. /finances/delete_user/1
    path('delete_user/<int:pk>', views.UserDeleteView.as_view(), name='user-delete'),
    # Ex. finances/delete_account/1
    path('delete_account/<int:pk>', views.AccountDeleteView.as_view(), name='account-delete'),
    # Ex. /finances/user=<user_id>/add_trading_account
    path('user=<int:user_id>/add_trading_account', views.add_trading_account_to_user, name='add_trading_account_to_user'),
    # Ex. /finances/user=<user_id>/add_retirement_account
    path('user=<int:user_id>/add_retirement_account', views.add_retirement_account_to_user,
         name='add_retirement_account_to_user'),
    # Ex. /finances/user=user_id/account=account_id/enter_expense_by_location/extra=0
    path('user=<int:user_id>/account=<int:account_id>/enter_expense_by_location/extra=<int:extrarows>',
         views.add_expense_by_location_user_account, name='add_exp_by_loc'),
]
