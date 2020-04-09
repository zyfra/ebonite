import json
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

#create project with error cases
create_project = requests.post('http://127.0.0.1:5000/projects', data=json.dumps({'name':'proj1'}))
print(create_project.status_code)
print(create_project.content)
create_project = requests.post('http://127.0.0.1:5000/projects', data=json.dumps({'name':'proj2'}))
print(create_project.status_code)
print(create_project.content)
create_project = requests.post('http://127.0.0.1:5000/projects', data=json.dumps({'name':'proj3'}))
print(create_project.status_code)
print(create_project.content)

create_project = requests.post('http://127.0.0.1:5000/projects', data=json.dumps({'asd':'aaaa'}))
print(create_project.status_code)
print(create_project.content)


create_project = requests.post('http://127.0.0.1:5000/projects', data=json.dumps({'name':'aaaa'}))
print(create_project.status_code)
print(create_project.content)

create_project = requests.post('http://127.0.0.1:5000/projects', data=json.dumps([{'name':'b'}, {'name':'a'}]))
print(create_project.status_code)
print(create_project.content)

get_all_projects = requests.get('http://127.0.0.1:5000/projects')
print(get_all_projects.status_code)
print(get_all_projects.content)

# Get, update, delete project
print('Get project')
get_project_by_id = requests.get('http://127.0.0.1:5000/projects/1')
print(get_project_by_id.status_code)
print(get_project_by_id.content)

print('Update project')
update_project = requests.patch('http://127.0.0.1:5000/projects/1',data=json.dumps({'name':'ddd'}))
print(update_project.status_code)
print(update_project.content)

print('Delete project')
delete_project = requests.delete('http://127.0.0.1:5000/projects/3?cascade=0')
print(delete_project.status_code)
print(delete_project.content)
