from django import forms


class UserForm(forms.ModelForm):
    """ Add a new user to the database"""
    username = forms.CharField(label='Name')
    date_of_birth = forms.DateField(label='Date of Birth')
    retirement_age = forms.DecimalField(label='Retirement Age')
    percent_withdrawal_at_retirement = forms.DecimalField(label='Percent withdrawal at retirement')
