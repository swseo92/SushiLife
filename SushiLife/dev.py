import numpy as np
import pandas as pd
import h5py

from Account import *
from Agent import *
from DataAsset import *
from Exchnage import *
from Updater import *

f = h5py.File("./data/stock_info.hdf5", "r")
array_stock, axis_stock = load_data(f, "stock", chunks=5, in_memory=False)
array_vol, axis_vol = load_data(f, "변동성", chunks=5, in_memory=False)

data_stock = DataAsset(array_stock, axis_stock)
data_vol = DataAsset(array_vol, axis_vol)

updater = Updater(pd.Timestamp(2010, 1, 1), data_stock.dates)

# 거래소 생성
exchange_stock = Exchange()
exchange_stock.set_DataAsset(data_stock)

# 주식 계좌 생성
stock_account = StockAccount(exchange_stock, 출력=False)

# 거래 에이전트 생성 및 주식 계좌 등록
agent = Agent(1e10, 출력=True)
agent.set_account("stock", stock_account)

# 날짜가 변할시 업데이트 요청
updater.set_data(data_stock)
updater.set_data(data_vol)

updater.set_agent(agent)
updater.set_exchange(exchange_stock)

updater.initialization()

t = True
while updater._date != updater._list_date[-1]:
    # 가격조건
    if t:
        가격데이터 = data_stock.get_info(updater._date, num=300, fields=["현재가", "거래대금(원)"])
        t = False
    else:
        가격데이터_오늘 = data_stock.get_info(updater._date, num=1, fields=["현재가", "거래대금(원)"]).reshape(1, -1, 2)
        가격데이터 = np.concatenate((가격데이터[1:], 가격데이터_오늘), axis=0)

    거래가능 = (가격데이터[:, :, 1] > 0).all(axis=0)

    가격데이터2 = 가격데이터[:, 거래가능, :]
    종목코드 = np.array(data_stock.codes)[거래가능]

    유동성 = np.sum(가격데이터2[-20:, :, 1], axis=0)
    idx = np.argsort(유동성)[int(0.2 * len(유동성)):]  # 유동성 하위 20% 제거
    종목코드 = 종목코드[idx]

    # 변동성조건
    변동성데이터 = data_vol.get_info(updater._date, num=1, codes=종목코드)
    vol_rank = 변동성데이터.argsort(axis=0).argsort(axis=0)
    vol_rank = np.sum(vol_rank, axis=1).argsort(axis=0).argsort(axis=0)

    idx = np.argsort(vol_rank)[:int(0.2 * len(유동성))]  # 상위 20% 선정

    종목코드 = 종목코드[idx]
    배팅금액 = agent.total_balance / len(종목코드)

    리밸런스 = pd.DataFrame({"배팅금액": 배팅금액}, index=종목코드)

    # 다음날로 이동
    updater.update()

    # 종목선정
    보유주식 = agent.accounts["stock"]
    전일종가 = data_stock.get_info(updater._date, num=2, codes=보유주식.keys(), fields=["현재가"])[-2].reshape(-1)

    i = -1
    for 종목코드 in list(보유주식.keys()):
        i += 1
        주문가격 = 전일종가[i]
        보유수량 = 보유주식[종목코드]["보유수량"]

        if 종목코드 not in 리밸런스.index:
            최종수량 = 0
        else:
            최종수량 = int(리밸런스.at[종목코드, "배팅금액"] / 주문가격)

        if 보유수량 > 최종수량:
            주문량 = 보유수량 - 최종수량
            agent.sell("stock", 종목코드, 주문가격 * 1.1, max(1, min(보유수량, int(주문량 / 10))), 주문종류="조건부지정가", 주문시간="장전")
        else:
            주문량 = 최종수량 - 보유수량

            agent.sell("stock", 종목코드, 주문가격 * 1.1, int(보유수량), 주문시간="장전")
            agent.buy("stock", 종목코드, 주문가격 * 0.99, min(주문량, int(최종수량 / 10)), 주문시간="장전")

    전일종가 = data_stock.get_info(updater._date, num=2, codes=리밸런스.index, fields=["현재가"])[-2].reshape(-1)

    i = -1
    for 종목코드 in 리밸런스.index:
        i += 1
        주문가격 = 전일종가[i]

        if 종목코드 in 보유주식.keys():
            continue

        if 종목코드[1] == "9":
            continue

        주문량 = int(리밸런스.at[종목코드, "배팅금액"] / 주문가격)
        agent.buy("stock", 종목코드, 주문가격 * 0.99, max(int(주문량 / 10), 1), 주문시간="장전")