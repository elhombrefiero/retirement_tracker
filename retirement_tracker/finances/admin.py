from django.contrib import admin
from finances.models import Account, Expense, User, Income, MonthlyBudget

# Register your models here.
admin.site.register(User)
admin.site.register(Account)
admin.site.register(Expense)
admin.site.register(Income)
admin.site.register(MonthlyBudget)
