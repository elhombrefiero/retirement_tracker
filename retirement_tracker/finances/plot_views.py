#!/usr/bin/env python3

from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView
from django.db.models.functions import Trunc
from django.utils.timezone import now

from finances.models import User, MonthlyBudget, CheckingAccount, RetirementAccount, DebtAccount, \
    dt_to_milliseconds_after_epoch, Statutory, Account
from finances.utils import chartjs_utils as cjs

from datetime import datetime
from dateutil.relativedelta import relativedelta


# TODO: Add plot views that take advantage of the value vs time functions. Account balance vs time. User net worth over time. Debt balance vs time

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
            'plugins': {
                'title': {
                    'display': True,
                    'text': f'{name}'
                }
            },
        }
    }
    )
    return config


def get_line_chart_config(name, type='scatter'):
    """ Returns the configuration for a line chart"""
    config = {'type': f'{type}',
              'options': {
                  'showLine': True,
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
                      'x': {'type': 'time',
                            'display': True,
                            'title': {
                               'display': True,
                               'text': 'Date'
                            },
                           },

                      'y':
                          {'display': True,
                            'title': {
                                'display': True,
                                'text': 'Amount'
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
        'plugins': {
            'title': {
                'display': True,
                'text': f'{name}'
            },
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

        mand_exp, mort_exp, dgr_exp, disc_exp, stat_exp = self.user.return_tot_expenses_by_budget_month_year(self.month,
                                                                                                             self.year)

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
            income_day_dt = datetime(income_day.year, income_day.month, income_day.day)
            income_day_ts = dt_to_milliseconds_after_epoch(income_day_dt)
            labels.append(income_day_ts)
            xy_data.append(
                {'x': income_day_ts, 'y': float(cumulative_income[income_day])})

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
            expensedate_dt = datetime(expensedate.year, expensedate.month,expensedate.day)
            expensedate_ts = dt_to_milliseconds_after_epoch(expensedate_dt)
            labels.append(expensedate_ts)
            xy_data.append(
                {'x': expensedate_ts, 'y': float(cumulative_expenses[expensedate])})

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
            date_dt = datetime(date_key.year, date_key.month, date_key.day)
            date_ts = dt_to_milliseconds_after_epoch(date_dt)
            labels.append(date_ts)
            xy_data.append(
                {'x': date_ts, 'y': float(cumulative_total[date_key]['cumulative'])})

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


class CheckingAccountBalanceByTime(DetailView):
    """ Uses the balance vs time function to return
        -line plot of
            actual balance vs time (of six months prior to last entry up to today) and,
            projected value five years into the future."""
    model = CheckingAccount

    def dispatch(self, request, *args, **kwargs):
        accountpk = kwargs['pk']
        self.account = CheckingAccount.objects.get(pk=accountpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        user = self.account.user

        config = get_line_chart_config(f'{self.account.name} Account Balance vs Time')
        return_dict = dict()
        return_dict['config'] = config

        xy_actual = []
        labels_actual = []
        xy_projected = []
        labels = []
        datasets = []

        today = now()

        one_year_prior = today + relativedelta(years=-1)
        five_years_from_today = today + relativedelta(years=+5)

        current_date = one_year_prior
        while current_date <= today:
            current_date_ts = dt_to_milliseconds_after_epoch(current_date)
            month = current_date.strftime('%B')
            year = current_date.strftime('%Y')
            current_balance = self.account.return_balance_up_to_month_year(month, year)
            xy_actual.append({'x': current_date_ts, 'y': current_balance})
            labels_actual.append(current_date_ts)
            current_date += relativedelta(months=+1)

        datasets.append({
            'label': 'Account Balance',
            'backgroundColor': cjs.get_color('black', 0.5),
            'borderColor': cjs.get_color('black'),
            'fill': False,
            'data': xy_actual
            }
        )

        f = self.account.return_value_vs_time_function()

        current_date = today

        while current_date <= five_years_from_today:
            current_date_ts = dt_to_milliseconds_after_epoch(current_date)
            current_balance = float(f(current_date_ts))
            xy_projected.append({'x': current_date_ts, 'y': current_balance})
            labels_actual.append(current_date_ts)

            current_date = current_date + relativedelta(years=+1)

        datasets.append({
            'label': 'Projected Account Balance',
            'backgroundColor': cjs.get_color('green', 0.5),
            'borderColor': cjs.get_color('green'),
            'fill': False,
            'data': xy_projected
        }
        )

        data = {
            'labels': labels,
            'datasets': datasets
        }

        return_dict['data'] = data

        return JsonResponse(return_dict)


class RetirementAccountBalanceByTime(DetailView):
    """ Uses the balance vs time function to return
        -line plot of
            actual balance vs time (of six months prior to last entry up to today) and,
            projected value five years into the future."""
    model = RetirementAccount

    def dispatch(self, request, *args, **kwargs):
        accountpk = kwargs['pk']
        self.account = RetirementAccount.objects.get(pk=accountpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        config = get_line_chart_config(f'{self.account.name} Account Balance vs Time')
        return_dict = dict()
        return_dict['config'] = config

        xy_actual = []
        labels_actual = []
        xy_projected = []
        labels = []
        datasets = []

        today = now()

        one_year_prior = today + relativedelta(years=-1)
        five_years_from_today = today + relativedelta(years=+5)

        current_date = one_year_prior
        while current_date <= today:
            current_date_ts = dt_to_milliseconds_after_epoch(current_date)
            month = current_date.strftime('%B')
            year = current_date.strftime('%Y')
            current_balance = self.account.return_balance_up_to_month_year(month, year)
            xy_actual.append({'x': current_date_ts, 'y': current_balance})
            labels_actual.append(current_date_ts)
            current_date += relativedelta(months=+1)

        datasets.append({
            'label': 'Account Balance',
            'backgroundColor': cjs.get_color('black', 0.5),
            'borderColor': cjs.get_color('black'),
            'fill': False,
            'data': xy_actual
            }
        )

        f = self.account.return_value_vs_time_function(num_of_years=1, num_of_months=0,
                                                       kind='cubic', fill_value='extrapolate', months_into_future=12)

        current_date = today

        while current_date <= five_years_from_today:
            current_date_ts = dt_to_milliseconds_after_epoch(current_date)
            current_balance = float(f(current_date_ts))
            xy_projected.append({'x': current_date_ts, 'y': current_balance})
            labels_actual.append(current_date_ts)

            current_date = current_date + relativedelta(years=+1)

        datasets.append({
            'label': 'Projected Account Balance',
            'backgroundColor': cjs.get_color('green', 0.5),
            'borderColor': cjs.get_color('green'),
            'fill': False,
            'data': xy_projected
        }
        )

        data = {
            'labels': labels,
            'datasets': datasets
        }

        return_dict['data'] = data

        return JsonResponse(return_dict)


class DebtAccountBalanceByTime(DetailView):
    """ Uses the balance vs time function to return
        -line plot of
            actual balance vs time (of six months prior to last entry up to today) and,
            projected value five years into the future."""
    model = DebtAccount

    def dispatch(self, request, *args, **kwargs):
        accountpk = kwargs['pk']
        self.account = DebtAccount.objects.get(pk=accountpk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):

        config = get_line_chart_config(f'{self.account.name} Account Balance vs Time')
        return_dict = dict()
        return_dict['config'] = config

        xy_actual = []
        labels_actual = []
        xy_projected = []
        labels = []
        datasets = []

        today = now()

        one_year_prior = today + relativedelta(years=-1)
        five_years_from_today = today + relativedelta(years=+5)

        current_date = one_year_prior
        while current_date <= today:
            current_date_ts = dt_to_milliseconds_after_epoch(current_date)
            month = current_date.strftime('%B')
            year = current_date.strftime('%Y')
            current_balance = self.account.return_balance_up_to_month_year(month, year)
            xy_actual.append({'x': current_date_ts, 'y': current_balance})
            labels_actual.append(current_date_ts)
            current_date += relativedelta(months=+1)

        datasets.append({
            'label': 'Account Balance',
            'backgroundColor': cjs.get_color('black', 0.5),
            'borderColor': cjs.get_color('black'),
            'fill': False,
            'data': xy_actual
            }
        )

        f = self.account.return_value_vs_time_function()

        current_date = today

        while current_date <= five_years_from_today:
            current_date_ts = dt_to_milliseconds_after_epoch(current_date)
            current_balance = float(f(current_date_ts))
            xy_projected.append({'x': current_date_ts, 'y': current_balance})
            labels_actual.append(current_date_ts)

            current_date = current_date + relativedelta(years=+1)

        datasets.append({
            'label': 'Projected Account Balance',
            'backgroundColor': cjs.get_color('green', 0.5),
            'borderColor': cjs.get_color('green'),
            'fill': False,
            'data': xy_projected
        }
        )

        data = {
            'labels': labels,
            'datasets': datasets
        }

        return_dict['data'] = data

        return JsonResponse(return_dict)


class UserReportDataCustom(DetailView):
    # TODO: Add some return information based on the inputs from the get function.
    model = User


class MonthlyBudgetCustomPlotView(DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']

        config = get_pie_chart_config(f'Monthly Budgets from {start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}')

        stat_tot = 0.0
        mand_tot = 0.0
        mort_tot = 0.0
        dgr_tot = 0.0
        disc_tot = 0.0

        mbs = MonthlyBudget.objects.filter(user=user, date__gte=start_date, date__lte=end_date)
        stats = Statutory.objects.filter(user=user, date__gte=start_date, date__lte=end_date)

        for stat in stats:
            stat_tot += stat.amount

        for mb in mbs:
            mand_tot += mb.mandatory
            mort_tot += mb.mortgage
            dgr_tot += mb.debts_goals_retirement
            disc_tot += mb.discretionary

        data = {
            'labels': ['Mandatory', 'Statutory', 'Mortgage', 'Debts, Goals, Retirement', 'Discretionary'],
            'datasets': [
                {
                    'label': 'Budgeted',
                    'data': [mand_tot, stat_tot, mort_tot, dgr_tot, disc_tot],
                    'backgroundColor': [cjs.get_color('red'), cjs.get_color('orange'), cjs.get_color('yellow'),
                                        cjs.get_color('green'), cjs.get_color('blue')],
                }
            ]
        }

        return_dict = dict()
        return_dict['config'] = config
        return_dict['data'] = data

        return JsonResponse(return_dict)


class ActualExpenseByBudgetGroupCustomDates(DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']

        mand_act, mort_act, dgr_act, disc_act, stat_act = user.return_tot_expenses_by_budget_startdt_to_enddt(start_date, end_date)

        config = get_pie_chart_config(f'Actual Expenses by Monthly Budget from {start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}')

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


class ExpenseSpentAndBudgetPlotViewCustomDates(DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        config = get_bar_chart_config('Budgeted vs. Spent')
        data = dict()
        labels = ['Mandatory', 'Mortgage', 'Statutory', 'Debts, Goals, Retirement', 'Discretionary']
        data['labels'] = labels

        stat_mb, mand_mb, mort_mb, dgr_mb, disc_mb = user.return_monthly_budgets(start_date, end_date)

        mand_exp, mort_exp, dgr_exp, disc_exp, stat_exp = user.return_tot_expenses_by_budget_startdt_to_enddt(start_date, end_date)

        datasets = list()
        budgeted_info = {
            'label': 'Budgeted',
            'data': [mand_mb, mort_mb, stat_mb, dgr_mb, disc_mb],
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


class ExpenseByCategoryPlotViewCustomDates(DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        config = get_bar_chart_config('Top Expenses by Category')
        data = dict()
        top5_cat = user.return_top_category_dt_to_dt(start_date, end_date, 5)

        labels = list()
        data_sum = list()
        for topcat in top5_cat:
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


class ExpenseByDescriptionPlotViewCustomDates(DetailView):

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        config = get_bar_chart_config('Top Expenses by Description')

        data = dict()
        top5_desc = user.return_top_description_dt_to_dt(start_date, end_date, num_of_entries=5)

        labels = list()
        data_sum = list()
        for topdesc in top5_desc:
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


class ExpenseByLocationPlotViewCustomDates(DetailView):

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        config = get_bar_chart_config('Top Expenses by Location')

        top5_loc = user.return_top_location_dt_to_dt(start_date, end_date, num_of_entries=5)
        labels = list()
        data = dict()
        data_sum = list()
        for toploc in top5_loc:
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


class IncomeCumulativeMonthYearPlotViewCustomDates(DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        config = get_line_chart_config(f'Cumulative Incomes from {start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}')
        cumulative_income = user.return_cumulative_incomes(start_date, end_date)

        return_dict = dict()
        return_dict['config'] = config

        xy_data = []
        labels = []
        for income_day in cumulative_income:
            income_day_dt = datetime(income_day.year, income_day.month, income_day.day)
            income_day_ts = dt_to_milliseconds_after_epoch(income_day_dt)
            labels.append(income_day_ts)
            xy_data.append(
                {'x': income_day_ts, 'y': float(cumulative_income[income_day])})

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


class ExpenseCumulativeMonthYearPlotViewCustomDate(DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']

        config = get_line_chart_config(f'Cumulative Expenses from {start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}')
        cumulative_expenses = user.return_cumulative_expenses(start_date, end_date)

        return_dict = dict()
        return_dict['config'] = config

        xy_data = []
        labels = []
        for expensedate in cumulative_expenses:
            expensedate_dt = datetime(expensedate.year, expensedate.month, expensedate.day)
            expensedate_ts = dt_to_milliseconds_after_epoch(expensedate_dt)
            labels.append(expensedate_ts)
            xy_data.append(
                {'x': expensedate_ts, 'y': float(cumulative_expenses[expensedate])})

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


class TotalCumulativeMonthYearPlotViewCustomDates(DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        user = User.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        config = get_line_chart_config(f'Cumulative Total from {start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}')
        cumulative_total = user.return_cumulative_total(start_date, end_date)

        return_dict = dict()
        return_dict['config'] = config

        xy_data = []
        labels = []
        for date_key in sorted(cumulative_total.keys()):
            date_dt = datetime(date_key.year, date_key.month, date_key.day)
            date_ts = dt_to_milliseconds_after_epoch(date_dt)
            labels.append(date_ts)
            xy_data.append(
                {'x': date_ts, 'y': float(cumulative_total[date_key]['cumulative'])})

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

class AccountCumulativeCustomDates(DetailView):
    model = Account

    def get(self, request, *args, **kwargs):
        account = Account.objects.get(pk=kwargs['pk'])
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        config = get_line_chart_config(f'{account.name.title()} Data from {start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}')
        cumulative_total, projected_data, trend_data = account.return_cumulative_total(start_date, end_date)

        return_dict = dict()
        return_dict['config'] = config

        xy_data = []
        labels = []
        for date_key in sorted(cumulative_total.keys()):
            date_dt = datetime(date_key.year, date_key.month, date_key.day)
            date_ts = dt_to_milliseconds_after_epoch(date_dt)
            labels.append(date_ts)
            if 'cumulative' in cumulative_total[date_key]:
                xy_data.append(
                    {'x': date_ts, 'y': float(cumulative_total[date_key]['cumulative'])})

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
        if projected_data:
            proj_xy_data = []
            labels = []
            for date_key in sorted(projected_data.keys()):
                date_dt = datetime(date_key.year, date_key.month, date_key.day)
                date_ts = dt_to_milliseconds_after_epoch(date_dt)
                labels.append(date_ts)
                proj_xy_data.append(
                    {'x': date_ts, 'y': float(projected_data[date_key])})
            data['datasets'].append({
                'label': 'Projected',
                'backgroundColor': cjs.get_color('green', 0.5),
                'borderColor': cjs.get_color('green'),
                'fill': False,
                'data': proj_xy_data
            })

        if trend_data:
            trend_xy_data = []
            labels = []
            for date_key in sorted(trend_data.keys()):
                date_dt = datetime(date_key.year, date_key.month, date_key.day)
                date_ts = dt_to_milliseconds_after_epoch(date_dt)
                labels.append(date_ts)
                trend_xy_data.append(
                    {'x': date_ts, 'y': float(projected_data[date_key])})
            data['datasets'].append({
                'label': 'Trendline',
                'backgroundColor': cjs.get_color('yellow', 0.25),
                'borderColor': cjs.get_color('yellow'),
                'fill': False,
                'data': trend_xy_data
            })

        return_dict['data'] = data

        return JsonResponse(return_dict)

class DebugView(TemplateView):
    template_name = 'finances/debug.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accountpk'] = 1
        context['start_date'] = '2023-06-01'
        context['end_date'] = '2024-09-01'

        return context
