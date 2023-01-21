from django import forms
from django.utils.timezone import now

from finances.models import User, Expense, Account, TradingAccount, RetirementAccount, MonthlyBudget


class UserForm(forms.ModelForm):
    """ Add a new user to the database"""

    class Meta:
        model = User
        fields = '__all__'


class UserWorkIncomeExpenseForm(forms.Form):
    """ Adds work-related income and expenses for the user."""

    account = forms.ChoiceField(label='Main Account')
    account_401k = forms.ChoiceField(label='Account for 401k')
    account_HSA = forms.ChoiceField(label='Account for HSA')
    date = forms.DateField(label='Date of paycheck', initial=now, widget=forms.SelectDateWidget)
    gross_income = forms.FloatField(label='Gross income')
    fed_income_tax = forms.DecimalField(label='Federal Income Tax')
    social_security_tax = forms.DecimalField(label='Social Security Tax')
    medicare = forms.DecimalField(label='Medicare Tax')
    state_income_tax = forms.DecimalField(label='State Income Tax')
    dental = forms.DecimalField(label='Dental')
    medical = forms.DecimalField(label='Medical')
    vision = forms.DecimalField(label='Vision')
    retirement_401k = forms.DecimalField(label="Retirement - 401k")
    retirement_HSA = forms.DecimalField(label="Retirement - HSA")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        user_accounts = Account.objects.filter(user=user)
        account_choices = [(None, None)]
        for i, acct in enumerate(user_accounts):
            account_choices.append((i, acct))
        self.fields['account'] = forms.ChoiceField(choices=account_choices)
        self.fields['account_401k'] = forms.ChoiceField(choices=account_choices)
        self.fields['account_HSA'] = forms.ChoiceField(choices=account_choices)


class ExpenseForUserForm(forms.ModelForm):
    """ Add expense for a given user"""

    class Meta:
        model = Expense
        exclude = ['user']


class MonthlyBudgetForUserForm(forms.ModelForm):
    """ Add a monthly budget for a given user"""

    class Meta:
        model = MonthlyBudget
        exclude = ['user', 'Date', 'month', 'year']


class ExpenseByLocForm(forms.ModelForm):
    """ Add or update an expense."""

    class Meta:
        model = Expense
        exclude = ['user', 'account']


class AddAccountForm(forms.ModelForm):

    class Meta:
        model = Account
        exclude = ['user']


class AddTradingAccountForm(forms.ModelForm):

    class Meta:
        model = TradingAccount
        exclude = ['user']


class AddRetirementAccountForm(forms.ModelForm):

    class Meta:
        model = RetirementAccount
        exclude = ['user']
