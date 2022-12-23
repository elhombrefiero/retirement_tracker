from django import forms

from finances.models import User, Expense, Account, TradingAccount, RetirementAccount


class UserForm(forms.ModelForm):
    """ Add a new user to the database"""

    class Meta:
        model = User
        fields = '__all__'


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
