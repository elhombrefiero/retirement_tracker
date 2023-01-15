from django import forms

from finances.models import User, Expense, Account, TradingAccount, RetirementAccount, MonthlyBudget


class UserForm(forms.ModelForm):
    """ Add a new user to the database"""

    class Meta:
        model = User
        fields = '__all__'


class ExpenseForUserForm(forms.ModelForm):
    """ Add expense for a given user"""

    class Meta:
        model = Expense
        exclude = ['user']


class MonthlyBudgetForUserForm(forms.ModelForm):
    """ Add a monthly budget for a given user"""

    class Meta:
        model = MonthlyBudget
        exclude = ['user']


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
