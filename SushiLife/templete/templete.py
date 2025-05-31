import numpy as np
import pandas as pd
import h5py
# cProfile, pstats, io imports removed

from SushiLife import *

# Adjusted HDF5 path assuming execution from repo root
# Ensure this path is correct for the final execution environment.
# If stock_info.hdf5 is expected in SushiLife/data (created by generate_dummy_data.py):
f = h5py.File("SushiLife/data/stock_info.hdf5", "r")
# If it's expected at the repo root/data:
# f = h5py.File("data/stock_info.hdf5", "r")
# Or if the original script's relative path from SushiLife/templete was intended:
# f = h5py.File("../../../../data/stock_info.hdf5", "r") # This seems less likely for general use

array_stock, axis_stock = load_data(f, "stock", chunks=5)
array_value, axis_value = load_data(f, "value", chunks=5)

data_stock = DataAsset(array_stock, axis_stock, chunks=60, in_memory=False) # chunks=60
data_value = DataAsset(array_value, axis_value, chunks=60, in_memory=False) # chunks=60

updater = Updater(pd.Timestamp(2003, 1, 1), data_stock.dates)

# 거래소 생성
exchange_stock = Exchange()
exchange_stock.set_DataAsset(data_stock)

# 주식 계좌 생성
stock_account = StockAccount(exchange_stock, 출력=False) # Profiling showed original StockAccount, not opt3

# 거래 에이전트 생성 및 주식 계좌 등록
agent = Agent(1e8, 출력=True)
agent.set_account("stock", stock_account)

# 날짜가 변할시 업데이트 요청
updater.set_data(data_stock)
updater.set_data(data_value)
updater.set_exchange(exchange_stock)
updater.set_agent(agent)

# Profiler init calls removed
updater.initialization()

# 백테스트
columns = ["상장시가총액(원)", "지배주주순이익(원)(직전4분기)", "지배주주지분(원)",
           "현금흐름(원)(직전4분기)", "매출액(원)(직전4분기)"]

#  백테스트 시작
# Profiler loop calls removed
while updater._date != updater._list_date[-1]:
    fin_stat = data_value.get_info(updater._date, num=1,
                                   fields=columns)

    # NumPy-based optimization from profiled_templete_opt1/opt2
    market_cap_col_name = "상장시가총액(원)"
    market_cap_col_idx = -1
    for i, col_name in enumerate(columns):
        if col_name == market_cap_col_name:
            market_cap_col_idx = i
            break

    if market_cap_col_idx == -1:
        raise ValueError(f"Column '{market_cap_col_name}' not found in 'columns'")

    if fin_stat.size == 0:
        df = pd.DataFrame(columns=columns)
    else:
        valid_indices_filter = ~np.isnan(fin_stat[:, market_cap_col_idx])
        filtered_stat = fin_stat[valid_indices_filter]

        current_codes_for_fin_stat = data_value.codes
        filtered_codes = current_codes_for_fin_stat[valid_indices_filter]

        if filtered_stat.shape[0] == 0:
            df = pd.DataFrame(columns=columns)
        else:
            sorted_indices = np.argsort(filtered_stat[:, market_cap_col_idx])

            num_to_take = int(filtered_stat.shape[0] * 0.3)
            if num_to_take == 0 and filtered_stat.shape[0] > 0 :
                num_to_take = 1

            smallest_cap_indices = sorted_indices[:num_to_take]

            small_cap_stats = filtered_stat[smallest_cap_indices]
            small_cap_codes = filtered_codes[smallest_cap_indices]

            df = pd.DataFrame(small_cap_stats, index=small_cap_codes, columns=columns)

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

    updater.update()

    # 매도
    매도종목 = agent.accounts["stock"].keys()
    매수종목 = np.sort(df.index) # df.index should be valid codes from small_cap_codes

    # Check if 매도종목 is not empty before calling get_info
    if len(매도종목) > 0:
        현재가_매도 = data_stock.get_info(updater._date, codes=list(매도종목), fields=["현재가"]).reshape(-1)
        # Ensure order of 현재가_매도 matches 매도종목 if get_info doesn't guarantee it (though it should for list of codes)
        # For safety, one might re-index, but assuming get_info(codes=X) returns in order of X or provides means to align.
        # The original code iterated dict keys and then an indexed array, assuming alignment.

        idx = 0
        for 종목코드 in 매도종목: # Iterating dict keys means order isn't strictly guaranteed unless Python 3.7+
            매도수량 = agent.accounts["stock"][종목코드]["보유수량"]
            # Need to ensure 현재가_매도[idx] corresponds to 종목코드
            # A safer way if get_info result order is not guaranteed with dict.keys():
            # price_for_code = data_stock.get_info(updater._date, codes=[종목코드], fields=["현재가"])[0]
            # agent.sell("stock", 종목코드, price_for_code, 매도수량, 주문종류="조건부지정가")
            # However, the original code did: 현재가 = data_stock.get_info(updater._date, codes=매도종목...); for i, 종목코드... 현재가[i]
            # This implies an order. Sticking to a similar pattern for now.
            agent.sell("stock", 종목코드, 현재가_매도[idx], 매도수량, 주문종류="조건부지정가")
            idx += 1


    # 매수
    # Check if 매수종목 is not empty
    if len(매수종목) > 0:
        현재가_매수 = data_stock.get_info(updater._date, codes=매수종목, fields=["현재가"]).reshape(-1)
        i = 0
        for 종목코드 in 매수종목: # 매수종목 is a sorted NumPy array
            if not np.isnan(현재가_매수[i]):
                매수수량 = int(agent.total_balance / 50 / 현재가_매수[i])
                if 매수수량 > 0 : # Ensure positive quantity to buy
                    agent.buy("stock", 종목코드, 현재가_매수[i], 매수수량, 주문종류="조건부지정가")
            i += 1

    for i in range(20):
        updater.update()
        if updater._date == updater._list_date[-1]:
            break
# Profiler dump/print calls removed
# Final print statements for profile stats removed
