import numpy as np
import pandas as pd


def moving_average(data, window, weight=None):
    if weight is None:
        weight = np.ones_like(data)
    return pd.Series(data * weight).rolling(window=window).sum() / pd.Series(weight).rolling(window=window).sum()


def bollinger_band(price, window=20):
    ma20 = moving_average(price, window)
    std = pd.Series(price - ma20).rolling(window=window).std()

    upper = ma20 + std
    lower = ma20 - std

    return ma20, upper, lower
