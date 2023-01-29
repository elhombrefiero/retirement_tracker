#!/usr/bin/env python3

# Python Library Imports

# Other Imports
from django.urls import path

from finances import plot_views as pv

app_name = 'finances'

urlpatterns = [
    # Ex. /finances/plot/user/1/monthly_budget/January/2022/actual
    path('plot/user/<int:pk>/monthly_budget/<str:month>/<int:year>/actual', pv.MonthlyBudgetPlotView.as_view(), name='plot_monthlybudget_for_user')
]
