from django.contrib import admin
from finances.models import Account, CheckingAccount, RetirementAccount, DebtAccount, Expense, User, Income, MonthlyBudget

# Register your models here.
admin.site.register(User)
admin.site.register(Account)
admin.site.register(CheckingAccount)
admin.site.register(RetirementAccount)
admin.site.register(DebtAccount)
admin.site.register(Expense)
admin.site.register(Income)
admin.site.register(MonthlyBudget)
