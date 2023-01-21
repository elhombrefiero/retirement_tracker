#!/usr/bin/env python3

# Python Library Imports

# Other Imports
from django.urls import path
from django.views.generic import TemplateView

from finances import views

app_name = 'finances'

urlpatterns = [
    # Ex. /finances/
    path('', views.IndexView.as_view(), name='index'),
    # Ex. /finances/user_overview/pk
    path('user/<int:pk>/', views.UserView.as_view(), name='user_overview'),
    # Ex. /finances/user/1/add_expense
    path('user/<int:pk>/add_expense', views.ExpenseForUserView.as_view(), name='user_add_expense'),
    # Ex. /finances/usr/1/January/2022
    path('user/<int:pk>/<str:month>/<int:year>/', views.UserMonthYearView.as_view(), name='user_month_year'),
    # Ex. /finances/user/1/January/2022/add_monthly_budget
    path('user/<int:pk>/<str:month>/<int:year>/add_monthly_budget', views.MonthlyBudgetForUserViewMonthYear.as_view(),
         name='user_add_monthly_budget_month_year'),
    # Ex. /finances/user/1/add_work_income
    path('user/<int:pk>/add_work_income', views.UserWorkRelatedIncomeView.as_view(), name='user_work_income'),
    # Ex. /finances/account_overview/pk
    path('account_overview/<int:pk>/', views.AccountView.as_view(), name='account_overview'),
    # Ex. /finances/retirementaccount_overview/pk
    path('retirementaccount_overview/<int:pk>/', views.RetirementAccountView.as_view(), name='raccount_overview'),
    # Ex. /finances/tradingaccount_overview/pk
    path('tradingaccount_overview/<int:pk>/', views.TradingAccountView.as_view(), name='taccount_overview'),
    # Ex. /finances/monthlybudget_overview/pk
    path('monthlybudget_overview/<int:pk>/', views.MonthlyBudgetView.as_view(), name='mbudget_overview'),
    # Ex. /finances/expense_overview/pk
    path('expense_overview/<int:pk>/', views.ExpenseView.as_view(), name='expense_overview'),
    # Ex. /finances/income_overview/pk
    path('income_overview/<int:pk>/', views.IncomeView.as_view(), name='income_overview'),
    # Ex. /finances/add_user
    path('add_user/', views.UserCreateView.as_view(), name='add_user'),
    # Ex. /finances/add_account
    path('add_account/', views.AccountCreateView.as_view(), name='account-add'),
    # Ex. /finances/add_retirement_account
    path('add_retirement_account/', views.RetirementAccountCreateView.as_view(), name='raccount-add'),
    # Ex. /finances/add_trading_account
    path('add_trading_account/', views.TradingAccountCreateView.as_view(), name='taccount-add'),
    # Ex. /finances/add_monthly_budget
    path('add_monthly_budget/', views.MonthlyBudgetCreateView.as_view(), name='mbudget-add'),
    # Ex. /finances/add_income
    path('add_income/', views.IncomeCreateView.as_view(), name='income-add'),
    # Ex. /finances/add_expense
    path('add_expense/', views.ExpenseCreateView.as_view(), name='expense-add'),
    # Ex. /finances/update_user/1
    path('update_user/<int:pk>', views.UserUpdateView.as_view(), name='user-update'),
    # Ex. /finances/update_account/1
    path('update_account/<int:pk>', views.AccountUpdateView.as_view(), name='account-update'),
    # Ex. /finances/update_retirement_account/1
    path('update_retirement_account/<int:pk>', views.RetirementAccountUpdateView.as_view(), name='raccount-update'),
    # Ex. /finances/update_trading_account/1
    path('update_trading_account/<int:pk>', views.TradingAccountUpdateView.as_view(), name='taccount-update'),
    # Ex. /finances/update_monthly_budget/1
    path('update_monthly_budget/<int:pk>', views.MonthlyBudgetUpdateView.as_view(), name='mbudget-update'),
    # Ex. /finances/update_income/1
    path('update_income/<int:pk>', views.IncomeUpdateView.as_view(), name='income-update'),
    # Ex. /finances/update_expense/1
    path('update_expense/<int:pk>', views.ExpenseUpdateView.as_view(), name='expense-update'),
    # Ex. /finances/delete_user/1
    path('delete_user/<int:pk>', views.UserDeleteView.as_view(), name='user-delete'),
    # Ex. finances/delete_account/1
    path('delete_account/<int:pk>', views.AccountDeleteView.as_view(), name='account-delete'),
    # Ex. finances/delete_retirement_account/1
    path('delete_retirement_account/<int:pk>', views.RetirementAccountDeleteView.as_view(), name='raccount-delete'),
    # Ex. finances/delete_trading_account/1
    path('delete_trading_account/<int:pk>', views.TradingAccountDeleteView.as_view(), name='taccount-delete'),
    # Ex. finances/delete_monthly_budget/1
    path('delete_monthly_budget/<int:pk>', views.MonthlyBudgetDeleteView.as_view(), name='mbudget-delete'),
    # Ex. finances/delete_income/1
    path('delete_income/<int:pk>', views.IncomeDeleteView.as_view(), name='income-delete'),
    # Ex. finances/delete_expense/1
    path('delete_expense/<int:pk>', views.ExpenseDeleteView.as_view(), name='expense-delete'),
    # Ex. /finances/user=user_id/account=account_id/enter_expense_by_location/extra=0
    path('user=<int:user_id>/account=<int:account_id>/enter_expense_by_location/extra=<int:extrarows>',
         views.add_expense_by_location_user_account, name='add_exp_by_loc'),
]
