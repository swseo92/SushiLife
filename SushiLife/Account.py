import numpy as np
import copy
import pyximport
pyximport.install()
from SushiLife import Account_cython


class AssetAccount(dict):
    """
    하나에 자산군에 대한 정보를 저장한다.(ex) 주식, 금, 외환 등)

    Account는 하나의 자산군에 대한 agent의 보유자산 정보를 저장한다.
    dictionary-like object로 주식의 경우 보유 종목의 종목코드를 key 값으로 갖고,
    보유수량, 현재가, 평단가를 key로 갖는 dictionary를 value로 갖는다.

    ex) 삼성전자(A005930)
    AssetAccount["A005930"]["현재가"] : 보유한 삼성전자 주식의 현재가
    AssetAccount["A005930"]["보유수량"] : 보유한 삼성전자 주식의 보유수량

    ex) 보유주식
    AssetAccount.keys() : 보유한 주식의 리스트를 리턴
    """

    def __init__(self, exchange, cost=(0.3, 0.03, 0), 출력=True):
        """

        :param exchange: SushiLife.Exchange, 해당 자산의 거래소
        :param cost: tuple, 거래비용. 세금, 수수료, 슬리피지
        :param 출력: bool, 거래내역 출력 여부
        """
        self._print = 출력
        self.type = "Account"
        self._exchange = exchange

        self._date = None
        self._asset_info = None  # (날짜, 이름, 데이터) 3개의 axis로 구성된 array
        self._total_balance = 0

        # self._balance = dict()
        self._tax, self._fee, self._slippage = cost
        self._TC = 1-(self._tax + self._fee + self._slippage) / 100

    def buy(self, cash, names, 주문가격, 주문수량):
        """

        :param cash: int or float, 보유현금
        :param names: array-like object, str으로 구성된 array-like object, 주식에 경우 종목코드
        :param 주문가격: array-like object,
        :param 주문수량: array-like object,
        :return:
        """
        pass

    def sell(self, cash, names, 주문가격, 주문수량):
        """

        :param cash: int or float, 보유현금
        :param names: array-like object, str으로 구성된 array-like object, 주식에 경우 종목코드
        :param 주문가격: array-like object,
        :param 주문수량: array-like object,
        :return:
        """

        pass

    def _add_assets(self, cash, names, 주문가격, 현재가, 주문수량):
        """

        :param cash: int or float, 보유현금
        :param names: array-like object, str으로 구성된 array-like object, 주식에 경우 종목코드
        :param 주문가격: array-like object,
        :param 현재가: array-like object, 해당 자산들의 현재가
        :param 주문수량: array-like object,
        :return: float, 자산을 매수하고 남은 현금
        """
        for i in range(len(names)):
            name = names[i]
            수량 = 주문수량[i]
            가격 = 주문가격[i]

            if cash < 가격 * 수량:
                # 만일 현금이 부족할 경우 자산의 매수를 그만둔다.
                break

            cash -= 가격 * 수량

            if name not in self.keys():
                # 지갑에 매수한 자산의 상태를 등록한다.
                self[name] = {"현재가": 현재가[i], "평단가": 가격, "보유수량": 수량}
            else:
                self[name]["평단가"] = (수량 * 가격
                                     + self[name]["평단가"]
                                     * self[name]["보유수량"]) / (수량 + self[name]["보유수량"])
                self[name]["보유수량"] += 수량

        return cash

    def _remove_assets(self, cash, names, 주문가격, 주문수량):
        """

        :param cash: int or float, 보유현금
        :param names: array-like object, str으로 구성된 array-like object, 주식에 경우 종목코드
        :param 주문가격: array-like object,
        :param 현재가: array-like object, 해당 자산들의 현재가
        :param 주문수량: array-like object,
        :return: float, 자산을 매도하고 남은 현금
        """

        for i in range(len(names)):
            if self[names[i]]["보유수량"] < 주문수량[i]:
                raise Exception(names[i] + "의 보유수량 %d개 보다 주문수량 %d가 많습니다." % (self[names[i]]["보유수량"], 주문수량[i]))

            cash += 주문가격[i] * 주문수량[i] * self._TC  # 거래비용을 제외한 매도금액을 보유현금에 더한다.
            self[names[i]]["보유수량"] -= 주문수량[i]

        for name in np.unique(names):
            # 자산의 보유 수량이 0일경우 삭제한다.
            if self[name]["보유수량"] == 0:
                del self[name]

        return cash

    def get_total_balance(self):
        return self._total_balance

    def _get_current_price(self):
        """

        :return: 보유한 자산들의 종목코드와 현재가
        """
        names = list(self.keys())
        current_price = self._exchange.get_assets_info(codes=names, fields=["현재가"])

        return names, current_price

    def _apply_current_price(self):
        """
        지갑에 소유한 자산들의 현재가와 총자산을 업데이트한다.
        :return:
        """
        names, current_price = self._get_current_price()

        self._total_balance = 0
        for i in range(len(names)):
            self[names[i]]["현재가"] = current_price[i]
            self._total_balance += self[names[i]]["현재가"] * self[names[i]]["보유수량"]

    def update_from_agent(self, date):
        """
        입력받은 날짜로 지갑에 상태를 업데이트 한다.
        :param date: 업데이트 할 날짜
        :return:
        """
        self._date = date
        self._apply_current_price()


class StockAccount(AssetAccount):
    def __init__(self, exchange, cost=(0.3, 0.03, 0), 출력=True):
        AssetAccount.__init__(self, exchange, cost=cost, 출력=출력)

    def buy(self, cash, names, 주문가격, 주문수량, 주문종류=None, 주문시간=None):
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
        주문수량 = np.array(주문수량, dtype=np.int64)[체결]

        cash = self._add_assets(cash, names, 체결가, 현재가, 주문수량)

        # 거래대금 = np.sum(체결가 * 주문수량)
        return cash

    def sell(self, cash, names, 주문가격, 주문수량, 주문종류=None, 주문시간=None):
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
        주문수량 = np.array(주문수량, dtype=np.int64)[체결]
        cash = self._remove_assets(cash, names, 체결가, 주문수량)

        # 거래대금 = np.sum(체결가 * 주문수량) * self._TC
        return cash

    def _get_current_price(self):
        names = list(self.keys())
        current_price = self._exchange._DataAsset.get_info(self._date, num=1, codes=names,
                                                           fields=["현재가", "대비"]).reshape(-1, 2)

        return names, current_price

    def _apply_current_price(self):
        names, current_price = self._get_current_price()
        self, self._total_balance = Account_cython.apply(self, names, current_price)
