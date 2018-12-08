import numpy as np
import pandas as pd
import h5py

from SushiLife import *

f = h5py.File("../data/stock_info.hdf5", "r")
array_stock, axis_stock = load_data(f, "stock", chunks=5, in_memory=False)
array_value, axis_value = load_data(f, "value", chunks=5, in_memory=False)

data_stock = DataAsset(array_stock, axis_stock, chunks=5)
data_value = DataAsset(array_value, axis_value, chunks=5)

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
    fin_stat = data_value.get_info(updater._date, num=2,
                                   fields=columns)

    df = pd.DataFrame(fin_stat[-2], index=data_value.codes, columns=columns)
    df = df[~np.isnan(df["상장시가총액(원)"])]  # 상장종목 고려
    df = df.sort_values(by=['상장시가총액(원)']).iloc[:int(len(df.index) * 0.3)]  # 소형주

    # 종목선정
    df["PER"] = df["상장시가총액(원)"] / df["지배주주순이익(원)(직전4분기)"]
    df["PBR"] = df["상장시가총액(원)"] / df["지배주주지분(원)"]
    df["PCR"] = df["상장시가총액(원)"] / df["현금흐름(원)(직전4분기)"]
    df["PSR"] = df["상장시가총액(원)"] / df["매출액(원)(직전4분기)"]

    df = df[df["PER"] > 0]
    df = df[df["PBR"] > 0]
    df = df[df["PCR"] > 0]
    df = df[df["PSR"] > 0]

    df["Rank"] = (df["PER"].rank() + df["PBR"].rank() + df["PCR"].rank() + df["PSR"].rank()).rank()

    df = df[df["Rank"] < 51]

    # 매도
    매도종목 = agent.accounts["stock"].keys()
    매수종목 = df.index
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
        매수수량 = (agent.cash / 50 / 현재가[i])
        agent.buy("stock", 종목코드, 현재가[i], 매수수량)
        i += 1

    for i in range(20):
        if updater._date == updater._list_date[-1]:
            break
        updater.update()