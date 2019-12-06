import numpy as np


class GradientDescent:
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

    def run(self, lr=0.05, lr_int=5, threshold=1e-5):
        delta = 1e3
        self.lr = lr
        self.lr_int = lr_int
        while delta > threshold:

            list_x = list()
            list_x.append(self.point)  # 현재 포인트

            for i in range(len(self.point)):  # gradient를 계산하기 위한 점을 추가
                h = np.zeros_like(self.point)

                if i in self.idx_int:
                    h[i] = self.lr_int
                else:
                    h[i] = self.lr

                x_plus_h = self.point + h
                x_minus_h = self.point - h

                list_x.append(x_plus_h)
                list_x.append(x_minus_h)

            if self._pool is None:
                list_y = np.array([self.eval_func(x) for x in list_x]).reshape(-1)
            else:
                list_y = np.array(self._pool.map(self.eval_func, list_x)).reshape(-1)

            val_now = float(list_y[0])  # 현재 지점에서 value
            print(self.point, val_now)

            list_y = list_y[1:]

            # stepping
            gradient = (list_y[0::2] - list_y[1::2]) / (2 * self.lr)
            grad_norm = gradient / np.sum(gradient ** 2) ** 0.5

            d_point = grad_norm * self.lr
            d_point[self.idx_int] = d_point[self.idx_int] / np.abs(d_point[self.idx_int]) * np.ceil(np.abs(d_point[self.idx_int]))

            d_point[np.isnan(d_point)] = 0
            point_next = self.point + d_point
            self.point = point_next

        return self.point

    def _get_next_point(self):
        list_x = list()
        for i in range(len(self.point)):
            h = np.zeros_like(self.point)
            h[i] = self.lr

            x_plus_h = self.point + h
            x_minus_h = self.point - h

            list_x.append(x_plus_h)
            list_x.append(x_minus_h)

        if self._pool is None:
            list_y = np.array([self.eval_func(x) for x in list_x]).reshape(-1)
        else:
            list_y = np.array(self._pool.map(self.eval_func, list_x)).reshape(-1)

        gradient = (list_y[0::2] - list_y[1::2]) / (2 * self.lr)

        grad_norm = gradient / np.sum(gradient ** 2) ** 0.5
        d_point = grad_norm * self.lr
        d_point[self.idx_int] = d_point[self.idx_int] / np.abs(d_point[self.idx_int]) * np.ceil(np.abs(d_point[self.idx_int]))


        point_next = self.point + d_point

        return point_next
