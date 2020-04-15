import json
from pprint import pprint

import requests


def get_next_id():
    for i in range(1, 100):
        yield i


t_id_gen = get_next_id()
for i in range(1, 4):
    proj_name = f'project_{i}'
    create_project = requests.post('http://127.0.0.1:5000/projects', data=json.dumps({'name': proj_name}))
    if create_project.status_code == 201:
        print(f'Project {proj_name} created')
    for _ in range(1, 4):
        task_name = f'task_{next(t_id_gen)}'
        create_task = requests.post('http://127.0.0.1:5000/tasks', data=json.dumps({'name': task_name, 'project_id': i}))
        if create_task.status_code == 201:
            print(f'Task {task_name} created')

get_all_projects = requests.get('http://127.0.0.1:5000/projects')
print('All projects in repository')
pprint(get_all_projects.json())
get_all_tasks = requests.get('http://127.0.0.1:5000/tasks?project_id=1')
print('All tasks in repository for project with id 1')
pprint(get_all_tasks.json())

print('Updating project with id 1')
update_project = requests.patch('http://127.0.0.1:5000/projects/1', data=json.dumps({'name': 'project_updated_1'}))
print('Getting project with id 1 from repository')
get_project_by_id = requests.get('http://127.0.0.1:5000/projects/1')
pprint(get_project_by_id.json())
print('Deleting project with id 3 w/o cascade')
delete_project = requests.delete('http://127.0.0.1:5000/projects/3?cascade=0')
pprint(delete_project.content)
print('All projects in repository')
get_all_projects = requests.get('http://127.0.0.1:5000/projects')
pprint(get_all_projects.json())
print('Deleting project with id 2 with cascade')
delete_project = requests.delete('http://127.0.0.1:5000/projects/2?cascade=1')
pprint(delete_project.content)
print('All projects in repository')
get_all_projects = requests.get('http://127.0.0.1:5000/projects')
pprint(get_all_projects.json())

print('Trying to get task with id 7')
get_task = requests.get('http://127.0.0.1:5000/tasks/7')
pprint(get_task.json())
