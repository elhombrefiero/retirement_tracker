#!/usr/bin/env python3

MONTHS = [
    'January', 'February', 'March', 'April',
    'May', 'June', 'July', 'August',
    'September', 'October', 'November', 'December'
]

COLOR_PRIMARY = '#79aec8'
CHART_COLORS = {
  'red': 'rgb(255, 99, 132)',
  'orange': 'rgb(255, 159, 64)',
  'yellow': 'rgb(255, 205, 86)',
  'green': 'rgb(75, 192, 192)',
  'blue': 'rgb(54, 162, 235)',
  'purple': 'rgb(153, 102, 255)',
  'grey': 'rgb(201, 203, 207)'
}

CHART_COLOR_NUMS = {
    'red': [255, 99, 132],
    'orange': [255, 159, 64],
    'yellow': [25, 205, 86],
    'green': [75, 192, 192],
    'blue': [54, 162, 235],
    'purple': [153, 102, 255],
    'grey': [201, 203, 207]
}


def get_color(color_name, alpha=None):
    chart_numbers = CHART_COLOR_NUMS[color_name]
    if alpha:
        return f'rgba({chart_numbers[0]}, {chart_numbers[1]}, {chart_numbers[2]}, {alpha})'
    else:
        return f'rgb({chart_numbers[0]}, {chart_numbers[1]}, {chart_numbers[2]})'

