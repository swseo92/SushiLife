import plotly
import plotly.graph_objs as go
import visdom

class Chart(visdom.Visdom):
    def __init__(self):
        visdom.Visdom.__init__(self)
        return

    def make_chart(self, data):
        layout = go.Layout(
            xaxis=dict(
                rangeslider=dict(
                    visible=False
                )
            )
        )

        fig = dict(data=[], layout=layout)

        candle = go.Candlestick(open=data[:, 0, 1],
                                high=data[:, 0, 2],
                                low=data[:, 0, 3],
                                close=data[:, 0, 0], yaxis='y2', showlegend=False)

        volume = dict(y=data[:, 0, 4], type='bar', yaxis='y', showlegend=False)

        fig["data"].append(candle)
        fig["data"].append(volume)

        fig['layout']['yaxis'] = dict(domain=[0, 0.2], showticklabels=False)
        fig['layout']['yaxis2'] = dict(domain=[0.2, 1])

        self.fig = fig

    def show(self):
        self.plotlyplot(self.fig)
