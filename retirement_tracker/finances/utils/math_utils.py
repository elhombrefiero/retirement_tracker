#!/usr/bin/env python3


def linear_trend(xi, x1, x2, y1, y2):
    """ Returns the y_i value at x_i based on the trendline from (x1,y1) to (x2,y2)"""

    m = (y2-y1)/(x2-x1)

    b = y2 - (y2-y1)/x2

    return m*xi + b