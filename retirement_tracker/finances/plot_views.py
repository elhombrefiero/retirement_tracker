#!/usr/bin/env python3

from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView
from django.db.models.functions import Trunc

from finances.models import User, MonthlyBudget
from finances.utils import chartjs_utils as cjs

from datetime import datetime
from dateutil.relativedelta import relativedelta


def get_pie_chart_config(name):
    """Returns the configuration for a pie chart minus the data using chart.js"""
    config = {}
    config.update({
        'type': 'pie',
        'options': {
            'responsive': True,
            'legend': {
                'position': 'bottom',
                },
            'title': {
                'display': True,
                'text': f'{name}'
            }
        }
    }
    )
    return config


def get_line_chart_config(name):
    """ Returns the configuration for a line chart"""
    config = {'type': 'scatter',
              'options': {
                  'responsive': True,
                  'plugins': {
                      'title': {
                          'display': True,
                          'text': f'{name}'
                      },
                  },
                  'interaction': {
                      'intersect': False,
                  },
                  'layout': {
                      'padding': 20
                  },
                  'scales': {
                      'x': {
                          'type': 'time',
                          'time': {
                              'unit': 'day',
                          },
                          'display': True,
                          'title': {
                              'display': True,
                              'text': 'Date'
                          }
                      },
                      'y': {
                          'display': True,
                          'title': {
                              'display': True,
                              'text': 'Value'
                          },
                          # 'suggestedMin': -10,
                          # 'suggestedMax': 200
                      }
                  }
              },
              }

    return config


def get_bar_chart_config(name):
    """ Returns the configuration for the bar chart."""

    config = dict()

    config['type'] = 'bar'

    config['options'] = {
        'title': {
            'display': True,
            'text': f'{name}'
        },
        'maintainAspectRatio': False,
        # 'padding': {
        #     'left': 20,
        # },
        'responsive': True,
        'legend': {
            'position': 'bottom'
        },
        'scales': {
            'y': {
                'beginAtZero': True
            }
        }
    }

    config['type'] = 'bar'

    return config


class ExpenseSpentAndBudgetPlotView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        config = get_bar_chart_config('Budgeted vs. Spent')
        data = dict()
        labels = ['Mandatory', 'Mortgage', 'Statutory', 'Debts, Goals, Retirement', 'Discretionary']
        data['labels'] = labels
        try:
            mb = MonthlyBudget.objects.get(user=self.user, month=self.month, year=self.year)
        except MonthlyBudget.DoesNotExist:
            return redirect('user_add_monthly_budget_month_year', self.user.pk, self.month, self.year)

        mand_exp, mort_exp, dgr_exp, disc_exp, stat_exp = self.user.return_aggregated_monthly_expenses_by_budgetgroup(self.month, self.year)

        datasets = list()
        budgeted_info = {
            'label': 'Budgeted',
            'data': [mb.mandatory, mb.mortgage, stat_exp, mb.debts_goals_retirement, mb.discretionary],
            'borderColor': cjs.get_color('red'),
            'backgroundColor': cjs.get_color('red', 0.5)
        }
        datasets.append(budgeted_info)

        actual_info = {
                'label': 'Actual',
                'data': [mand_exp, mort_exp, stat_exp, dgr_exp, disc_exp],
                'borderColor': cjs.get_color('blue'),
                'backgroundColor': cjs.get_color('blue', 0.5)
            }
        datasets.append(actual_info)

        data['datasets'] = datasets
        config['data'] = data

        return JsonResponse(config)


class ExpenseByCategoryPlotView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        config = get_bar_chart_config('Expenses by Category')
        data = dict()
        top_5cat = self.user.return_top_category(self.month, self.year, 5)

        labels = list()
        data_sum = list()
        for topcat in top_5cat:
            labels.append(topcat['category'])
            data_sum.append(topcat['sum'])

        data['labels'] = labels
        datasets = list()
        cat_sum = {
            'label': 'Total',
            'data': data_sum,
            'borderColor': cjs.get_color('black'),
            'backgroundColor': cjs.get_color('black', 0.5)
        }
        datasets.append(cat_sum)

        data['datasets'] = datasets
        config['data'] = data

        return JsonResponse(config)


class ExpenseByDescriptionPlotView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        config = get_bar_chart_config('Expenses by Description')
        data = dict()
        top_5desc = self.user.return_top_description(self.month, self.year, 5)

        labels = list()
        data_sum = list()
        for topdesc in top_5desc:
            labels.append(topdesc['description'])
            data_sum.append(topdesc['sum'])

        data['labels'] = labels
        datasets = list()
        desc_sum = {
            'label': 'Total',
            'data': data_sum,
            'borderColor': cjs.get_color('black'),
            'backgroundColor': cjs.get_color('black', 0.5)
        }
        datasets.append(desc_sum)

        data['datasets'] = datasets
        config['data'] = data

        return JsonResponse(config)


