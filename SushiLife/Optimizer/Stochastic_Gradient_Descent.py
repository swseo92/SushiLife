import numpy as np
import pandas as pd
import sys
import time


class BackTestSGD(object):

    def __call__(self, array, data_stock=None, save=False):
        pass

    def set_period(self, period):
        self.period = period


class StochasticGradientDescent:
    def __init__(self, eval_func, num_param, pool=None, guess=None):
        self.eval_func = eval_func
        self.num_param = num_param

        self.idx_int = list()
        for i in range(len(guess)):
            if type(guess[i]) is int:
                self.idx_int.append(i)

        if guess is None:
            self.point = np.random.sample(self.num_param)
        else:
            self.point = np.array(guess)

        self._pool = pool

    def fit(self, epoch, steps_per_epoch=100, period=[None, None], validataion_period=None, term=30, lr=0.05, lr_int=5, decay=0.05, warm_epoch=50):
        days = (period[1] - period[0]).days - term - 10
        if steps_per_epoch is None:
            steps_per_epoch = int(days / term)

        lr_warm = lr / (1 + decay) ** warm_epoch / 10
        if warm_epoch > 0:
            print("Start Warm Up Epochs")
            self._update_epoch(warm_epoch, steps_per_epoch, days, period, validataion_period, term, lr_warm, lr_int, -decay)

        print("Start Train")
        self._update_epoch(epoch, steps_per_epoch, days, period, validataion_period, term, lr, lr_int, decay)

    def _update_epoch(self, num_epoch, steps_per_epoch, days, period, validataion_period, term, lr, lr_int, decay):
        if validataion_period is None:
            validataion_period = period
        for i in range(num_epoch):
            self.list_value = list()
            start = time.time()
            for j in range(steps_per_epoch):
                idx = np.random.choice(days)
                start_day = period[0] + pd.Timedelta(days=idx)
                end_day = period[0] + pd.Timedelta(days=idx + term)
                self.eval_func.set_period([start_day, end_day])

                self._update_one_step(lr=lr, lr_int=lr_int)
                sys.stdout.write("\repoch: {}, step: {} / {}, value: {}".format(i+1, j+1, steps_per_epoch,
                                                                                np.mean(self.list_value)))
                sys.stdout.flush()

            self.eval_func.set_period(validataion_period)
            value_epoch = self.eval_func(self.point, save=True)
            end = time.time()
            sys.stdout.write("\repoch: {}, lr:{}, value: {}, mean_value: {}, time: {}\n".format(i+1, lr, value_epoch[0], np.mean(self.list_value), end-start))
            # learning rate warm up
            lr = lr * (1 - decay)

    def _update_one_step(self, lr=0.05, lr_int=5):
        list_x = list()
        list_x.append(self.point)  # 현재 포인트

        for i in range(len(self.point)):  # gradient를 계산하기 위한 점을 추가
            h = np.zeros_like(self.point)

            if i in self.idx_int:
                h[i] = lr_int
            else:
                h[i] = lr

            x_plus_h = self.point + h
            x_minus_h = self.point - h

            list_x.append(x_plus_h)
            list_x.append(x_minus_h)

        if self._pool is None:
            list_y = np.array([self.eval_func(x) for x in list_x]).reshape(-1)
        else:
            list_y = np.array(self._pool.map(self.eval_func, list_x)).reshape(-1)

        val_now = float(list_y[0])  # 현재 지점에서 value
        self.list_value.append(val_now)

        list_y = list_y[1:]

        # stepping
        gradient = (list_y[0::2] - list_y[1::2]) / (2 * lr)
        grad_norm = gradient / np.sum(gradient ** 2) ** 0.5

        d_point = grad_norm * lr
        d_point[self.idx_int] = d_point[self.idx_int] / np.abs(d_point[self.idx_int]) * np.ceil(
            np.abs(d_point[self.idx_int]))

        d_point[np.isnan(d_point)] = 0
        point_next = self.point + d_point
        self.point = point_next
