#!/usr/bin/env python3

from django.http import JsonResponse
from django.views.generic import DetailView

from finances.models import User


class MonthlyBudgetPlotView(DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        print(f"args: {args}")
        print(f"kwargs: {kwargs}")
        return JsonResponse({'test': 1})
