from cloudify import ctx
from cloudify import manager
from cloudify.state import ctx_parameters as inputs
import subprocess
import os
import glob


credentials = {
    'manager_host': inputs['manager_host'],
    'repo_path': inputs['repo_path'],
    'github_token': inputs['github_token'],
    'repo_url': inputs['repo_url'],
    'branch_name': inputs['branch_name']
}

entity_template = '''
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: {blueprint_id}
  description: {description}
  tags:
    - tosca
    - cloudify
  links:
    - url: http://{manager_ip}/console/page/blueprints_blueprint/{blueprint_id}?c=%5B%7B%22context%22%3A%7B%7D%7D%2C%7B%22context%22%3A%7B%22blueprintId%22%3A%22{blueprint_id}%22%7D%2C%22pageName%22%3A%22{blueprint_id}%22%7D%5D#!
      title: Deploy component
      icon: user
spec:
  type: service
  lifecycle: production
  owner: team-a
'''

entity_template_ms = '''
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: {blueprint_id}
  description: {description}
  annotations:
    backstage.io/kubernetes-id: {blueprint_id}
  tags:
    - tosca
    - cloudify
  links:
    - url: http://{manager_ip}/console/page/blueprints_blueprint/{blueprint_id}?c=%5B%7B%22context%22%3A%7B%7D%7D%2C%7B%22context%22%3A%7B%22blueprintId%22%3A%22{blueprint_id}%22%7D%2C%22pageName%22%3A%22{blueprint_id}%22%7D%5D#!
      title: Deploy component
      icon: user
    - url: http://{repo_ip}/projects/CLOUD/repos/nodejs-test/browse
      title: {repo_name} repo
      icon: docs
spec:
  type: service
  lifecycle: production
  owner: team-a
'''

def _get_client():
    return manager.get_rest_client()

def execute_and_wait(commands_list, path):
    for command in commands_list:
        process = subprocess.Popen(command, cwd=path)
        process.wait()

def add_file_change(filename, repo_path):
    execute_and_wait( [
        ['git', 'add', filename],
    ], repo_path
    )

def push_changes(repo_path, github_token, repo_url, branch_name, **kwargs):
    execute_and_wait( [
        ['git', 'pull'],
        ['git', 'add', '.'],
        ['git', 'commit', '-m', 'Apply blueprint modification'],
        ['git', 'push', 'https://' + github_token + '@' + repo_url, branch_name]
    ], repo_path
    )

def clean_repo(repo_path):
    for i in glob.glob(os.path.join(repo_path, '*.yaml')):
        os.remove(i)
    execute_and_wait( [
        ['git', 'add', '--all', '.'],
    ], repo_path
    )

def create_entity_file(blueprint, manager_host, repo_path, **kwargs):
    template_params= {
        "blueprint_id": blueprint.id,
        "manager_ip": manager_host,
        "description": blueprint.description or "Cloudify blueprint"
    }
    entity_definition = entity_template.format(**template_params)
    blueprint_entity_file_name = '{}.yaml'.format(blueprint.id)
    entity_file_path = os.path.join(repo_path, blueprint_entity_file_name)
    with open(entity_file_path, "w") as file:
        file.write(entity_definition)
    add_file_change(blueprint_entity_file_name, repo_path)

def ms1_v1_entity_file(repo_path, **kwargs):
    template_params= {
        "blueprint_id": "ms1-v1",
        "manager_ip": "44.194.70.211",
        "repo_ip": "44.194.70.211:7990",
        "description": "Microservice 1 blueprint",
        "repo_name": "MS1"
    }
    entity_definition = entity_template_ms.format(**template_params)
    blueprint_entity_file_name = 'ms1-v1.yaml'
    entity_file_path = os.path.join(repo_path, blueprint_entity_file_name)
    with open(entity_file_path, "w") as file:
        file.write(entity_definition)
    add_file_change(blueprint_entity_file_name, repo_path)


client = _get_client()

if inputs['clean_repo']:
    clean_repo(credentials['repo_path'])

for blueprint in client.blueprints.list():
    if blueprint.id != ctx.blueprint.id:
        create_entity_file(blueprint, **credentials)

ms1_v1_entity_file(**credentials)

push_changes(**credentials)
