import numpy as np
cimport numpy as np
from cpython.datetime cimport date
import pickle

ctypedef int int_t

def load_data(file, name):
    """
    make_data로 저장한 데이터를 읽어온다.
    :param file: make_data로 저장한 hdf5 파일 이름
    :param name: 쓸 데이터의 이름
    :return:
    """
    with open("%s-%s.axis" % (file.filename, name), "rb") as f:
        axis = pickle.load(f)

    array = file[name][:]

    return array, axis

cdef class DataAsset:
    """
    hdf5에서 읽어온 데이터를 가지고 있는 객체.
    """

    cdef readonly np.ndarray array
    cdef readonly np.ndarray dates, codes, fields
    cdef np.ndarray _idx_sync

    cdef readonly dict date2idx, code2idx, field2idx

    cdef date _date

    def __cinit__(self, np.ndarray array, axis):
        """

        :param array: numpy.array, load_data로 부터 읽은 array, 각 axis는 날짜, 종목코드, 필드 순서이다.
        :param axis: tuple, (list(날짜), list(종목코드), list(필드))로 구성되어있다.
        :param chunks: int, chunk size 한번에 쓸 데이터보다 큰 사이즈로 설정한다.
        :param in_memory: bool, in-memory로 할 것인지 설정한다.
        """
        self.dates, self.codes, self.fields = np.array(axis[0]), np.array(axis[1]), np.array(axis[2])

        self.array = array

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

        self.array = self.array[:, self._idx_sync, :].astype(float)

    def resampling(self, idx):
        self._idx_sync = self._idx_sync[idx]  # 이 indices를 통해 종목코드 순서를 맞춘다.
        self.codes = self.codes[idx]

        self.code2idx = dict()
        for i in range(len(self.codes)):
            self.code2idx[self.codes[i]] = i

    # cpdef get_info(self, date day, int num=1, codes=None, fields=None):
    cpdef np.ndarray[np.float64_t, ndim=3] get_info(self, date day, int num=1, codes=None, fields=None):

        """

        :param date: Pandas.Timestamp
        :param num: int, 반환할 과거 일수
        :param codes: list, 반환할 종목코드들의 리스트
        :param fields: list, 반환할 필드들의 리스트
        :return: numpy.array, 각 axis는 (날짜, 종목코드, 필드)이다.
        """

        cdef np.ndarray[np.float64_t, ndim=3] array
        cdef int idx_date
        cdef list idx_codes, idx_fields

        if day not in self.dates:
            raise Exception

        idx_date = self.date2idx[day]
        array = self.array[max(0, idx_date - num + 1):idx_date + 1]  # 해당 날짜의 데이터가 -1에 위치하도록 array를 slice 한다.

        # 요청한 codes와 fieldes를 indexing
        if codes is not None:
            idx_codes = [self.code2idx[code] for code in codes]
            array = array[:, idx_codes, :]
        if fields is not None:
            idx_fields = [self.field2idx[field] for field in fields]
            array = array[:, :, idx_fields]

        return array

    def update_date(self, date day):
        # SushiLife.Updater onject에서 날짜가 갱신 될 경우 실행되는 함수
        self._date = day

    def init(self, date day):
        # SushiLife.Updater onject에서 initialization 함수가 실행 될 경우 실행되는 함수
        self.update_date(day)
