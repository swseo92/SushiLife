import numpy as np
import pandas as pd
import h5py

from SushiLife import *

f = h5py.File("templete.hdf5", "r")
array_stock, axis_stock = load_data(f, "stock", chunks=5, in_memory=True)
array_value, axis_value = load_data(f, "value", chunks=5, in_memory=True)

data_stock = DataAsset(array_stock, axis_stock, chunks=5)
data_value = DataAsset(array_value, axis_value, chunks=5)

updater = Updater(pd.Timestamp(2002, 6, 15), data_stock.dates)

# 거래소 생성
exchange_stock = Exchange()
exchange_stock.set_DataAsset(data_stock)

# 주식 계좌 생성
stock_account = StockAccount(exchange_stock, 출력=False)

# 거래 에이전트 생성 및 주식 계좌 등록
agent = Agent(1e8, 출력=False)
agent.set_account("stock", stock_account)

# 날짜가 변할시 업데이트 요청
updater.set_instance4update(data_stock)
updater.set_instance4update(data_value)

updater.set_instance4update(exchange_stock)

updater.set_instance4update(agent)

updater.reset()
columns = ["상장시가총액(원)", "지배주주순이익(원)(직전4분기)", "지배주주지분(원)",
           "현금흐름(원)(직전4분기)", "매출액(원)(직전4분기)"]

while updater._date != updater._list_date[-1]:
    print(updater._date)
    fin_stat = data_value.get_info(updater._date, num=2,
                                   fields=columns)

    fin_stat = fin_stat[-2]
    상장시가총액 = fin_stat[:, 0]

    # 상장종목 고려
    상장종목 = ~np.isnan(상장시가총액)

    종목코드 = np.array(data_value.codes)[상장종목]
    상장시가총액 = 상장시가총액[상장종목]
    values = 상장시가총액.reshape(-1, 1) / fin_stat[상장종목, 1:]

    # 소형주
    시가총액순위 = 상장시가총액.argsort().argsort()
    시가총액조건 = 시가총액순위 < len(시가총액순위) * 0.3  # 상장종목 & 소형주

    values = values[시가총액조건, :]
    종목코드 = 종목코드[시가총액조건]

    # 양수
    cond_positive = (values > 0).all(axis=1)
    values = values[cond_positive, :]
    종목코드 = 종목코드[cond_positive]

    rank_each = values.argsort(axis=0).argsort(axis=0)
    sum_rank = np.sum(rank_each, axis=1)
    rank = sum_rank.argsort(axis=0).argsort(axis=0)

    cond_rank = rank < 50
    매수종목 = np.sort(종목코드[cond_rank])

    # 매도
    매도종목 = list(agent.accounts["stock"].keys())
    현재가 = data_stock.get_info(updater._date, codes=매도종목, fields=["현재가"]).reshape(-1)
    매도수량 = [agent.accounts["stock"][종목코드]["보유수량"] for 종목코드 in 매도종목]
    agent.sell("stock", 매도종목, 현재가, 매도수량)

    # 매수
    현재가 = data_stock.get_info(updater._date, codes=매수종목, fields=["현재가"]).reshape(-1).astype("f")
    거래가능 = ~np.isnan(현재가)
    매수수량 = (agent.cash / 50 / 현재가[거래가능]).astype("i")
    agent.buy("stock", 매수종목[거래가능], 현재가[거래가능], 매수수량)

    updater.update()