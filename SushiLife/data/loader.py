import sqlite3
import multiprocessing
import pandas as pd
import time


class read_db_process(multiprocessing.Process):
    def __init__(self, filename, data_dict, list_code, lock, field=None, date_format="%Y-%m-%d"):
        multiprocessing.Process.__init__(self)
        self.args = (filename, data_dict, list_code, field, date_format, lock, self)

    def target(self, filename, data_dict, list_code, field, date_format, lock, p):
        con_sql = sqlite3.connect(filename)
        if field is not None:
            query = 'Select "날짜"'
            for name in field:
                query = query + ', "%s"' % name
            query = query + ' from "%s"'
        else:
            query = 'Select * From %s'

        while list_code:
            lock.acquire()
            try:
                종목코드 = list_code.pop(0)
            except IndexError:
                lock.release()
                break
            lock.release()

            query_code = query % (종목코드)
            df = pd.read_sql(query_code, con_sql, index_col='날짜', parse_dates={"날짜": date_format})
            data_dict[종목코드] = df
        con_sql.close()

    def run(self):
        self.target(*self.args)

def read_db(filename, field=None, date_format="%Y-%m-%d", num_process=1, test=False):
    con = sqlite3.connect(filename)

    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

    u = cursor.fetchall()
    list_code = [종목코드[0] for 종목코드 in u]
    if "종료일" in list_code:
        list_code.remove("종료일")
    con.close()

    manager = multiprocessing.Manager()
    lock = multiprocessing.Lock()
    list_process = list()

    data_multi = manager.dict()
    list_code = manager.list(list_code)

    for i in range(num_process):
        p = read_db_process(filename, data_multi, list_code, lock, field=field, date_format=date_format)
        list_process.append(p)

    for p in list_process:
        p.start()

    for p in list_process:
        p.join()

    data_multi2 = dict(data_multi)

    for p in list_process:
        p.terminate()

    del manager, data_multi

    return data_multi2


if __name__ == "__main__":
    ts = time.time()
    filename = "./data/db/상장종목검색.db"
    read_db(filename, num_process=6)

    print(time.time() - ts)