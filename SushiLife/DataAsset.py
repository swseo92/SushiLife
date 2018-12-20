import numpy as np
import h5py
import pickle
import dask.array as da


def make_data(filename, name, data_df, fields=None, dtype=None, dates=None, ):
    """
    sql에서 읽은 dataframe을 (날짜, 종목코드, 필드)로 구성된 3-dimensional array로 변환한다.
    :param data_df: pandas.dataframe, 종목코드와 날짜를 각각 table과 index로 갖는 pandas dataframe
    :param dates:
    :return: numpy.array, (list, list, list), 두번째 tuple은 각각 날짜, 종목코드, 필드의 리스트로 구성된다.
    """

    if dates is None:
        dates = data_df["A005930"].index  # A005930 : 삼성전자
    else:
        dates = dates

    codes = list(data_df.keys())
    list_data = list()

    fields = list(data_df[codes[0]].columns)
    if dtype == "stock":
        fields = ["현재가", "시가", "고가", "저가", "대비", "거래량(주)", "거래대금(원)", "상장시가총액(원)", "시장구분"]

    for code in codes:
        print(code)
        dummy = data_df[code][fields].reindex(dates).fillna(np.nan)
        list_data.append(np.array(dummy).reshape(len(dates), 1, -1))

    dates = list(dates)
    array = np.concatenate(list_data, axis=1)

    if dtype == "stock":

        idx = fields.index("시장구분")

        array[:, :, idx][np.where(array[:, :, idx] == "코스피")] = 0
        array[:, :, idx][np.where(array[:, :, idx] == "코스닥")] = 1
        array = array.astype('f')

    f = h5py.File(filename, "a")
    try:
        f.create_dataset(name, data=array, maxshape=(None, None, None))
    except:
        f[name].resize((array.shape[0], array.shape[1], array.shape[2]))  # field를 2개 추가하도록 resize한다.
        f[name][:] = array
    f.close()

    with open("%s-%s.axis" % (filename, name), "wb") as f:
        pickle.dump((dates, codes, fields), f)


def load_data(file, name, chunks=5, in_memory=False):
    with open("%s-%s.axis" % (file.filename, name), "rb") as f:
        axis = pickle.load(f)

    array = file[name]
    if in_memory:
        array = array[:]

    array = da.from_array(array, chunks=(chunks, len(axis[1]), len(axis[2])))

    return array, axis

class DataAsset:
    def __init__(self, array, axis, chunks=300):
        #         array, axis = make_data(data_df)

        self.dates, self.codes, self.fields = np.array(axis[0]), np.array(axis[1]), np.array(axis[2])
        self.array = array
        self._idx_sync = np.arange(len(self.codes))

        # 해당 코드 및 필드의 index를 빠르게 찾기위해 dictionary를 사용
        self.code2idx = dict()
        for i in range(len(self.codes)):
            self.code2idx[self.codes[i]] = i

        self.field2idx = dict()
        for i in range(len(self.fields)):
            self.field2idx[self.fields[i]] = i

        self._chunks = chunks
        self._dates_chunk = []

        self._date = None

    def set_sync(self, idx):
        self._idx_sync = self._idx_sync[idx]
        self.codes = self.codes[idx]

        self.code2idx = dict()
        for i in range(len(self.codes)):
            self.code2idx[self.codes[i]] = i

    def get_info(self, date, num=1, codes=None, fields=None):
        """

        :param date: Pandas.Timestamp
        :param num: int, 반환할 과거 일수
        :param codes: list, 반환할 종목코드들의 리스트
        :param fields: list, 반환할 필드들의 리스트
        :return: numpy.array
        """
        if date not in self._dates_chunk:
            self._make_chunk()
        idx_date = self._dates_chunk.index(date)
        array = self._array_chunk[max(0, idx_date - num + 1):idx_date + 1]

        if codes is not None:
            idx_codes = [self.code2idx[code] for code in codes]
            array = array[:, idx_codes, :]
        if fields is not None:
            idx_fields = [self.field2idx[field] for field in fields]
            array = array[:, :, idx_fields]

        if num == 1:
            array = array[0]

        return array

    def _make_chunk(self):
        # 현재 날짜에 인접한 날짜의 array들을 미리 메모리에 읽어 효율을 높인다.
        idx_date = list(self.dates).index(self._date)
        self._dates_chunk = list(self.dates)[max(0, idx_date - self._chunks):idx_date + self._chunks]
        self._array_chunk = self.array[max(0, idx_date - self._chunks):idx_date + self._chunks, self._idx_sync].compute()

    def update_date(self, date):
        self._date = date
        if date not in self._dates_chunk:
            self._make_chunk()

    def init(self, date):
        self.update_date(date)
