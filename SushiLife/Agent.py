import numpy as np


class Agent:
    def __init__(self, initial_cash, 출력=True):
        self._출력 = 출력
        self._date = None

        self._initial_cash = initial_cash
        self.cash = initial_cash
        self.total_balance = initial_cash

        self.accounts = dict()  # 여러 자산군에 대한 계좌

        self.report = {"수익률(%)": [], "누적수익률(%)": [], "총자산(원)": [],
                       "CAGR(%)": [], "일평균수익률(%)": [], "MDD": [], "최대수익률(%)": [], "날짜": []}

    def set_account(self, name, account):
        self.accounts[name] = account

    def buy(self, name_account, names, 주문가격, 주문수량, **kwds):
        주문가격 = np.array(주문가격)
        주문수량 = np.array(주문수량)

        cash_required = np.sum(주문가격 * 주문수량)
        if cash_required > self.cash:
            idx = np.sum(np.cumsum(주문가격 * 주문수량) < cash_required) - 1
            if idx == -1:
                return False

            names = names[:idx]
            주문가격 = 주문가격[:idx]
            주문수량 = 주문수량[:idx]

        cash_consumed = self.accounts[name_account].buy(names, 주문가격, 주문수량, **kwds)
        self.cash -= cash_consumed

        return True

    def sell(self, name_account, names, 주문가격, 주문수량, **kwds):
        주문가격 = np.array(주문가격)
        주문수량 = np.array(주문수량)

        cash_earned = self.accounts[name_account].sell(names, 주문가격, 주문수량, **kwds)
        self.cash += cash_earned

    def update_date(self, date):
        self._date = date

        self.total_balance = 0
        for key in self.accounts.keys():
            self.accounts[key].update_from_agent(date)
            self.total_balance += self.accounts[key].get_total_balance()

        self.total_balance += self.cash
        self._update_report()

    def reset(self, date):
        self._date = date

        for key in self.accounts.keys():
            self.accounts[key].reset_from_agent(date)

        self.cash = self._initial_cash * 1
        self.total_balance = self._initial_cash * 1

        self.report = {"수익률(%)": [], "누적수익률(%)": [], "총자산(원)": [],
                       "CAGR(%)": [], "일평균수익률(%)": [], "MDD": [], "최대수익률(%)": [], "날짜": []}
        self._update_report()

    def _update_report(self):
        if not self.report["날짜"]:
            self.report = {"수익률(%)": [0.0], "누적수익률(%)": [0.0], "총자산(원)": [self._initial_cash],
                           "CAGR(%)": [0.0], "일평균수익률(%)": [0.0], "MDD": [0.0], "최대수익률(%)": [0], "날짜": [self._date]}
        else:
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