import numpy as np
import pandas as pd
import h5py
import cProfile
import pstats
import io

from SushiLife import *

# Adjusted HDF5 path assuming execution from repo root
f = h5py.File("SushiLife/data/stock_info.hdf5", "r")
array_stock, axis_stock = load_data(f, "stock", chunks=5)
array_value, axis_value = load_data(f, "value", chunks=5)

data_stock = DataAsset(array_stock, axis_stock, chunks=5, in_memory=False)
data_value = DataAsset(array_value, axis_value, chunks=5, in_memory=False)

updater = Updater(pd.Timestamp(2003, 1, 1), data_stock.dates)

# 거래소 생성
exchange_stock = Exchange()
exchange_stock.set_DataAsset(data_stock)  # 주가 데이터를 거래소에 등록한다.

# 주식 계좌 생성
stock_account = StockAccount(exchange_stock, 출력=False)

# 거래 에이전트 생성 및 주식 계좌 등록
agent = Agent(1e8, 출력=True)
agent.set_account("stock", stock_account)  # 각 자산을 보관할 지갑을 생성한다.

# 날짜가 변할시 업데이트 요청
updater.set_data(data_stock)
updater.set_data(data_value)

updater.set_exchange(exchange_stock)

updater.set_agent(agent)

profiler_init = cProfile.Profile()
profiler_init.enable()
updater.initialization()
profiler_init.disable()

# 백테스트
columns = ["상장시가총액(원)", "지배주주순이익(원)(직전4분기)", "지배주주지분(원)",
           "현금흐름(원)(직전4분기)", "매출액(원)(직전4분기)"]

#  백테스트 시작
profiler_loop = cProfile.Profile()
profiler_loop.enable()
while updater._date != updater._list_date[-1]:
    fin_stat = data_value.get_info(updater._date, num=1,
                                   fields=columns)

    # Original columns list:
    # columns = ["상장시가총액(원)", "지배주주순이익(원)(직전4분기)", "지배주주지분(원)",
    #            "현금흐름(원)(직전4분기)", "매출액(원)(직전4분기)"]
    # fin_stat is a NumPy array (num_all_codes, num_columns)
    # data_value.codes is a NumPy array of all codes in data_value

    market_cap_col_name = "상장시가총액(원)"
    # Find the index of the market cap column dynamically
    # Ensure 'columns' is the list passed to get_info and matches fin_stat's columns
    market_cap_col_idx = -1
    for i, col_name in enumerate(columns):
        if col_name == market_cap_col_name:
            market_cap_col_idx = i
            break

    if market_cap_col_idx == -1:
        raise ValueError(f"Column '{market_cap_col_name}' not found in 'columns'")

    # Filter out NaNs in market_cap
    # Ensure fin_stat has data. If it's empty, df will be empty.
    if fin_stat.size == 0:
        df = pd.DataFrame(columns=columns) # Create empty DataFrame
    else:
        valid_indices_filter = ~np.isnan(fin_stat[:, market_cap_col_idx])
        filtered_stat = fin_stat[valid_indices_filter]

        # data_value.codes might be longer if get_info can return a subset of codes.
        # For this optimization, we assume get_info for data_value returns all codes,
        # so data_value.codes aligns with the rows of the initial fin_stat.
        # If get_info was called with specific codes, this alignment is broken.
        # The original templete.py calls get_info on data_value without specific codes,
        # implying it gets all codes.
        current_codes_for_fin_stat = data_value.codes # This should align with the original fin_stat
        filtered_codes = current_codes_for_fin_stat[valid_indices_filter]

        if filtered_stat.shape[0] == 0: # If all are NaN or empty after filtering
            df = pd.DataFrame(columns=columns)
        else:
            # Sort by market_cap and take smallest 30%
            # argsort on the market_cap_col_idx of the filtered_stat
            sorted_indices = np.argsort(filtered_stat[:, market_cap_col_idx])

            num_to_take = int(filtered_stat.shape[0] * 0.3)
            if num_to_take == 0 and filtered_stat.shape[0] > 0 : # Ensure at least one if possible and not empty
                num_to_take = 1

            smallest_cap_indices = sorted_indices[:num_to_take]

            small_cap_stats = filtered_stat[smallest_cap_indices]
            small_cap_codes = filtered_codes[smallest_cap_indices]

            # Now create a smaller DataFrame
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
    매수종목 = np.sort(df.index)
    현재가 = data_stock.get_info(updater._date, codes=매도종목, fields=["현재가"]).reshape(-1)

    i = 0
    for 종목코드 in 매도종목:
        매도수량 = agent.accounts["stock"][종목코드]["보유수량"]
        agent.sell("stock", 종목코드, 현재가[i], 매도수량, 주문종류="조건부지정가")
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
        updater.update()
        if updater._date == updater._list_date[-1]: # Ensure break from outer loop if inner loop reaches end
            break
profiler_loop.disable()

profiler_init.dump_stats("init_profile_opt1.prof")
profiler_loop.dump_stats("loop_profile_opt1.prof")

print("--- Initialization Profile Stats (opt1) ---")
s_init = io.StringIO()
ps_init = pstats.Stats(profiler_init, stream=s_init).sort_stats('cumulative')
ps_init.print_stats(15)
print(s_init.getvalue())

print("\n--- Main Loop Profile Stats (opt1) ---")
s_loop = io.StringIO()
ps_loop = pstats.Stats(profiler_loop, stream=s_loop).sort_stats('cumulative')
ps_loop.print_stats(15)
print(s_loop.getvalue())
