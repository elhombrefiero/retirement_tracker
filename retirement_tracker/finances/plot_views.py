#!/usr/bin/env python3

from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView

from finances.models import User, MonthlyBudget
from finances.utils import chartjs_utils as cjs


def get_pie_chart_config(name):
    "Returns the configuration for a pie chart minus the data using chart.js"
    config = {}
    config.update({
        'type': 'pie',
        'options': {
            'responsive': True,
            'plugins': {
                'legend': {
                    'position': 'bottom',
                },
                'title': {
                    'display': True,
                    'text': f'{name}'
                }
            }
        }
    }
    )
    return config


class MonthlyBudgetPlotView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            mb = MonthlyBudget.objects.get(user=self.user, month=self.month, year=self.year)
        except MonthlyBudget.DoesNotExist:
            return redirect('user_add_monthly_budget_month_year', self.user.pk, self.month, self.year)
        config = get_pie_chart_config('Budgeted')
        data = {
            'labels': ['Mandatory', 'Statutory', 'Mortgage', 'Debts, Goals, Retirement', 'Discretionary'],
            'datasets': [
                {
                    'label': 'Budgeted',
                    'data': [mb.mandatory, mb.statutory, mb.mortgage, mb.debts_goals_retirement, mb.discretionary],
                    'backgroundColor': [cjs.get_color('red'), cjs.get_color('orange'), cjs.get_color('yellow'), cjs.get_color('green'), cjs.get_color('blue')],
                }
            ]
        }
        return_dict = dict()
        return_dict['config'] = config
        return_dict['data'] = data

        return JsonResponse(return_dict)


class ActualExpensesByBudgetGroup(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        mand_act, mort_act, dgr_act, disc_act, stat_act = self.user.return_tot_expenses_by_budget_month_year(self.month,
                                                                                                             self.year)
        config = get_pie_chart_config('Actual')

        data = {
            'labels': ['Mandatory', 'Statutory', 'Mortgage', 'Debts, Goals, Retirement', 'Discretionary'],
            'datasets': [
                {
                    'label': 'Actual',
                    'data': [mand_act, stat_act, mort_act, dgr_act, disc_act],
                    'backgroundColor': [cjs.get_color('red'), cjs.get_color('orange'), cjs.get_color('yellow'),
                                        cjs.get_color('green'), cjs.get_color('blue')],
                }
            ]
        }
        return_dict = dict()
        return_dict['data'] = data
        return_dict['config'] = config

        return JsonResponse(return_dict)


class DebugView(TemplateView):
    template_name = 'finances/debug.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['userpk'] = 2
        context['month'] = 'January'
        context['year'] = 2023
        return context
