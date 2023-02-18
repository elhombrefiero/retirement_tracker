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
    # Ex. /finances/plot/debug
    path('plot/debug', pv.DebugView.as_view(), name='plot_debug')
]
