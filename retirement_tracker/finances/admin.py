from django.contrib import admin
from finances.models import Account, CheckingAccount, RetirementAccount, DebtAccount, Expense, User, Income, \
                            MonthlyBudget, Deposit, Withdrawal, Transfer

# Register your models here.
admin.site.register(User)
admin.site.register(Account)
admin.site.register(CheckingAccount)
admin.site.register(RetirementAccount)
admin.site.register(DebtAccount)
admin.site.register(Expense)
admin.site.register(Income)
admin.site.register(MonthlyBudget)
admin.site.register(Deposit)
admin.site.register(Withdrawal)
admin.site.register(Transfer)
