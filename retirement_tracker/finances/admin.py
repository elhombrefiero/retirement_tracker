from django.contrib import admin
from finances.models import Account, Expense, User

# Register your models here.
admin.site.register(Account)
admin.site.register(Expense)
admin.site.register(User)
