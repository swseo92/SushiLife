import numpy as np
import copy
import pyximport
pyximport.install()
from SushiLife import Account_cython


class AssetAccount(dict):
    """
    하나에 자산군에 대한 정보를 저장한다.(ex) 주식, 금, 외환 등)
    """

    def __init__(self, exchange, cost=(0.3, 0.03, 0), 출력=True):
        self._print = 출력
        self.type = "Account"
        self._exchange = exchange

        self._date = None
        self._asset_info = None  # (날짜, 이름, 데이터) 3개의 axis로 구성된 array
        self._total_balance = 0

        # self._balance = dict()
        self._tax, self._fee, self._slippage = cost
        self._TC = 1-(self._tax + self._fee + self._slippage) / 100

    def buy(self, names, 주문가격, 주문수량):
        pass

    def sell(self, names, 주문가격, 주문수량):
        pass

    def _add_assets(self, names, 주문가격, 현재가, 주문수량):
        for i in range(len(names)):
            name = names[i]
            수량 = 주문수량[i]
            가격 = 주문가격[i]

            if name not in self.keys():
                self[name] = {"현재가": 현재가[i], "평단가": 가격, "보유수량": 수량}
            else:
                self[name]["평단가"] = (수량 * 가격
                                     + self[name]["평단가"]
                                     * self[name]["보유수량"]) / (수량 + self[name]["보유수량"])
                self[name]["보유수량"] += 수량

    def _remove_assets(self, names, 주문가격, 주문수량):
        for i in range(len(names)):
            self[names[i]]["보유수량"] -= 주문수량[i]

            if self[names[i]]["보유수량"] == 0:
                del self[names[i]]

    def get_total_balance(self):
        return self._total_balance

    def _get_current_price(self):
        names = list(self.keys())
        current_price = self._exchange.get_assets_info(codes=names, fields=["현재가"])

        return names, current_price

    def _apply_current_price(self):
        names, current_price = self._get_current_price()

        self._total_balance = 0
        for i in range(len(names)):
            self[names[i]]["현재가"] = current_price[i]
            self._total_balance += self[names[i]]["현재가"] * self[names[i]]["보유수량"]

    def update_from_agent(self, date):
        self._date = date
        self._apply_current_price()

    def reset_from_agent(self, date):
        self._date = date
        for key in list(self.keys()):
            del self[key]


class StockAccount(AssetAccount):
    def __init__(self, exchange, cost=(0.3, 0.03, 0), 출력=True):
        AssetAccount.__init__(self, exchange, cost=cost, 출력=출력)

    def buy(self, names, 주문가격, 주문수량, 주문종류=None, 주문시간=None):
        체결가, 현재가 = self._exchange.buy(names, 주문가격, 주문종류=주문종류, 주문시간=주문시간)

        체결 = ~np.isnan(체결가)
        if self._print:
            for i in range(len(체결)):
                if 체결[i]:
                    print("매수 체결 : ", names[i], "체결가 : ", 체결가[i], "주문수량 : ", 주문수량[i])
                else:
                    print("매수 실패 : ", names[i], "주문가", 주문가격[i], "주문수량 : ", 주문수량[i])

        names = np.array(names)[체결]
        체결가, 현재가 = 체결가[체결], 현재가[체결]
        주문수량 = np.array(주문수량)[체결]

        self._add_assets(names[주문수량 > 0], 체결가[주문수량 > 0], 현재가[주문수량 > 0], 주문수량[주문수량 > 0])

        거래대금 = np.sum(체결가 * 주문수량)
        return 거래대금

    def sell(self, names, 주문가격, 주문수량, 주문종류=None, 주문시간=None):
        체결가 = self._exchange.sell(names, 주문가격, 주문종류=주문종류, 주문시간=주문시간)

        체결 = ~np.isnan(체결가)
        if self._print == True:
            for i in range(len(체결)):
                if 체결[i]:
                    수익률 = (체결가[i] * (100 - self._tax - self._fee - self._slippage) / 100 - self[names[i]]["평단가"]) / \
                          self[names[i]]["평단가"] * 100
                    수익금 = (체결가[i] * (100 - self._tax - self._fee - self._slippage) / 100 - self[names[i]]["평단가"]) * \
                          self[names[i]]["보유수량"]

                    print("매도 체결 : ", names[i], "체결가 : ", 체결가[i], "주문수량 : ", 주문수량[i],
                          " / 수익률(%) : ", 수익률, ", 수익금(원) : ", 수익금)
                else:
                    print("매도 실패 : ", names[i], "주문가 : ", 주문가격[i], "주문수량 : ", 주문수량[i])

        names = np.array(names)[체결]
        체결가 = 체결가[체결]
        주문수량 = np.array(주문수량)[체결]
        self._remove_assets(names[주문수량 > 0], 체결가[주문수량 > 0], 주문수량[주문수량 > 0])

        거래대금 = np.sum((체결가 * 주문수량).astype("int64")) * self._TC
        return 거래대금

    def _get_current_price(self):
        names = list(self.keys())
        current_price = self._exchange._DataAsset.get_info(self._date, num=1, codes=names,
                                                           fields=["현재가", "대비"]).reshape(-1, 2)

        return names, current_price

    def _apply_current_price(self):
        names, current_price = self._get_current_price()
        self, self._total_balance = Account_cython.apply(self, names, current_price)
