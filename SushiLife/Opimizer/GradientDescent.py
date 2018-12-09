import numpy as np


class GradientDescent:
    def __init__(self, eval_func, num_param, pool=None, guess=None):
        self.eval_func = eval_func
        self.num_param = num_param

        if guess is None:
            self.point = np.random.sample(self.num_param)
        else:
            self.point = np.array(guess)

        self._pool = pool

    def run(self, lr=0.05, threshold=1e-5):
        delta = 1e3
        self.lr = lr
        val_now = float(self.eval_func(self.point))
        while delta > threshold:
            point_next = self._get_next_point()
            val_next = float(self.eval_func(point_next))

            delta = np.abs(val_now - val_next)

            self.point = point_next
            val_now = val_next
            print("\n\n")

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
        point_next = self.point + grad_norm * self.lr

        return point_next
