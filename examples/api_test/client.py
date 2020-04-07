import requests

resp_1 = requests.get('http://127.0.0.1:5000/healthcheck/docker')
print(resp_1.status_code)
print(resp_1.content)
resp_2 = requests.get('http://127.0.0.1:5000/healthcheck/metadata')
print(resp_2.status_code)
print(resp_2.content)
resp_3 = requests.get('http://127.0.0.1:5000/healthcheck/artifact')
print(resp_3.status_code)
print(resp_3.content)