from django.contrib import admin
from finances.models import CheckingAccount, RetirementAccount, DebtAccount, User, \
                            MonthlyBudget, Deposit, Withdrawal, Transfer

# Register your models here.
admin.site.register(User)
admin.site.register(CheckingAccount)
admin.site.register(RetirementAccount)
admin.site.register(DebtAccount)
admin.site.register(MonthlyBudget)
admin.site.register(Deposit)
admin.site.register(Withdrawal)
admin.site.register(Transfer)
