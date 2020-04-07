import six  # noqa
from sklearn.linear_model import LinearRegression

LR = LinearRegression()


def model(data):
    from proxy_pkg_import import pkg_func  # noqa
    pkg_func()
    assert hasattr(LR, 'predict')
    return data
