
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta


def return_relative_delta(end_date: datetime, latest_date_dt: datetime):
    """ Takes a start and end date and returns the subdivision to best represent the plotting"""

    td = end_date - latest_date_dt
    if td < timedelta(days=30):
        relative_diff = relativedelta(days=+1)
    elif td > timedelta(weeks=52 * 5):
        relative_diff = relativedelta(years=+1)
    else:
        relative_diff = relativedelta(months=+1)

    return relative_diff
