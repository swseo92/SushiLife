import numpy as np
import pandas as pd


class Updater:
    def __init__(self, date, list_date):
        self._list_date = list_date

        self._date = date
        self._date_start = date

        self.state = True
        self._init = False

        # 날짜가 업데이트 될 경우 내부 정보를 업데이트할 instance를 넣는다.
        # 해당 instance들은 "update_date" method를 갖고 있어야한다.
        # 해당 instance들은 "reset" method를 갖고 있어야한다.

        self.list_data_instance = list()
        self.list_agent_instance = list()
        self.list_exchange_instance = list()

    def set_data(self, instance):
        methods = dir(instance)
        if (('update_date' not in methods)
                or ('init' not in methods)):
            raise Exception

        self.list_data_instance.append(instance)

    def set_agent(self, instance):
        methods = dir(instance)
        if (('update_date' not in methods)
                or ('init' not in methods)):
            raise Exception

        self.list_agent_instance.append(instance)

    def set_exchange(self, instance):
        methods = dir(instance)
        if (('update_date' not in methods)
                or ('init' not in methods)):
            raise Exception

        self.list_exchange_instance.append(instance)

    def update(self):
        if not self._init:
            # init을 하지 않은경우 백테스트가 실행되지 않는다.
            raise Exception

        self._date = self._date + pd.Timedelta(days=1)

        while self._date not in self._list_date:
            self._date = self._date + pd.Timedelta(days=1)

        list_instance4update = self.list_data_instance + self.list_agent_instance + self.list_exchange_instance
        for instance in list_instance4update:
            instance.update_date(self._date)

    def initialization(self):
        self._init = True
        self._date = self._date_start

        sync_DataAssets(self.list_data_instance)

        while self._date not in self._list_date:
            self._date = self._date + pd.Timedelta(days=1)

        list_initialization4update = self.list_data_instance + self.list_exchange_instance + self.list_agent_instance

        for instance in list_initialization4update:
            instance.init(self._date)


def sync_DataAsset(DataAsset1, DataAsset2):
    _, idx_sync1, idx_sync2 = np.intersect1d(DataAsset1.codes, DataAsset2.codes, return_indices=True)
    DataAsset1.set_sync(idx_sync1)
    DataAsset2.set_sync(idx_sync2)


def sync_DataAssets(list_DataAsset):
    DataAsset0 = list_DataAsset[0]
    list_DataAsset = list_DataAsset[1:]

    for i in range(len(list_DataAsset)):
        sync_DataAsset(DataAsset0, list_DataAsset[i])
        for j in range(i):
            sync_DataAsset(DataAsset0, list_DataAsset[j])
