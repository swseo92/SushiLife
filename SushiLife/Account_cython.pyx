import numpy as np

def apply(account, names, current_price):
    num = current_price.shape[0]

    cdef double total_balance = 0

    cdef double price, price_yesterday, price_adjusted
    cdef double adjust_coeff
    cdef double price_diff
    cdef double shares

    cdef double returns

    cdef int i =0
    for name in names:
        # 전일 결산 후
        price_yesterday = account[name]["현재가"]
        shares = account[name]["보유수량"]

        total_balance += price_yesterday * shares

        # 가격을 오늘 가격으로 업데이트 한다.
        if np.isnan(current_price[i, 0]):
            del account[name]
            if account._print:
                print("\x1b[31m\"%s\"\x1b[0m" % (name + '  상장폐지 !!! ###################################'))
        else:
            price = current_price[i, 0]
            price_yesterday = account[name]["현재가"]
            returns = price / price_yesterday
            if (returns > 1.35) or (returns < 0.65):
                price_diff = current_price[i, 1]
                price_adjusted = price - price_diff
                adjust_coeff = price_adjusted / price_yesterday
                if adjust_coeff == 0:
                    print(names[i])
                account[name]["평단가"] = account[name]["평단가"] * adjust_coeff
                account[name]["보유수량"] = max(1, np.floor(shares / adjust_coeff))

            account[name]["현재가"] = price

            if account[name]["보유수량"] == 0:
                del account[name]
        i += 1
    return account, total_balance