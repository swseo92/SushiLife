import numpy as np
from SushiLife.Plot.Chart import *

class Exchange:
    def __init__(self):
        self.fields = ["시가", "현재가", "고가", "저가", "거래량(주)", "거래대금(원)", "대비", "시장구분"]

        self._date = None
        self._OCLHVVM = None

        self._DataAsset = None

    def buy(self, list_codes, 주문가격, 주문종류=None, 주문시간=None):
        OCLHVVM = self.get_assets_info(codes=list_codes)
        market_type = OCLHVVM[:, -1]
        OCLHVVM = OCLHVVM[:, :-2]

        주문가격 = cal_price_tick_unit(주문가격, market_type)

        if 주문종류 is None:
            주문종류 = ["limit" for x in np.arange(len(list_codes))]
        else:
            주문종류 = np.array(주문종류)

        if 주문시간 is None:
            주문시간 = ["장중" for x in np.arange(len(list_codes))]
        else:
            주문시간 = np.array(주문시간)

        주문시간 = np.array(주문시간)
        체결가 = np.zeros_like(주문가격) * np.nan  # 체결가가 nan인 경우 미체결, 숫자인 경우 체결가격

        # 체결조건 (시간순서로)
        cond1 = (OCLHVVM[:, 4] == 0) | (np.isnan(OCLHVVM[:, 4]))  # 미체결, 거래량이 0이거나 상장되지 않음
        cond2 = (주문시간 == "장전") & (OCLHVVM[:, 0] <= 주문가격)  # 체결, 장 시작과 동시에 체결
        cond3 = OCLHVVM[:, 2] <= 주문가격  # 체결, 장중 체결
        cond4 = OCLHVVM[:, 3] <= 주문가격  # 체결, 장중 체결
        cond5 = (주문종류 == "조건부지정가")  # 체결, 장 마감시 체결

        체결성공1 = ~cond1 & cond2  # 장시작과 동시에 시가에 체결
        체결성공2 = ~cond1 & ~cond2 & cond3  # 고가 < 주문가격, 고가에 장중 체결
        체결성공3 = ~cond1 & ~cond2 & ~cond3 & cond4  # 저가 < 주문가격, 주문가격에 장중 체결
        체결성공4 = ~cond1 & ~cond2 & ~cond3 & ~cond4 & cond5  # 장마감 동시호가에 체결

        체결가[체결성공1] = OCLHVVM[체결성공1, 0]  # 시가 체결
        체결가[체결성공2] = OCLHVVM[체결성공2, 2]  # 고가 체결
        체결가[체결성공3] = 주문가격[체결성공3]  # 시가 체결
        체결가[체결성공4] = OCLHVVM[체결성공4, 1]  # 종가 체결

        현재가 = OCLHVVM[:, 1]
        return 체결가, 현재가

    def sell(self, list_codes, 주문가격, 주문종류=None, 주문시간=None):
        OCLHVVM = self.get_assets_info(codes=list_codes)
        market_type = OCLHVVM[:, -1]
        OCLHVVM = OCLHVVM[:, :-2]

        주문가격 = cal_price_tick_unit(주문가격, market_type)

        if 주문종류 is None:
            주문종류 = ["limit" for x in np.arange(len(list_codes))]
        else:
            주문종류 = np.array(주문종류)

        if 주문시간 is None:
            주문시간 = ["장중" for x in np.arange(len(list_codes))]
        else:
            주문시간 = np.array(주문시간)

        주문시간 = np.array(주문시간)

        체결가 = np.zeros_like(주문가격) * np.nan  # 체결가가 nan인 경우 미체결, 숫자인 경우 체결가격

        # 체결조건 (시간순서로)
        cond1 = (OCLHVVM[:, 4] == 0) | (np.isnan(OCLHVVM[:, 1]))  # 미체결, 거래량이 0이거나 상장되지 않음
        cond2 = (주문시간 == "장전") & (OCLHVVM[:, 0] >= 주문가격)  # 체결, 장 시작과 동시에 체결
        cond3 = OCLHVVM[:, 3] >= 주문가격  # 체결, 장중 체결 : 저가 > 판매가
        cond4 = OCLHVVM[:, 2] >= 주문가격  # 체결, 장중 체결 : 고가 > 판매가
        cond5 = (주문종류 == "조건부지정가")  # 체결, 장 마감시 체결

        체결성공1 = ~cond1 & cond2  # 장시작과 동시에 시가에 체결
        체결성공2 = ~cond1 & ~cond2 & cond3  # 저가 > 주문가격, 저가에 장중 체결
        체결성공3 = ~cond1 & ~cond2 & ~cond3 & cond4  # 고가 > 주문가격, 주문가격에 장중 체결
        체결성공4 = ~cond1 & ~cond2 & ~cond3 & ~cond4 & cond5  # 장마감 동시호가에 체결

        체결가[체결성공1] = OCLHVVM[체결성공1, 0]  # 시가 체결
        체결가[체결성공2] = OCLHVVM[체결성공2, 3]  # 고가 체결
        체결가[체결성공3] = 주문가격[체결성공3]  # 시가 체결
        체결가[체결성공4] = OCLHVVM[체결성공4, 1]  # 종가 체결

        return 체결가

    def set_DataAsset(self, data_asset):
        self._DataAsset = data_asset

    def get_assets_info(self, codes=None, fields=None):
        array = self._OCLHVVM[:]

        if codes is not None:
            idx_codes = [self._DataAsset.code2idx[code] for code in codes]
            array = array[idx_codes, :]
        if fields is not None:
            idx_fields = [self._DataAsset.field2idx[field] for field in fields]
            array = array[:, idx_fields]

        return array

    def update_date(self, date):
        self._date = date
        self._get_OCLHVV()

    def init(self, date):
        self.update_date(date)

    def _get_OCLHVV(self):
        self._OCLHVVM = self._DataAsset.get_info(self._date, num=1, fields=self.fields).reshape(-1, len(self.fields))

    def chart(self, 종목코드, num=250):
        data = self._DataAsset.get_info(self._date, num=num, fields=["현재가", "시가", "고가", "저가", "거래대금(원)"],
                                   codes=[종목코드])[:, 0, :]

        idx_dates = self._DataAsset.date2idx[self._date]
        list_date = self._DataAsset.dates[idx_dates-num+1:idx_dates+1]
        chart = Chart()
        chart.make_chart(data, list_date)

        return chart


def cal_price_tick_unit(price, market_type):
    price = np.array(price)
    market_type = np.array(market_type).reshape(-1)
    tick_unit = np.zeros_like(price)

    kosdaq = (market_type == 1)  # type : 0: 코스피, 1: 코스닥
    tick_unit[kosdaq] = 100
    tick_unit[kosdaq & (price < 50000)] = 50
    tick_unit[kosdaq & (price < 10000)] = 10
    tick_unit[kosdaq & (price < 5000)] = 5
    tick_unit[kosdaq & (price < 1000)] = 1

    tick_unit[~kosdaq] = 1000
    tick_unit[~kosdaq & (price < 500000)] = 500
    tick_unit[~kosdaq & (price < 100000)] = 100
    tick_unit[~kosdaq & (price < 50000)] = 50
    tick_unit[~kosdaq & (price < 10000)] = 10
    tick_unit[~kosdaq & (price < 5000)] = 5
    tick_unit[~kosdaq & (price < 1000)] = 1

    price = np.floor(price / tick_unit) * tick_unit
    return price
