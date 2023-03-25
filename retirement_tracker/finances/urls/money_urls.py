#!/usr/bin/env python3

# Python Library Imports

# Other Imports
from django.urls import path

from finances import views

app_name = 'finances'

urlpatterns = [
    # Ex. /finances/
    path('', views.IndexView.as_view(), name='index'),
    # Ex. /finances/user_overview/pk
    path('user/<int:pk>/', views.UserView.as_view(), name='user_overview'),
    # Ex. /finances/user/1/add_checking_account
    path('user/<int:pk>/add_checking_account', views.CheckingAccountForUserView.as_view(),
         name='user_add_checking_account'),
    # Ex. /finances/user/1/add_retirement_account
    path('user/<int:pk>/add_retirement_account', views.RetirementAccountForUserView.as_view(),
         name='user_add_retirement_account'),
    # Ex. /finances/user/1/add_debt_account
    path('user/<int:pk>/add_debt_account', views.DebtAccountForUserView.as_view(), name='user_add_debt_account'),
    # Ex. /finances/user/1/add_trading_account
    path('user/<int:pk>/add_trading_account', views.TradingAccountForUserView.as_view(),
         name='user_add_trading_account'),
    # Ex. /finances/user/1/add_withdrawal
    path('user/<int:pk>/add_withdrawal', views.WithdrawalForUserView.as_view(), name='user_add_withdrawal'),
    # Ex. /finances/user/1/add_income
    path('user/<int:pk>/add_deposit', views.DepositForUserView.as_view(), name='user_add_deposit'),
    # Ex. /finances/user/1/transfer_money
    path('user/<int:pk>/transfer_money', views.UserTransferView.as_view(), name='user_transfer'),
    # Ex. /finances/user/1/add_statutory
    path('user/<int:pk>/add_statutory', views.StatutoryForUserView.as_view(), name='user_add_statutory'),
    # Ex. /finances/user/1/add_monthly_budget
    path('user/<int:pk>/add_monthly_budget', views.MonthlyBudgetForUserView.as_view(), name='user_add_monthly_budget'),
    # Ex. /finances/user/1/accounts
    path('user/<int:pk>/accounts', views.UserAccountsAvailable.as_view(), name='user_available_accounts'),
    # Ex. /finances/user/1/expenses
    path('user/<int:pk>/expenses', views.UserExpensesAvailable.as_view(), name='user_available_expenses'),
    # Ex. /finances/user/1/incomes
    path('user/<int:pk>/incomes', views.UserIncomesAvailable.as_view(), name='user_available_incomes'),
    # Ex. /finances/user/1/statutory
    path('user/<int:pk>/statutory_entries', views.UserStatutoryAvailable.as_view(), name='user_available_statutory'),
    # Ex. /finances/user/1/transfers
    path('user/<int:pk>/transfers', views.UserStatutoryAvailable.as_view(), name='user_available_statutory'),
    # Ex. /finances/user/1/reports
    path('user/<int:pk>/reports', views.UserReportsAvailable.as_view(), name='user_available_reports'),
    # Ex. /finances/user/1/monthly_budgets
    path('user/<int:pk>/monthly_budgets', views.UserMonthlyBudgetsAvailable.as_view(), name='user_available_monthly_budgets'),
    # Ex. /finances/user/1/2022
    path('user/<int:pk>/<int:year>', views.UserYearView.as_view(), name='user_year'),
    # Ex. /finances/usr/1/January/2022
    path('user/<int:pk>/<str:month>/<int:year>/', views.UserMonthYearView.as_view(), name='user_month_year'),
    # Ex. /finances/user/1/January/2022/add_monthly_budget
    path('user/<int:pk>/<str:month>/<int:year>/add_monthly_budget', views.MonthlyBudgetForUserView.as_view(),
         name='user_add_monthly_budget_month_year'),
    path('user/<int:pk>/<str:month>/<int:year>/view_monthly_budget', views.MonthlyBudgetForUserViewMonthYear.as_view(), name='user_monthly_budget'),
    # Ex. /finances/user/1/lookup_expenses
    path('user/<int:pk>/lookup_expenses', views.ExpenseLookupForUserView.as_view(), name='user_expense_lookup'),
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
    path('withdrawal_overview/<int:pk>/', views.WithdrawalView.as_view(), name='withdrawal_overview'),
    # Ex. /finances/income_overview/pk
    path('deposit_overview/<int:pk>/', views.DepositView.as_view(), name='deposit_overview'),
    # Ex. /finances/statutory_overview/pk
    path('statutory_overview/<int:pk>/', views.StatutoryView.as_view(), name='statutory_overview'),
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
    path('update_deposit/<int:pk>', views.DepositUpdateView.as_view(), name='deposit-update'),
    # Ex. /finances/update_withdrawal/1
    path('update_withdrawal/<int:pk>', views.WithdrawalUpdateView.as_view(), name='withdrawal-update'),
    # Ex. /finances/update_depsoit/1
    path('update_deposit/<int:pk>', views.DepositUpdateView.as_view(), name='deposit-update'),
    # Ex. /finances/update_withdrawal/1
    path('update_withdrawal/<int:pk>', views.WithdrawalUpdateView.as_view(), name='withdrawal-update'),
    # Ex. /finances/update_statutory/1
    path('update_statutory/<int:pk>', views.StatutoryUpdateView.as_view(), name='statutory-update'),
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
    path('delete_deposit/<int:pk>', views.DepositDeleteView.as_view(), name='deposit-delete'),
    # Ex. finances/delete_expense/1
    path('delete_withdrawal/<int:pk>', views.WithdrawalDeleteView.as_view(), name='withdrawal-delete'),
    # Ex. finances/delete_withdrawal/1
    path('delete_statutory/<int:pk>', views.StatutoryDeleteView.as_view(), name='statutory-delete'),
    # Ex. /finances/user=1/enter_expense_by_location/extra=0
    path('user=<int:user_id>/enter_withdrawal_by_location/extra=<int:extrarows>',
         views.add_expense_by_location_user_account, name='add_withdrawal_by_loc'),
]
