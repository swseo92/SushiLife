import numpy as np
import pandas as pd


class Updater:
    def __init__(self, date, list_date):
        self._list_date = list_date

        self._date = date
        self._date_start = date

        self.state = True

        # 날짜가 업데이트 될 경우 내부 정보를 업데이트할 instance를 넣는다.
        # 해당 instance들은 "update_date" method를 갖고 있어야한다.
        # 해당 instance들은 "reset" method를 갖고 있어야한다.

        self.list_instance4update = list()
        self.update()

    def set_instance4update(self, instance):
        """
        날짜가 변할 경우 업데이트가 필요한 instance를 등록한다.
        :param instance: class, method로 "update_date"과 "reset"를 가져야한다.
        :return:
        """

        methods = dir(instance)
        if (('update_date' not in methods)
                or ('reset' not in methods)):
            raise Exception

        # 업데이트 순서를 고려하여 Account는 대응되는 Exchange가 업데이트 된 후 업데이트되어야 한다.
        if "type" in methods:
            if instance.type == "Account":
                if instance._exchange not in self.list_instance4update:
                    raise Exception

        self.list_instance4update.append(instance)
        instance.update_date(self._date)

    def update(self):
        self._date = self._date + pd.Timedelta(days=1)

        while self._date not in self._list_date:
            self._date = self._date + pd.Timedelta(days=1)

        for instance in self.list_instance4update:
            instance.update_date(self._date)

    def reset(self):
        self._date = self._date_start
        self.update()
        for instance in self.list_instance4update:
            instance.reset(self._date)
