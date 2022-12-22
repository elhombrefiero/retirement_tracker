from django import forms

from finances.models import User, Expense


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
