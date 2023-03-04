from django import forms
from django.utils.timezone import now

from finances.models import User, Expense, Account, DebtAccount, TradingAccount, RetirementAccount, MonthlyBudget, Income, CheckingAccount

FORM_BUDGET_GROUP_CHOICES = (
    (None, None),
    ('Mandatory', 'Mandatory'),
    ('Mortgage', 'Mortgage'),
    ('Debts, Goals, Retirement', 'Debts, Goals, Retirement'),
    ('Discretionary', 'Discretionary'),
    ('Statutory', 'Statutory'),
)


class UserForm(forms.ModelForm):
    """ Add a new user to the database"""

    class Meta:
        model = User
        fields = '__all__'


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
        user_checking_accounts = CheckingAccount.objects.filter(user=user)
        user_ret_accounts = RetirementAccount.objects.filter(user=user)
        checking_account_choices = [(None, None)]
        ret_account_choices = [(None, None)]
        for i, acct in enumerate(user_checking_accounts):
            checking_account_choices.append((i, acct))
        for i, acct in enumerate(user_ret_accounts):
            ret_account_choices.append((i, acct))
        self.fields['checking_account'] = forms.ChoiceField(choices=checking_account_choices)
        self.fields['account_401k'] = forms.ChoiceField(choices=ret_account_choices)
        self.fields['account_HSA'] = forms.ChoiceField(choices=ret_account_choices)


class ExpenseForUserForm(forms.ModelForm):
    """ Add expense for a given user"""

    class Meta:
        model = Expense
        exclude = ['user']


class IncomeForUserForm(forms.ModelForm):
    """ Add income for a given user"""

    class Meta:
        model = Income
        exclude = ['user']


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
        user_expenses = Expense.objects.filter(user=user)
        # Fill in choices for category
        category_choices = [(None, None)]
        user_categories = list(user_expenses.values_list('category', flat=True).distinct())
        for cat in user_categories:
            category_choices.append((cat, cat))
        self.fields['category'] = forms.ChoiceField(choices=category_choices)
        # Fill in choices for description
        description_choices = [(None, None)]
        user_description = list(user_expenses.values_list('description', flat=True).distinct())
        for desc in user_description:
            description_choices.append((desc, desc))
        self.fields['description'] = forms.ChoiceField(choices=description_choices)
        # Fill in choices for location
        location_choices = [(None, None)]
        user_where_bought = list(user_expenses.values_list('where_bought', flat=True).distinct())
        for loc in user_where_bought:
            location_choices.append((loc, loc))
        self.fields['where_bought'] = forms.ChoiceField(choices=location_choices)


class MonthlyBudgetForUserForm(forms.ModelForm):
    """ Add a monthly budget for a given user."""
    class Meta:
        model = MonthlyBudget
        exclude = ['user', 'month', 'year']


class MonthlyBudgetForUserMonthYearForm(forms.ModelForm):
    """ Add a monthly budget for a given user, month and year"""

    class Meta:
        model = MonthlyBudget
        exclude = ['user', 'date', 'month', 'year']


class ExpenseByLocForm(forms.ModelForm):
    """ Add or update an expense."""

    class Meta:
        model = Expense
        exclude = ['user', 'account']


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
