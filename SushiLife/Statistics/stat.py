import datetime
import visdom
import numpy as np


def cal_rolling_GR(profit, period):
    rolling_gr = ((profit + 100) / (profit + 100).shift(period))
    rolling_gr = rolling_gr.fillna(rolling_gr[period])

    return rolling_gr


def cal_winning_rate(profit, period):
    rolling_gr = cal_rolling_GR(profit, period)
    winning_rate = np.sum(rolling_gr[period:] > 1) / len(rolling_gr[period:] > 1)

    return winning_rate


def cal_shape_ratio(profit, period):
    rolling_gr = cal_rolling_GR(profit, period)
    SR = np.mean(rolling_gr - 1) / np.std(rolling_gr)

    return SR
