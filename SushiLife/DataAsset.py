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
        # print(code)
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
    f.create_dataset(name, data=array)
    f.close()

    with open("%s-%s.axis" % (filename, name), "wb") as f:
        pickle.dump((dates, codes, fields), f)


def load_data(file, name, chunks=5):
    """
    make_data로 저장한 데이터를 읽어온다.
    :param file: make_data로 저장한 hdf5 파일 이름
    :param name: 쓸 데이터의 이름
    :param chunks: chunk size
    :return:
    """
    with open("%s-%s.axis" % (file.filename, name), "rb") as f:
        axis = pickle.load(f)

    array = file[name]
    array = da.from_array(array, chunks=(chunks, len(axis[1]), len(axis[2])))

    return array, axis


class DataAsset:
    """
    hdf5에서 읽어온 데이터를 가지고 있는 객체.
    """
    def __init__(self, array, axis, chunks=300, in_memory=False):
        """

        :param array: numpy.array, load_data로 부터 읽은 array, 각 axis는 날짜, 종목코드, 필드 순서이다.
        :param axis: tuple, (list(날짜), list(종목코드), list(필드))로 구성되어있다.
        :param chunks: int, chunk size 한번에 쓸 데이터보다 큰 사이즈로 설정한다.
        :param in_memory: bool, in-memory로 할 것인지 설정한다.
        """
        self.dates, self.codes, self.fields = np.array(axis[0]), np.array(axis[1]), np.array(axis[2])

        if in_memory:
            # in-memory를 사용한다면 dask array를 numpy.array로 바꾸어 메모리에 저장한다.
            self.array = array.compute()
            self.in_memory = True
        else:
            self.array = array
            self.in_memory = False

        self._idx_sync = np.arange(len(self.codes))

        # 해당 코드 및 필드의 index를 빠르게 찾기위해 dictionary를 사용
        self.date2idx = dict()
        for i in range(len(self.dates)):
            self.date2idx[self.dates[i]] = i

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
        """
        각 데이터별로 종목코드 순서가 다르기때문에 종목코드 순서를 맞춰주기 위한 함수
        :param idx: list-like object, 종목코드 순서를 맞춰주는 indices가 들어있다.
        :return:
        """
        self._idx_sync = self._idx_sync[idx]  # 이 indices를 통해 종목코드 순서를 맞춘다.
        self.codes = self.codes[idx]

        self.code2idx = dict()
        for i in range(len(self.codes)):
            self.code2idx[self.codes[i]] = i

        if self.in_memory:
            self.array = self.array[:, self._idx_sync, :]

    def resampling(self, idx):
        self._idx_sync = self._idx_sync[idx]  # 이 indices를 통해 종목코드 순서를 맞춘다.
        self.codes = self.codes[idx]

        self.code2idx = dict()
        for i in range(len(self.codes)):
            self.code2idx[self.codes[i]] = i

        if self.in_memory:
            self.array = self.array[:, self._idx_sync, :]

    def get_info(self, date, num=1, codes=None, fields=None):
        """

        :param date: Pandas.Timestamp
        :param num: int, 반환할 과거 일수
        :param codes: list, 반환할 종목코드들의 리스트
        :param fields: list, 반환할 필드들의 리스트
        :return: numpy.array, 각 axis는 (날짜, 종목코드, 필드)이다.
        """

        if num > self._chunks:
            raise Exception("요청할 수 있는 최대 날짜 수는 chunk size를 넘을 수 없습니다.")

        if date not in self.dates:
            raise Exception

        if date not in self._dates_chunk:
            # 요청한 날짜에 해당하는 데이터가 없을 경우 해당 날짜가 속한 chunk를 메모리로 불러온다.
            self._make_chunk(date)
        idx_date = self._dates_chunk.index(date)
        array = self._array_chunk[max(0, idx_date - num + 1):idx_date + 1]  # 해당 날짜의 데이터가 -1에 위치하도록 array를 slice 한다.

        # 요청한 codes와 fieldes를 indexing
        if codes is not None:
            idx_codes = [self.code2idx[code] for code in codes]
            array = array[:, idx_codes, :]
        if fields is not None:
            idx_fields = [self.field2idx[field] for field in fields]
            array = array[:, :, idx_fields]

        if num == 1:
            array = array[0]

        return array

    def _make_chunk(self, date):
        # 현재 날짜에 인접한 날짜의 array들을 미리 메모리에 읽어 효율을 높인다.
        idx_date = list(self.dates).index(date)
        self._dates_chunk = list(self.dates)[max(0, idx_date - self._chunks):idx_date + self._chunks]
        if self.in_memory:
            self._array_chunk = self.array[max(0, idx_date - self._chunks):idx_date + self._chunks]
        else:
            # dask.array에 있는 chunk를 불러서 메모리에 저장한다.
            self._array_chunk = self.array[max(0, idx_date - self._chunks):idx_date + self._chunks, self._idx_sync].compute()

    def update_date(self, date):
        # SushiLife.Updater onject에서 날짜가 갱신 될 경우 실행되는 함수
        self._date = date
        if date not in self._dates_chunk:
            self._make_chunk(date)

    def init(self, date):
        # SushiLife.Updater onject에서 initialization 함수가 실행 될 경우 실행되는 함수
        self.update_date(date)
