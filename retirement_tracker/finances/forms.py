from django import forms
from django.utils.timezone import now
from django.forms import modelformset_factory

from finances.models import User, Withdrawal, Transfer, Deposit, Statutory, DebtAccount, TradingAccount, RetirementAccount, \
    MonthlyBudget, CheckingAccount, BUDGET_GROUP_MANDATORY, BUDGET_GROUP_MORTGAGE, BUDGET_GROUP_DGR, BUDGET_GROUP_DISC

FORM_BUDGET_GROUP_CHOICES = (
    (None, None),
    (BUDGET_GROUP_MANDATORY, BUDGET_GROUP_MANDATORY),
    (BUDGET_GROUP_MORTGAGE, BUDGET_GROUP_MORTGAGE),
    (BUDGET_GROUP_DGR, BUDGET_GROUP_DGR),
    (BUDGET_GROUP_DISC, BUDGET_GROUP_DISC),
)


class UserForm(forms.ModelForm):
    """ Add a new user to the database"""

    class Meta:
        model = User
        fields = '__all__'


class DepositForUserForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = '__all__'


class WithdrawalByLocForm(forms.ModelForm):
    """ Add or update an expense."""

    class Meta:
        model = Withdrawal
        fields = '__all__'


class WithdrawalForUserForm(forms.ModelForm):
    class Meta:
        model = Withdrawal
        fields = '__all__'


class StatutoryForUserForm(forms.ModelForm):
    """ Add a statutory payment for the user."""

    class Meta:
        model = Statutory
        exclude = ['user']


class UserWorkIncomeExpenseForm(forms.Form):
    """ Adds work-related income and expenses for the user."""

    checking_account = forms.ChoiceField(label='Main Account (Checking)')
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
        user_checking_accts = user.return_checking_accts()
        user_checking_accts_names = [acct.name for acct in user_checking_accts]
        user_checking_accounts = CheckingAccount.objects.all().filter(name__in=user_checking_accts_names)
        user_ret_accts = RetirementAccount.objects.filter(user=user)
        user_ret_accounts_names = [acct.name for acct in user_ret_accts]
        user_ret_accounts = RetirementAccount.objects.all().filter(name__in=user_ret_accounts_names)

        checking_account_choices = [(None, None)]
        ret_account_choices = [(None, None)]
        for acct in user_checking_accounts:
            checking_account_choices.append((acct.pk, acct))
        for acct in user_ret_accounts:
            ret_account_choices.append((acct.pk, acct))
        self.fields['checking_account'] = forms.ChoiceField(choices=checking_account_choices)
        self.fields['account_401k'] = forms.ChoiceField(choices=ret_account_choices)
        self.fields['account_HSA'] = forms.ChoiceField(choices=ret_account_choices)


class UserExpenseLookupForm(forms.Form):
    """ Used to lookup expenses for a given user."""
    MONTH_CHOICES = ((None, None), ('January', 'January'), ('February', 'February'), ('March', 'March'),
                     ('April', 'April'), ('May', 'May'), ('June', 'June'),
                     ('July', 'July'), ('August', 'August'), ('September', 'September'),
                     ('October', 'October'), ('November', 'November'), ('December', 'December'))
    budget_choices = (None, None)
    month = forms.CharField(label='Month',
                            widget=forms.Select(choices=MONTH_CHOICES))
    year = forms.ChoiceField()
    budget_group = forms.CharField(label='Budget Group',
                                   widget=forms.Select(choices=FORM_BUDGET_GROUP_CHOICES))
    category = forms.CharField(label='Category')
    description = forms.CharField(label='Description')
    where_bought = forms.CharField(label='Location')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        # Fill in choices for year
        earliest, latest = user.get_earliest_latest_dates()
        earliest = earliest.year
        latest = latest.year
        year_choices = [(None, None)]
        for year in range(earliest, latest + 1):
            year_choices.append((year, year))
        self.fields['year'] = forms.ChoiceField(choices=year_choices)
        user_accounts = user.return_all_accounts()
        user_withdrawals = Withdrawal.objects.filter(account__in=user_accounts)
        # Fill in choices for category
        category_choices = [(None, None)]
        user_categories = list(user_withdrawals.values_list('category', flat=True).distinct())
        for cat in user_categories:
            category_choices.append((cat, cat))
        self.fields['category'] = forms.ChoiceField(choices=category_choices)
        # Fill in choices for description
        description_choices = [(None, None)]
        user_description = list(user_withdrawals.values_list('description', flat=True).distinct())
        for desc in user_description:
            description_choices.append((desc, desc))
        self.fields['description'] = forms.ChoiceField(choices=description_choices)
        # Fill in choices for location
        location_choices = [(None, None)]
        location = list(user_withdrawals.values_list('location', flat=True).distinct())
        for loc in location:
            location_choices.append((loc, loc))
        self.fields['location'] = forms.ChoiceField(choices=location_choices)


class MonthlyBudgetForUserForm(forms.ModelForm):
    """ Add a monthly budget for a given user."""
    date = forms.DateField(label='Date', initial=now, widget=forms.SelectDateWidget)

    class Meta:
        model = MonthlyBudget
        exclude = ['user', 'date', 'month', 'year']


class MonthlyBudgetForUserMonthYearForm(forms.ModelForm):
    """ Add a monthly budget for a given user, month and year"""
    date = forms.DateField(label='Date', initial=now, widget=forms.SelectDateWidget)

    class Meta:
        model = MonthlyBudget
        exclude = ['user', 'date', 'month', 'year']


class AddCheckingAccountForm(forms.ModelForm):

    class Meta:
        model = CheckingAccount
        exclude = ['user']


class AddDebtAccountForm(forms.ModelForm):

    class Meta:
        model = DebtAccount
        exclude = ['user']


class AddTradingAccountForm(forms.ModelForm):

    class Meta:
        model = TradingAccount
        exclude = ['user']


class AddRetirementAccountForm(forms.ModelForm):

    class Meta:
        model = RetirementAccount
        exclude = ['user']


class TransferBetweenAccountsForm(forms.ModelForm):
    date = forms.DateField(label='Transfer Date', initial=now, widget=forms.SelectDateWidget)

    class Meta:
        model = Transfer
        fields = '__all__'


# WithdrawalFormSet = formset_factory()
