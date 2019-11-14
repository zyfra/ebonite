import os
import sys
from urllib.request import urlopen

import requests


def main():
    try:
        img = sys.argv[1]
    except (IndexError, ValueError):
        print(f'Usage: {sys.argv[0]} [image url]')
        return

    r = requests.post('http://localhost:9000/predict', files={'vector': urlopen(img)})
    r.raise_for_status()

    _, ext = os.path.splitext(img)
    with open(f'result{ext}', 'wb') as f:
        f.write(r.content)


if __name__ == '__main__':
    main()
