#!/usr/bin/env python3

from .plot_urls import urlpatterns as urlpatterns_plot
from .money_urls import urlpatterns as urlpatterns_reg
urlpatterns = urlpatterns_reg + urlpatterns_plot