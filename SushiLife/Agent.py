import numpy as np


class Agent:
    def __init__(self, initial_cash, 출력=True):
        self._출력 = 출력
        self._date = None

        self._initial_cash = initial_cash
        self.cash = initial_cash
        self.total_balance = initial_cash

        self.accounts = dict()  # 여러 자산군에 대한 계좌
        self._basket = dict()  # 해당일에 구매리스트를 받기위한 바구니

        self.report = {"수익률(%)": [], "누적수익률(%)": [], "총자산(원)": [],
                       "CAGR(%)": [], "일평균수익률(%)": [], "MDD": [], "최대수익률(%)": [], "날짜": []}

    def set_account(self, name, account):
        self.accounts[name] = account  # 계좌등록
        # 해당 자산에 대해서 바스켓 생성
        self._basket[name] = {"구매이름": [], "구매가격": [], "구매수량": [], "구매종류": [], "구매시간": [],
                              "판매이름": [], "판매가격": [], "판매수량": [], "판매종류": [], "판매시간": []}

    def buy(self, name_account, name, 주문가격, 주문수량, 주문종류="limit", 주문시간="장중"):
        self._basket[name_account]["구매이름"].append(name)
        self._basket[name_account]["구매가격"].append(주문가격)
        self._basket[name_account]["구매수량"].append(주문수량)
        self._basket[name_account]["구매종류"].append(주문종류)
        self._basket[name_account]["구매시간"].append(주문시간)

    def sell(self, name_account, name, 주문가격, 주문수량, 주문종류="limit", 주문시간="장중"):
        self._basket[name_account]["판매이름"].append(name)
        self._basket[name_account]["판매가격"].append(주문가격)
        self._basket[name_account]["판매수량"].append(주문수량)
        self._basket[name_account]["판매종류"].append(주문종류)
        self._basket[name_account]["판매시간"].append(주문시간)

    def _reset_basket(self, name):
        self._basket[name] = {"구매이름": [], "구매가격": [], "구매수량": [], "구매종류": [], "구매시간": [],
                              "판매이름": [], "판매가격": [], "판매수량": [], "판매종류": [], "판매시간": []}

    def _shopping_basket(self):
        for name_account in self.accounts.keys():
            self._sell_list(name_account, self._basket[name_account]["판매이름"],
                      self._basket[name_account]["판매가격"], self._basket[name_account]["판매수량"],
                      주문종류=self._basket[name_account]["판매종류"], 주문시간=self._basket[name_account]["판매시간"])

            self._buy_list(name_account, self._basket[name_account]["구매이름"],
                     self._basket[name_account]["구매가격"], self._basket[name_account]["구매수량"],
                     주문종류=self._basket[name_account]["구매종류"], 주문시간=self._basket[name_account]["구매시간"])

            self._reset_basket(name_account)

    def _buy_list(self, name_account, names, 주문가격, 주문수량, 주문종류=None, 주문시간=None):
        if len(names) == 0:
            return False
        주문가격 = np.array(주문가격)
        주문수량 = np.array(주문수량)

        cash_required = np.sum(주문가격 * 주문수량)

        if cash_required > self.cash:
            idx = np.sum(np.cumsum(주문가격 * 주문수량) < self.cash) - 1
            if idx == -1:
                return False

            names = names[:idx]
            주문가격 = 주문가격[:idx]
            주문수량 = 주문수량[:idx]

            if 주문종류 is not None:
                주문종류 = 주문종류[:idx]
            if 주문시간 is not None:
                주문시간 = 주문시간[:idx]

        cash_consumed = self.accounts[name_account].buy(names, 주문가격, 주문수량, 주문종류=주문종류, 주문시간=주문시간)
        self.cash -= cash_consumed

        return True

    def _sell_list(self, name_account, names, 주문가격, 주문수량, **kwds):
        if len(names) == 0:
            return False
        주문가격 = np.array(주문가격)
        주문수량 = np.array(주문수량)

        cash_earned = self.accounts[name_account].sell(names, 주문가격, 주문수량, **kwds)
        self.cash += cash_earned


    def update_date(self, date):
        self._shopping_basket()
        self.total_balance = 0

        for key in self.accounts.keys():
            self.accounts[key].update_from_agent(date)
            self.total_balance += self.accounts[key].get_total_balance()

        self.total_balance += self.cash
        self._update_report()

        self._date = date

    def init(self, date):
        self._date = date
        self.report = {"수익률(%)": [0.0], "누적수익률(%)": [0.0], "총자산(원)": [self._initial_cash],
                       "CAGR(%)": [0.0], "일평균수익률(%)": [0.0], "MDD": [0.0], "최대수익률(%)": [0], "날짜": [self._date]}

    def _update_report(self):
        당일수익률 = (self.total_balance - self.report["총자산(원)"][-1]) / self.report["총자산(원)"][-1] * 100
        누적수익률 = (self.total_balance / self._initial_cash - 1) * 100
        총자산 = self.total_balance
        경과 = (self._date - self.report["날짜"][0]).days + 1

        일평균수익률 = ((누적수익률 / 100 + 1) ** (1 / 경과) - 1) * 100
        CAGR = ((일평균수익률 / 100 + 1) ** 365 - 1) * 100

        최대수익률 = max(누적수익률, np.max(self.report["누적수익률(%)"]))
        DD = (누적수익률 - 최대수익률) / (최대수익률 + 100) * 100
        MDD = min(DD, np.min(self.report["MDD"]))

        레포트_당일 = {"수익률(%)": 당일수익률, "누적수익률(%)": 누적수익률, "총자산(원)": 총자산,
                  "CAGR(%)": CAGR, "일평균수익률(%)": 일평균수익률, "MDD": MDD, "최대수익률(%)": 최대수익률, "날짜": self._date}

        for field in self.report.keys():
            self.report[field].append(레포트_당일[field])

        if self._출력:
            print("장마감 : ", self._date, "\n\n",
                  "당일수익률(%) : ", 당일수익률, "\n",
                  "누적수익률(%) : ", 누적수익률, "\n",
                  "CAGR(%)", CAGR, "\n",
                  "MDD : ", MDD, "\n",
                  "총자산(원) : ", 총자산, "\n",
                  "--------------------------------------------------\n")
