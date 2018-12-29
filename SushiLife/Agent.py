import numpy as np
import pandas as pd
from SushiLife.Statistics.stat import *
import visdom
import plotly
import plotly.graph_objs as go

class Agent:
    def __init__(self, initial_cash, 레버리지=1, 출력=True):
        self._출력 = 출력
        self._date = None

        self._initial_cash = initial_cash
        self.cash = initial_cash
        self.total_balance = initial_cash

        self._레버리지 = 레버리지

        self.accounts = dict()  # 여러 자산군에 대한 계좌
        self._basket = dict()  # 해당일에 구매리스트를 받기위한 바구니

        self.report = {"수익률(%)": [], "누적수익률(%)": [], "총자산(원)": [], "현금자산": [], "현물자산": [],
                       "CAGR(%)": [], "일평균수익률(%)": [], "MDD": [], "최대수익률(%)": [], "날짜": []}

    def set_account(self, name, account):
        self.accounts[name] = account  # 계좌등록
        # 해당 자산에 대해서 바스켓 생성
        self._basket[name] = {"구매이름": [], "구매가격": [], "구매수량": [], "구매종류": [], "구매시간": [],
                              "판매이름": [], "판매가격": [], "판매수량": [], "판매종류": [], "판매시간": []}

    def buy(self, name_account, name, 주문가격, 주문수량, 주문종류="limit", 주문시간="장중"):
        if 주문수량 < 0:
            raise Exception

        주문수량 = int(주문수량)

        self._basket[name_account]["구매이름"].append(name)
        self._basket[name_account]["구매가격"].append(주문가격)
        self._basket[name_account]["구매수량"].append(주문수량)
        self._basket[name_account]["구매종류"].append(주문종류)
        self._basket[name_account]["구매시간"].append(주문시간)

    def sell(self, name_account, name, 주문가격, 주문수량, 주문종류="limit", 주문시간="장중"):
        if 주문수량 < 0:
            raise Exception

        주문수량 = int(주문수량)

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
        cash_available = (self._레버리지 - 1) * self.total_balance + self.cash

        if cash_required > cash_available:
            idx = np.sum(np.cumsum(주문가격 * 주문수량) < cash_available) - 1
            if idx == -1:
                return False

            names = names[:idx]
            주문가격 = 주문가격[:idx]
            주문수량 = 주문수량[:idx]

            if 주문종류 is not None:
                주문종류 = 주문종류[:idx]
            if 주문시간 is not None:
                주문시간 = 주문시간[:idx]

        self.cash = self.accounts[name_account].buy(self.cash, names, 주문가격, 주문수량, 주문종류=주문종류, 주문시간=주문시간)
        # self.cash -= cash_consumed

        return True

    def _sell_list(self, name_account, names, 주문가격, 주문수량, **kwds):
        if len(names) == 0:
            return False
        주문가격 = np.array(주문가격)
        주문수량 = np.array(주문수량)

        self.cash = self.accounts[name_account].sell(self.cash, names, 주문가격, 주문수량, **kwds)
        # self.cash += cash_earned


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
        self.report = {"수익률(%)": [0.0], "누적수익률(%)": [0.0], "총자산(원)": [self._initial_cash], "현금자산": [self._initial_cash], "현물자산": [0],
                       "CAGR(%)": [0.0], "일평균수익률(%)": [0.0], "MDD": [0.0], "DD": [0.0], "최대수익률(%)": [0], "날짜": [self._date]}

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

        레포트_당일 = {"수익률(%)": 당일수익률, "누적수익률(%)": 누적수익률, "총자산(원)": 총자산, "현금자산": self.cash, "현물자산": self.total_balance,
                  "CAGR(%)": CAGR, "일평균수익률(%)": 일평균수익률, "MDD": MDD, "DD": DD, "최대수익률(%)": 최대수익률, "날짜": self._date}

        for field in self.report.keys():
            self.report[field].append(레포트_당일[field])

        if self._출력:
            print("\n\n",
                  "당일수익률(%) : ", 당일수익률, "\n",
                  "누적수익률(%) : ", 누적수익률, "\n",
                  "CAGR(%)", CAGR, "\n",
                  "MDD : ", MDD, "\n",
                  "DD : ", DD, "\n",
                  "총자산(원) : ", 총자산, "\n",
                  "--------------------------------------------------\n",
                  "장시작 : ", self._date, )

    def stat(self, Strategy_name, height=900, width=1400):
        레포트 = pd.DataFrame(self.report)

        rolling_cagr = cal_rolling_GR(레포트["누적수익률(%)"], 250)
        rolling_cmgr = cal_rolling_GR(레포트["누적수익률(%)"], 20)

        annual_winning_rate = cal_winning_rate(레포트["누적수익률(%)"], 250)
        monthly_winning_rate = cal_winning_rate(레포트["누적수익률(%)"], 20)
        weekly_winning_rate = cal_winning_rate(레포트["누적수익률(%)"], 5)

        annual_SR = cal_shape_ratio(레포트["누적수익률(%)"], 250)
        monthly_SR = cal_shape_ratio(레포트["누적수익률(%)"], 20)
        weekly_SR = cal_shape_ratio(레포트["누적수익률(%)"], 5)

        visdom.Visdom().text(
            "--- " + Strategy_name + " ---" + '<br>'
            + '<br>'
            + '누적수익률: %.2f' % 레포트["누적수익률(%)"].iat[-1] + '% <br>'
            + '일평균수익률: %.2f' % 레포트["일평균수익률(%)"].iat[-1] + '% <br>'
            + 'CAGR: %.2f' % 레포트["CAGR(%)"].iat[-1] + '% <br>'
            + 'MDD: %.2f' % 레포트["MDD"].iat[-1] + '% <br>'
            + '<br>'
            + '- Annual Winning Rate: %.2f <br>' % annual_winning_rate
            + '- Monthly Winning Rate: %.2f <br>' % monthly_winning_rate
            + '- Weekly Winning Rate: %.2f <br>' % weekly_winning_rate
            + "<br>"
            + '- Annual Sharpe Ratio: %.2f <br>' % annual_SR
            + '- Monthly Sharpe Ratio: %.2f <br>' % monthly_SR
            + '- Weekly Sharpe Ratio: %.2f <br>' % weekly_SR
        )

        trace1 = dict(x=레포트["날짜"], y=(100 + 레포트["누적수익률(%)"]), xaxis='x', yaxis='y', showlegend=False)
        trace2 = dict(x=레포트["날짜"], y=레포트["DD"], xaxis='x', yaxis='y2', showlegend=False)

        trace3 = dict(x=레포트["날짜"], y=rolling_cagr, xaxis='x2', yaxis='y3', showlegend=False)
        trace4 = dict(x=레포트["날짜"], y=rolling_cmgr, xaxis='x2', yaxis='y4', showlegend=False)

        data = [trace1, trace2, trace3, trace4]
        layout = go.Layout(
            title=Strategy_name, height=height, width=width,
            yaxis=dict(type='log', domain=[0.3, 1], title="누적수익률(%)"),
            yaxis2=dict(domain=[0, 0.3], title="Drawdown(%)"),
            xaxis=dict(domain=[0, 0.6], anchor="y2"),

            xaxis2=dict(domain=[0.75, 1], anchor="y4"),
            yaxis3=dict(domain=[0.5, 1], anchor="x2", title="Rolling CAGR(%)"),
            yaxis4=dict(domain=[0, 0.5], anchor="x2", title="Rolling CMGR(%)")
        )
        fig = go.Figure(data=data, layout=layout)
        visdom.Visdom().plotlyplot(fig)
        print("http://localhost:8097/#")
        return 레포트
