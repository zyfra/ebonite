import json


# HEALTHCHECKS
def test_healthchecks__docker_ok(client):
    rv = client.get('/healthchecks/docker')
    assert rv.status_code == 200
    assert rv.json == {'msg': 'Docker daemon is healthy'}


def test_healthchecks__meta_ok(client):
    rv = client.get('/healthchecks/metadata')
    assert rv.status_code == 200
    assert rv.json == {'msg': 'Metadata repository is healthy'}


def test_healthchecks__artifact_ok(client):
    rv = client.get('/healthchecks/artifact')
    assert rv.status_code == 200
    assert rv.json == {'msg': 'Artifact repository is healthy'}


# PROJECTS
def test_projects__create_ok(client):
    rv = client.post('/projects', data=json.dumps({'name': 'project_1'}))
    assert rv.status_code == 201
    assert rv.json['name'] == 'project_1'


def test_projects__create_validation_error(client):
    rv = client.post('/projects', data=json.dumps({'not_name': 'project_1'}))
    assert rv.status_code == 422


def test_projects__create_existing_project_error(client, create_project_1):
    rv = client.post('/projects', data=json.dumps({'name': 'project_1'}))
    assert rv.status_code == 400
    assert rv.json['errormsg'] == 'Project with name project_1 already exists'


def test_projects__get_all_ok(client, create_project_1, create_project_2):
    rv = client.get('/projects')
    assert rv.status_code == 200

    projects = rv.json
    assert len(projects) == 2
    assert projects[0]['name'] == 'project_1'
    assert projects[1]['name'] == 'project_2'


def test_projects__get_one_ok(client, create_project_1):
    rv = client.get('/projects/1')
    assert rv.status_code == 200
    assert rv.json['name'] == 'project_1'
    assert rv.json['id'] == 1


def test_projects__get_one_not_exist(client):
    rv = client.get('/projects/1')
    assert rv.status_code == 404
    assert rv.json['errormsg'] == 'Project with id 1 does not exist'


def test_projects__update_ok(client, create_project_1):
    rv = client.patch('/projects/1', data=json.dumps({'name': 'project_new'}))
    assert rv.status_code == 204

    rv = client.get('/projects/1')
    assert rv.json['name'] == 'project_new'


def test_projects__update_not_exist(client):
    rv = client.patch('/projects/1', data=json.dumps({'name': 'project_new'}))
    assert rv.status_code == 400
    assert rv.json['errormsg'] == 'Project with id 1 does not exist'


def test_projects__update_validation_error(client):
    rv = client.patch('/projects/1', data=json.dumps({'not_name': 'project_new'}))
    assert rv.status_code == 422


def test_projects__delete_ok(client, create_project_1):
    rv = client.delete('/projects/1')
    assert rv.status_code == 204

    rv = client.get('/projects/1')
    assert rv.status_code == 404


def test_projects__delete_not_existing_project(client):
    rv = client.delete('/projects/1')
    assert rv.status_code == 404
    assert rv.json['errormsg'] == 'Project with id 1 does not exist'


def test_projects__with_tasks_error(client, create_tasK_1):
    rv = client.delete('/projects/1')
    assert rv.status_code == 400
    assert rv.json['errormsg'] == 'Project project_1 has foreign key and can not be deleted'


# TASKS
def test_tasks__create_ok(client, create_tasK_1):
    rv = client.get('/tasks/1')
    assert rv.json['name'] == 'task_1'


def test_tasks__create_project_not_exist(client):
    rv = client.post('/tasks', data=json.dumps({'name': 'task_1', 'project_id': 1}))
    assert rv.status_code == 404
    assert rv.json['errormsg'] == 'Project with id 1 does not exist'
