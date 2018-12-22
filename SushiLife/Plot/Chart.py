import plotly
import plotly.graph_objs as go
import visdom
import numpy as np

class Chart(visdom.Visdom):
    def __init__(self):
        visdom.Visdom.__init__(self)
        self.data = None
        return

    def make_chart(self, data, list_date):
        self.data = data
        self.list_date = list_date
        layout = go.Layout(xaxis=dict(type='date',
                                    rangeslider=dict(visible=False), range=[list_date[0], list_date[-1]]))

        fig = dict(data=[], layout=layout)

        candle = go.Candlestick(
            x=list_date,
            open=data[:, 1],
            high=data[:, 2],
            low=data[:, 3],
            close=data[:, 0], yaxis='y', showlegend=False)

        volume = dict(x=list_date, y=data[:, 4], type='bar', yaxis='y2', showlegend=False)

        fig["data"].append(candle)
        fig["data"].append(volume)

        fig['layout']['yaxis'] = dict(domain=[0.2, 1], showticklabels=False)
        fig['layout']['yaxis2'] = dict(domain=[0, 0.2])

        self.fig = fig

    def set_data(self, data, yaxis="y", **kwargs):
        idx = ~np.isnan(data)

        data = dict(x=self.list_date[idx], y=data[idx], yaxis=yaxis, showlegend=False, **kwargs)
        self.fig["data"].append(data)

    def show(self):
        self.plotlyplot(self.fig)
        print("http://localhost:8097/#")

