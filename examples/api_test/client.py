import requests

#Healthchecks
docker_healthcheck = requests.get('http://127.0.0.1:5000/healthcheck/docker')
print(docker_healthcheck.status_code)
print(docker_healthcheck.content)
metadata_healthcheck = requests.get('http://127.0.0.1:5000/healthcheck/metadata')
print(metadata_healthcheck.status_code)
print(metadata_healthcheck.content)
artifact_healthcheck = requests.get('http://127.0.0.1:5000/healthcheck/artifact')
print(artifact_healthcheck.status_code)
print(artifact_healthcheck.content)

get_all_projects = requests.get('http://127.0.0.1:5000/projects')
print(get_all_projects.status_code)
print(get_all_projects.content)

get_project_by_id = requests.get('http://127.0.0.1:5000/projects/1')
print(get_project_by_id.status_code)
print(get_project_by_id.content)