class MonthlyBudgetByUserMonthYear(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return_json = {'mandatory': 0.0,
                       'mortgage': 0.0,
                       'debts_goals_retirement': 0.0,
                       'discretionary': 0.0}
        try:
            mb = MonthlyBudget.objects.get(user=self.user, month=self.month, year=self.year)
        except MonthlyBudget.DoesNotExist:
            return JsonResponse(return_json)

        return_json = {'mandatory': mb.mandatory,
                       'mortgage': mb.mortgage,
                       'debts_goals_retirement': mb.debts_goals_retirement,
                       'discretionary': mb.discretionary}

        return JsonResponse(return_json)


class ExpenseByLocationPlotView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        config = get_bar_chart_config('Expenses by Location')
        data = dict()
        top_5loc = self.user.return_top_location(self.month, self.year, 5)

        labels = list()
        data_sum = list()
        for toploc in top_5loc:
            labels.append(toploc['location'])
            data_sum.append(toploc['sum'])

        data['labels'] = labels
        datasets = list()
        loc_sum = {
            'label': 'Total',
            'data': data_sum,
            'borderColor': cjs.get_color('black'),
            'backgroundColor': cjs.get_color('black', 0.5)
        }
        datasets.append(loc_sum)

        data['datasets'] = datasets
        config['data'] = data

        return JsonResponse(config)


class IncomeCumulativeMonthYearPlotView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        start_date = datetime.strptime(f'{self.month}-01-{self.year}', '%B-%d-%Y')
        end_date = start_date + relativedelta(months=+1)
        config = get_line_chart_config(f'Cumulative Incomes for {self.month}, {self.year}')
        cumulative_income = self.user.return_cumulative_incomes(start_date, end_date)
        return_dict = dict()
        return_dict['config'] = config

        xy_data = []
        labels = []
        for income_day in cumulative_income:
            # TODO: Try converting the date to timestamp
            labels.append(income_day)
            xy_data.append(
                {'x': income_day, 'y': float(cumulative_income[income_day])})

        data = {
            'labels': labels,
            'datasets': [{
                'label': 'Cumulative Incomes',
                'backgroundColor': cjs.get_color('green', 0.5),
                'borderColor': cjs.get_color('green'),
                'fill': False,
                'data': xy_data
            }]
        }

        return_dict['data'] = data

        return JsonResponse(return_dict)


class ExpenseCumulativeMonthYearPlotView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        start_date = datetime.strptime(f'{self.month}-01-{self.year}', '%B-%d-%Y')
        end_date = start_date + relativedelta(months=+1)
        config = get_line_chart_config(f'Cumulative Expenses for {self.month}, {self.year}')
        cumulative_expenses = self.user.return_cumulative_expenses(start_date, end_date)

        return_dict = dict()
        return_dict['config'] = config

        xy_data = []
        labels = []
        for expensedate in cumulative_expenses:
            labels.append(expensedate)
            xy_data.append(
                {'x': expensedate, 'y': float(cumulative_expenses[expensedate])})

        data = {
            'labels': labels,
            'datasets': [{
                'label': 'Cumulative Expenses',
                'backgroundColor': cjs.get_color('red', 0.5),
                'borderColor': cjs.get_color('red'),
                'fill': False,
                'data': xy_data
            }]
        }

        return_dict['data'] = data

        return JsonResponse(return_dict)


class TotalCumulativeMonthYearPlotView(DetailView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']
        userpk = kwargs['pk']
        self.user = User.objects.get(pk=userpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        start_date = datetime.strptime(f'{self.month}-01-{self.year}', '%B-%d-%Y')
        end_date = start_date + relativedelta(months=+1)
        config = get_line_chart_config(f'Cumulative Total for {self.month}, {self.year}')
        cumulative_total = self.user.return_cumulative_total(start_date, end_date)

        return_dict = dict()
        return_dict['config'] = config

        xy_data = []
        labels = []
        for date_key in sorted(cumulative_total.keys()):
            labels.append(date_key)
            xy_data.append(
                {'x': date_key, 'y': float(cumulative_total[date_key]['cumulative'])})

        data = {
            'labels': labels,
            'datasets': [{
                'label': 'Cumulative Total',
                'backgroundColor': cjs.get_color('red', 0.5),
                'borderColor': cjs.get_color('red'),
                'fill': False,
                'data': xy_data
            }]
        }

        return_dict['data'] = data

        return JsonResponse(return_dict)


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
        statutory = self.user.return_statutory_month_year(self.month, self.year)
        config = get_pie_chart_config('Budgeted')
        data = {
            'labels': ['Mandatory', 'Statutory', 'Mortgage', 'Debts, Goals, Retirement', 'Discretionary'],
            'datasets': [
                {
                    'label': 'Budgeted',
                    'data': [mb.mandatory, statutory, mb.mortgage, mb.debts_goals_retirement, mb.discretionary],
                    'backgroundColor': [cjs.get_color('red'), cjs.get_color('orange'), cjs.get_color('yellow'),
                                        cjs.get_color('green'), cjs.get_color('blue')],
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
        context['month'] = 'February'
        context['year'] = 2023
        return context
