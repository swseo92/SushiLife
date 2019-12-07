import numpy as np
from SushiLife import *
import DataAsset

f = h5py.File("../../../../data/stock_info.hdf5", "r")
array_stock, axis_stock = load_data(f, "stock", chunks=5)
array_value, axis_value = load_data(f, "value", chunks=5)

data_stock = DataAsset.DataAsset(array_stock.compute(), axis_stock)
data_value = DataAsset.DataAsset(array_value.compute(), axis_value)

updater = Updater(pd.Timestamp(2002, 6, 15), data_stock.dates)

# 거래소 생성
exchange_stock = Exchange()
exchange_stock.set_DataAsset(data_stock)

# 주식 계좌 생성
stock_account = StockAccount(exchange_stock, 출력=False)

# 거래 에이전트 생성 및 주식 계좌 등록
agent = Agent(1e8, 출력=True)
agent.set_account("stock", stock_account)

# 날짜가 변할시 업데이트 요청
updater.set_data(data_stock)
updater.set_data(data_value)

updater.set_exchange(exchange_stock)

updater.set_agent(agent)

updater.initialization()

# 백테스트

columns = ["상장시가총액(원)", "지배주주순이익(원)(직전4분기)", "지배주주지분(원)",
           "현금흐름(원)(직전4분기)", "매출액(원)(직전4분기)"]

while updater._date != updater._list_date[-1]:
    fin_stat = data_value.get_info(updater._date, num=1, fields=columns)[0]

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
    매수종목 = 종목코드[cond_rank]
    updater.update()

    # 매도
    매도종목 = agent.accounts["stock"].keys()
    현재가 = data_stock.get_info(updater._date, codes=매도종목, fields=["현재가"]).reshape(-1)

    i = 0
    for 종목코드 in 매도종목:
        매도수량 = agent.accounts["stock"][종목코드]["보유수량"]
        agent.sell("stock", 종목코드, 현재가[i], 매도수량)
        i += 1

    # 매수
    현재가 = data_stock.get_info(updater._date, codes=매수종목, fields=["현재가"]).reshape(-1)
    i = 0
    for 종목코드 in 매수종목:
        if not np.isnan(현재가[i]):
            매수수량 = int(agent.total_balance / 50 / 현재가[i])
            agent.buy("stock", 종목코드, 현재가[i], 매수수량, 주문종류="조건부지정가")
        i += 1

    for i in range(20):
        if updater._date == updater._list_date[-1]:
            break
        updater.update()
