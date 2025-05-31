import numpy as np
# cimport numpy as np # if using more advanced numpy C-API

# account: Python dictionary (original)
# names: list of Python strings
# current_price_updates_all_holdings: NumPy array (num_holdings, 2) [new_current_price, price_diff]
# 평단가_arr, 보유수량_arr, 현재가_arr_prev_day: NumPy arrays for the assets in 'names'
def apply(평단가_arr, 보유수량_arr, 현재가_arr_prev_day, list_names_py, current_price_updates_all_holdings):
    cdef double total_balance = 0.0
    cdef int num_holdings = len(list_names_py) # Or use shape of one of the arrays

    # Ensure arrays are C-contiguous if doing direct memory access, though not strictly needed for basic indexing
    # 평단가_arr_c = np.ascontiguousarray(평단가_arr, dtype=np.double)
    # 보유수량_arr_c = np.ascontiguousarray(보유수량_arr, dtype=np.double)
    # 현재가_arr_prev_day_c = np.ascontiguousarray(현재가_arr_prev_day, dtype=np.double)
    # current_price_updates_all_holdings_c = np.ascontiguousarray(current_price_updates_all_holdings, dtype=np.double)

    cdef double price_today, price_yesterday, price_adjusted_for_split
    cdef double price_diff_from_update
    cdef double shares_original, shares_new
    cdef double avg_price_original, avg_price_new
    cdef double split_adjust_coeff
    cdef double returns_ratio

    # Calculate initial total_balance based on previous day's prices
    for i in range(num_holdings):
        total_balance += 현재가_arr_prev_day[i] * 보유수량_arr[i]

    # Create new arrays for modification, or modify in-place if safe
    평단가_arr_new = np.copy(평단가_arr)
    보유수량_arr_new = np.copy(보유수량_arr)

    delisted_indices = [] # Keep track of delisted items by index

    for i in range(num_holdings):
        price_today = current_price_updates_all_holdings[i, 0]
        price_diff_from_update = current_price_updates_all_holdings[i, 1] # 대비
        price_yesterday = 현재가_arr_prev_day[i] # This is account[name]["현재가"] from previous day
        shares_original = 보유수량_arr[i]
        avg_price_original = 평단가_arr[i]

        if np.isnan(price_today): # 상장폐지 (Delisted)
            # Mark for deletion by Python side, e.g., by setting shares to 0
            보유수량_arr_new[i] = 0
            평단가_arr_new[i] = 0 # Or np.nan
            # No print here, Python side will handle
            delisted_indices.append(i) # Store index of delisted item
        else:
            returns_ratio = 0
            if price_yesterday != 0: # Avoid division by zero
                returns_ratio = price_today / price_yesterday

            avg_price_new = avg_price_original
            shares_new = shares_original

            # Handle stock splits/reverse splits (가격 변동폭이 크고, 대비가 있는 경우)
            if (returns_ratio > 1.35 or returns_ratio < 0.65) and price_diff_from_update != 0 and price_yesterday != 0:
                price_adjusted_for_split = price_today - price_diff_from_update
                if price_yesterday != 0: # Avoid division by zero
                     split_adjust_coeff = price_adjusted_for_split / price_yesterday
                     if split_adjust_coeff != 0: # Avoid division by zero for adjustment
                        avg_price_new = avg_price_original * split_adjust_coeff
                        shares_new = max(1.0, np.floor(shares_original / split_adjust_coeff))

            평단가_arr_new[i] = avg_price_new
            보유수량_arr_new[i] = shares_new

            # 현재가 (current price in account dict) will be updated in Python to price_today

    return 평단가_arr_new, 보유수량_arr_new, total_balance, delisted_indices
