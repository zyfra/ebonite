import sys

import pandas as pd

from ebonite.ext.flask.client import HTTPClient


def main():
    try:
        value_a, value_b = float(sys.argv[1]), float(sys.argv[2])
    except (IndexError, ValueError):
        print(f'Usage: {sys.argv[0]} [float] [float]')
        return

    client = HTTPClient()
    df = pd.DataFrame({'a': [value_a], 'b': [value_b]})

    pred = client.predict(df)
    # pred is numpy array of shape (1,)
    print(pred.item())

    proba = client.predict_proba(df)
    # proba is numpy array of shape (1, 2)
    print(list(proba[0]))


if __name__ == '__main__':
    main()
