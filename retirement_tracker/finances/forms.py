from django import forms

from finances.models import User


class UserForm(forms.ModelForm):
    """ Add a new user to the database"""

    class Meta:
        model = User
        fields = '__all__'

