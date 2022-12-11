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
    path('user_overview=<int:user_id>/', views.user_main, name='user_overview'),
    # Ex. /finances/account_overview=id
    path('account_overview=<int:account_id>/', views.account_overview, name='account_overview'),
    # Ex. /finances/add_user
    path('add_user/', views.add_user, name='add_user')
]
