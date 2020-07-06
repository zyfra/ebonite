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
    rv = client.post('/projects', json={'name': 'project_1'})
    assert rv.status_code == 201
    assert rv.json['name'] == 'project_1'


def test_projects__create_validation_error(client):
    rv = client.post('/projects', json={'not_name': 'project_1'})
    assert rv.status_code == 422


def test_projects__create_existing_project_error(client, create_project_1):
    rv = client.post('/projects', json={'name': 'project_1'})
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
    rv = client.patch('/projects/1', json={'name': 'project_new'})
    assert rv.status_code == 204

    rv = client.get('/projects/1')
    assert rv.json['name'] == 'project_new'


def test_projects__update_not_exist(client):
    rv = client.patch('/projects/1', json={'name': 'project_new'})
    assert rv.status_code == 400
    assert rv.json['errormsg'] == 'Project with id 1 does not exist'


def test_projects__update_validation_error(client):
    rv = client.patch('/projects/1', json={'not_name': 'project_new'})
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


def test_projects__with_tasks_error(client, create_task_1):
    rv = client.delete('/projects/1')
    assert rv.status_code == 400
    assert rv.json['errormsg'] == 'Project project_1 has foreign key and can not be deleted'


# TASKS
def test_tasks__create_ok(client, create_task_1):
    rv = client.get('/tasks/1')
    assert rv.json['name'] == 'task_1'


def test_tasks__create_project_not_exist(client):
    rv = client.post('/tasks', json={'name': 'task_1', 'project_id': 1})
    assert rv.status_code == 404
    assert rv.json['errormsg'] == 'Project with id 1 does not exist'


def test_tasks__create_validation_error(client, create_project_1):
    rv = client.post('/tasks', json={'name': 'task_1'})
    assert rv.status_code == 422

    rv = client.post('/tasks', json={'not_name': 1, 'project_id': 1})
    assert rv.status_code == 422

    rv = client.post('/tasks', json={'name': 1, 'project_id': 'not_id'})
    assert rv.status_code == 422


def test_tasks__get_tasks_ok(client, create_task_1, create_task_2):
    rv = client.get('/tasks?project_id=1')
    assert rv.status_code == 200
    tasks = rv.json
    assert len(tasks) == 2
    assert tasks[0]['name'] == 'task_1'
    assert tasks[1]['name'] == 'task_2'


def test_tasks__get_tasks_project_not_exist(client):
    rv = client.get('/tasks?project_id=1')
    assert rv.status_code == 404
    assert rv.json['errormsg'] == 'Project with id 1 does not exist'


def test_tasks__get_single_task_ok(client, create_task_1):
    rv = client.get('/tasks/1')
    assert rv.status_code == 200
    assert rv.json['name'] == 'task_1'


def test_tasks__get_single_task_not_exist(client):
    rv = client.get('/tasks/1')
    assert rv.status_code == 404
    assert rv.json['errormsg'] == 'Task with id 1 does not exist'


def test_tasks__update_ok(client, create_task_1):
    rv = client.patch('/tasks/1', json={'name': 'new_task', 'project_id': 1})
    assert rv.status_code == 204

    rv = client.get('/tasks/1')
    assert rv.json['name'] == 'new_task'


def test_tasks__update_non_existing_task_project(client, create_task_1):
    rv = client.patch('/tasks/1', json={'name': 'new_task', 'project_id': 2})
    assert rv.status_code == 404

    rv = client.patch('/tasks/2', json={'name': 'new_task', 'project_id': 1})
    assert rv.status_code == 404


def test_tasks__delete_ok(client, create_task_1):
    rv = client.get('/tasks/1')
    assert rv.json['name'] == 'task_1'
    rv = client.delete('/tasks/1?cascade=0')
    assert rv.status_code == 204


def test_tasks__delete_task_not_exist(client):
    rv = client.delete('/tasks/1')
    assert rv.status_code == 404


# def test_tasks__delete_cascade__ok
# todo: cascade task deletion

# Models
def test_models__get_artifact_ok(client, model_in_db):
    rv = client.get('/models/1/artifacts/model.pkl')
    assert rv.status_code == 200


def test_models__get_artifact_fail(client, model_in_db):
    rv = client.get('/models/100/artifacts/model.pkl')
    assert rv.status_code == 404
    rv = client.get('/models/1/artifacts/rofl.mao')
    assert rv.status_code == 404


def test_models__get_model_ok(client, model_in_db):
    rv = client.get('/models/1')
    assert rv.status_code == 200
    print(rv.json)
    assert rv.json['name'] == 'test_model'


def test_models__get_model_not_exist(client):
    rv = client.get('/models/1')
    assert rv.status_code == 404


def test_models__get_models_ok(client, model_in_db):
    rv = client.get('/models?task_id=1')
    assert rv.status_code == 200
    assert rv.json[0]['name'] == 'test_model'


def test_models__get_models_task_not_exist(client):
    rv = client.get('/models?task_id=15')
    assert rv.status_code == 404


def test_models__update_model_ok(client, model_in_db):
    rv = client.patch('/models/1', json={'name': 'new_model', 'task_id': 1})
    assert rv.status_code == 204
    rv = client.get('/models/1')
    assert rv.json['name'] == 'new_model'


def test_models__delete_model_ok(client, model_in_db):
    rv = client.delete('/models/1')
    assert rv.status_code == 204
    rv = client.get('/models/1')
    assert rv.status_code == 404

# TODO: Val tests together?

def test_environments__get_envs_ok(client, env_in_db):
    rv = client.get('/environments')
    assert rv.status_code == 200
    assert len(rv.json) == 1


def test_environments__get_env_ok(client, env_in_db):
    rv = client.get('/environments/1')
    assert rv.status_code == 200
    assert rv.json['name'] == 'test_env'


def test_environments__get_env_not_exist(client):
    rv = client.get('/environments/15')
    assert rv.status_code == 404


def test_environments__create_env_ok(client):
    rv = client.post('/environments', json={'name': 'test_env_2', 'params': {'host': 'localhost:1234',
                                                                             'type': 'ebonite.build.docker.DockerHost'}}
                     )
    assert rv.status_code == 201
    assert rv.json['name'] == 'test_env_2'


def test_environments__create_val_error(client):
    rv = client.post('/environments', json={'not_name': 'test_env_2', 'params': {'host': 'localhost:1234',
                                                                             'type': 'ebonite.build.docker.DockerHost'}}
                     )
    assert rv.status_code == 422

    rv = client.post('/environments', json={'name': 'test_env_2'})
    assert rv.status_code == 422


def test_environments__create_env_already_exist(client, env_in_db):
    rv = client.post('/environments', json={'name': 'test_env', 'params': {'host': 'localhost:1234',
                                                                             'type': 'ebonite.build.docker.DockerHost'}}
                     )
    assert rv.status_code == 400


def test_environments__update_env_ok(client, env_in_db):
    rv = client.patch('/environments/1', json={'name': 'new_env'})
    assert rv.status_code == 204

    rv = client.get('/environments/1')
    assert rv.json['name'] == 'new_env'


def test_environments__update_env_not_exist(client):
    rv = client.patch('/environments/1', json={'name': 'new_env'})
    assert rv.status_code == 404


def test_environments__delete_env_ok(client, env_in_db):
    rv = client.delete('/environments/1')
    assert rv.status_code == 204

    rv = client.get('/environaments/1')
    assert rv.status_code == 404

