import numpy as np
import copy
import pyximport
# Ensure numpy headers are available for Cython compilation
pyximport.install(reload_support=True, setup_args={"include_dirs": np.get_include()})
from SushiLife import Account_cython_opt3 as Account_cython_module


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

    def __init__(self, exchange, cost=(0.3, 0.03, 0), 출력=True, 매매기록=False):
        """

        :param exchange: SushiLife.Exchange, 해당 자산의 거래소
        :param cost: tuple, 거래비용. 세금, 수수료, 슬리피지
        :param 출력: bool, 거래내역 출력 여부
        """
        self._print = 출력
        self._매매기록 = 매매기록
        self.매매내역 = {'종목코드': list(), '수익금': list(), '수익률': list(), '자산대비수익률': list()}
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

            # if cash < 가격 * 수량:
            #     # 만일 현금이 부족할 경우 자산의 매수를 그만둔다.
            #     break

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
        names_list = list(self.keys()) # Keep as list of strings for Cython
        if not names_list:
            self._total_balance = 0 # No assets, so balance from assets is 0
            return

        # _get_current_price now returns (names_list, current_price_updates_for_holdings_array)
        # where current_price_updates_for_holdings_array is (N, 2) with new price and '대비'
        # For AssetAccount, _get_current_price might only return (N,1) if it doesn't handle '대비'
        # This part needs to be consistent with what StockAccount._get_current_price returns.
        # Assuming this is StockAccount being called, so current_price_updates_for_holdings has 2 columns.
        # If this method is ever called on a plain AssetAccount, _get_current_price would need adjustment or this logic would.

        # For the generic AssetAccount, we might not have '대비', so let's fetch only '현재가'
        # and create a dummy '대비' if needed, or adjust Cython.
        # However, the Cython code expects '대비'. The original non-stock AssetAccount._apply_current_price
        # did not use Cython. This optimization is targeted at StockAccount.
        # The current structure calls this method for StockAccount.

        # This method will be effectively overridden by StockAccount's version for this optimization.
        # So, the original logic for plain AssetAccount can be kept here, as it won't be hit by StockAccount instances.
        original_names, original_current_price_flat = super()._get_current_price() # Call AssetAccount's _get_current_price

        self._total_balance = 0
        for i in range(len(original_names)):
            self[original_names[i]]["현재가"] = original_current_price_flat[i] # Assuming it's flat
            self._total_balance += self[original_names[i]]["현재가"] * self[original_names[i]]["보유수량"]


    def update_from_agent(self, date):
        """
        입력받은 날짜로 지갑에 상태를 업데이트 한다.
        :param date: 업데이트 할 날짜
        :return:
        """
        self._date = date
        self._apply_current_price()


class StockAccount(AssetAccount):
    def __init__(self, exchange, cost=(0.3, 0.03, 0), 출력=True, 매매기록=False):
        AssetAccount.__init__(self, exchange, cost=cost, 출력=출력, 매매기록=매매기록)

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
        if self._print == True or self._매매기록:
            for i in range(len(체결)):
                if 체결[i]:
                    수익률 = (체결가[i] * (100 - self._tax - self._fee - self._slippage) / 100 - self[names[i]]["평단가"]) / \
                          self[names[i]]["평단가"] * 100
                    수익금 = (체결가[i] * (100 - self._tax - self._fee - self._slippage) / 100 - self[names[i]]["평단가"]) * \
                          self[names[i]]["보유수량"]

                    if self._print:
                        print("매도 체결 : ", names[i], "체결가 : ", 체결가[i], "주문수량 : ", 주문수량[i],
                              " / 수익률(%) : ", 수익률, ", 수익금(원) : ", 수익금)

                    if self._매매기록:
                        self.매매내역['종목코드'].append(names[i])
                        self.매매내역['수익률'].append(수익률)
                        self.매매내역['수익금'].append(수익금)
                        self.매매내역['자산대비수익률'].append(수익금 / self._total_balance)
                else:
                    if self._print:
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
        names_list = list(self.keys()) # Keep as list of strings for Cython
        if not names_list:
            self._total_balance = 0 # No assets, so balance from assets is 0
            return

        # _get_current_price now returns (names_list, current_price_updates_for_holdings_array)
        # where current_price_updates_for_holdings_array is (N, 2) with new price and '대비'
        _, current_price_updates_for_holdings = self._get_current_price()

        평단가_arr = np.array([self[name]["평단가"] for name in names_list], dtype=np.double)
        보유수량_arr = np.array([self[name]["보유수량"] for name in names_list], dtype=np.double)
        현재가_arr_prev_day = np.array([self[name]["현재가"] for name in names_list], dtype=np.double)

        # Call the modified Cython function
        평단가_arr_updated, 보유수량_arr_updated, total_balance_from_cython, delisted_indices = \
            Account_cython_module.apply(평단가_arr, 보유수량_arr, 현재가_arr_prev_day,
                                      names_list, current_price_updates_for_holdings)

        self._total_balance = total_balance_from_cython # This is based on prev day's prices * quantities

        # Update account dictionary based on returned arrays
        # Handle delisted items first by creating a list of names to delete
        names_to_delete = []
        for delisted_idx in sorted(delisted_indices, reverse=True): # Sort to avoid index issues when deleting
            name_to_del = names_list[delisted_idx]
            names_to_delete.append(name_to_del)
            if self._print:
                print(f"\x1b[31m\"{name_to_del}\"\x1b[0m  상장폐지 !!! ###################################")

        for name_to_del in names_to_delete:
            if name_to_del in self: # Check if not already deleted by other logic
                 del self[name_to_del]

        # Update existing holdings
        for i, name in enumerate(names_list):
            if i not in delisted_indices: # Only update if not delisted
                if 보유수량_arr_updated[i] == 0: # If shares became zero due to split logic
                    if name in self: # Check if not already deleted
                       del self[name]
                       if self._print:
                           print(f"{name} 보유수량 0 되어 삭제.") # Shares became 0, deleted
                else:
                    if name in self: # Ensure it wasn't delisted
                        self[name]["평단가"] = 평단가_arr_updated[i]
                        self[name]["보유수량"] = 보유수량_arr_updated[i]
                        # current_price_updates_for_holdings[i, 0] is today's actual market price
                        self[name]["현재가"] = current_price_updates_for_holdings[i, 0]
