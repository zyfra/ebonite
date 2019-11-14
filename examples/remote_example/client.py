import sys

import requests


def main():
    try:
        value_a = float(sys.argv[1])
    except (IndexError, ValueError):
        print(f'Usage: {sys.argv[0]} [float]')
        return
    payload = {
        "vector": [value_a]
    }
    r = requests.post('http://localhost:9000/predict', json=payload)
    r.raise_for_status()
    print(r.json()['data'][0])


if __name__ == '__main__':
    main()
