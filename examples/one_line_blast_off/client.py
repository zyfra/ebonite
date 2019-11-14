import sys

import requests


def main():
    try:
        value_a, value_b = float(sys.argv[1]), float(sys.argv[2])
    except (IndexError, ValueError):
        print(f'Usage: {sys.argv[0]} [float] [float]')
        return
    payload = {
        "vector": {
            "values": [
                {
                    "a": value_a,
                    "b": value_b
                }
            ]
        }
    }
    r = requests.post('http://localhost:9000/predict', json=payload)
    r.raise_for_status()
    print(r.json()['data'][0])


if __name__ == '__main__':
    main()
