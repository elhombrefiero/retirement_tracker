#!/usr/bin/env python3

# Python Library Imports

# Other Imports
from django.urls import path

from finances import plot_views as pv

app_name = 'finances'

urlpatterns = [
    # Ex. /finances/plot/user/1/monthly_budget/January/2022/budgeted
    path('plot/user/<int:pk>/monthly_budget/<str:month>/<int:year>/budgeted', pv.MonthlyBudgetPlotView.as_view(),
         name='plot_monthlybudget_for_user'),
    # Ex. /finances/plot/user/1/expenses/January/2022/by_budgetgroup
    path('plot/user/<int:pk>/expenses/<str:month>/<int:year>/by_budgetgroup', pv.ActualExpensesByBudgetGroup.as_view(),
         name='plot_expenses_by_budget_group'),
    # Ex. /finances/plot/user/1/expenses/January/2022/cumulative_expenses
    path('plot/user/<int:pk>/expenses/<str:month>/<int:year>/cumulative_expenses',
         pv.ExpenseCumulativeMonthYearPlotView.as_view(), name='plot_expenses_cumulative_month_year'),
    # Ex. /finances/plot/user/1/incomes/January/2022/cumulative_incomes
    path('plot/user/<int:pk>/incomes/<str:month>/<int:year>/cumulative_incomes',
         pv.IncomeCumulativeMonthYearPlotView.as_view(), name='plot_incomes_cumulative_month_year'),
    # Ex. /finances/plot/user/1/totals/January/2022/cumulative_totals
    path('plot/user/<int:pk>/totals/<str:month>/<int:year>/cumulative_totals',
         pv.TotalCumulativeMonthYearPlotView.as_view(), name='plot_totals_cumulative_month_year'),
    # Ex. /finances/plot/user/1/bar_budgeted_vs_spent/January/2023/
    path('plot/user/<int:pk>/bar_budgeted_vs_spent/<str:month>/<int:year>',
         pv.ExpenseSpentAndBudgetPlotView.as_view(), name='plot_bar_budget_vs_spent_month_year'),
    # Ex. /finances/plot/user/1/bar_top5_category/January/2023
    path('plot/user/<int:pk>/bar_top5_category/<str:month>/<int:year>',
         pv.ExpenseByCategoryPlotView.as_view(), name='plot_top5_by_category'),
    # Ex. /finances/plot/user/1/bar_top5_description/January/2023
    path('plot/user/<int:pk>/bar_top5_description/<str:month>/<int:year>',
         pv.ExpenseByDescriptionPlotView.as_view(), name='plot_top5_by_description'),
    # Ex. /finances/plot/user/1/bar_top5_location/January/2023
    path('plot/user/<int:pk>/bar_top5_location/<str:month>/<int:year>',
         pv.ExpenseByLocationPlotView.as_view(), name='plot_top5_by_location'),
    # Ex. /finances/data/user/1/monthly_budget/January/2023
    path('data/user/<int:pk>/monthly_budget/<str:month>/<int:year>',
         pv.MonthlyBudgetByUserMonthYear.as_view(), name='data_monthlybudget_by_user_month_year'),
    # Ex. /finances/data/account/1/projected_checkingbalance
    path('data/account/<int:pk>/projected_checkingbalance', pv.CheckingAccountBalanceByTime.as_view(),
         name='data_projected_checkingaccount_balance'),
    # Ex. /finances/data/account/1/projected_retirementbalance
    path('data/account/<int:pk>/projected_retirementbalance', pv.RetirementAccountBalanceByTime.as_view(),
         name='data_projected_retirementaccount_balance'),
    # Ex. /finances/data/account/1/projected_debtbalance
    path('data/account/<int:pk>/projected_debtbalance', pv.DebtAccountBalanceByTime.as_view(),
         name='data_projected_debtaccount_balance'),
    # Ex. /finances/data/user/1/report/all
    path('data/user/<int:pk>/report/<str:all>', pv.UserReportDataCustom.as_view(), name='data_user_all'),
    # Ex. /finances/data/user/1/report/2022/2023
    path('data/user/<int:pk>/report/<int:start_year>/<int:end_year>', pv.UserReportDataCustom.as_view(),
         name='data_user_year_to_year'),
    # Ex. /finances/data/user/1/report/2022/March/2023
    path('data/user/<int:pk>/report/<int:start_year>/<str:start_month>/<int:end_year>', pv.UserReportDataCustom.as_view(),
         name='data_user_yearmonth_to_year'),
    # Ex. /finances/data/user/1/report/2022/March/2023/March
    path('data/user/<int:pk>/report/<int:start_year>/<str:start_month>/<int:end_year>/<str:end_month>',
         pv.UserReportDataCustom.as_view(), name='data_user_yearmonth_to_yearmonth'),
    # Ex. /finances/plot/debug
    path('plot/debug', pv.DebugView.as_view(), name='plot_debug')
]
