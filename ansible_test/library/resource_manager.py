#!/usr/bin/python3

# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: resource_manager
short_description: Manage cluster resources
description:
    Manage cluster resources.
author: "Maxim Olzeev"
options:
    name:
        description:
            Name of the resource.
        required: true
        type: str
    description:
        description:
            Description of the resource
        required: false
        type: str
    op_type:
        description:
            Create/delete
        required: false
        type: str
        choices: ['create', 'delete', 'manage']
        default: 'create'
    operations:
    description: List of operations for the resource.
    type: list
    elements: dict
    suboptions:
      action:
        description: Operation name (start, stop, monitor, promote, demote).
        type: str
        required: true
      interval:
        description: Operation interval (e.g., '10s', '5m').
        type: str
        default: '0s'
      timeout:
        description: Operation timeout (e.g., '20s', '60s').
        type: str
      on_fail:
        description: Action on failure.
        type: str
        choices: ['ignore', 'block', 'restart', 'fail', 'stop', 'demote']
    type:
        description:
            Type of the resource
        required: false
        choices: ["primitive", "promotable"]
        default: "primitive"
        type: str
    agent: 
        description:
            Provider of the resource
        required: false
        default: ["ocf:pacemaker:Dummy"]
        type: str
    
    meta_attrs:
        description:
            Meta attributes of the resource
        required: false
        type: dict
    instance_attrs:
        description:
            Instance attributed of the resource
        required: false
        type: dict
    desired_state:
        description: 
            Desired state of the resource
        required: false
        type: str
        choices: ['enabled', 'disabled']
        default: "enabled"
'''


import subprocess
import time
from ansible.module_utils.basic import AnsibleModule


def resource_exists(module, name): # check whether resource exists
    cmd = ['pcs', 'resource', 'show', name]
    
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return (res.returncode == 0):


def run_cmd(module, cmd):
    result = subprocess.run(
        cmd, 
        capture_output = True, 
        text=True, 
        check=False,
    )
    if result.returncode != 0:
        module.fail_json(
            msg=f"Command '{' '.join(cmd)}' failed!", 
            stdout=result.stdout, 
            stderr=result.stderr
        )
    return result

def create_resource(module):
    

def main():
    module_args = dict(
        name=dict(type='str', required=True), 
        description=dict(type='str', required=False), 
        op_type=dict(type='str', required=False, default='create', choices=['create', 'delete']), 
        type=dict(type='str', required=False, choices=["primitive", "promotable"], default='primitive'), 
        agent=dict(type='str', required=False, default='ocf:pacemaker:Dummy'), 
        meta_attrs=dict(type='dict', required=False), 
        instance_attrs=dict(type='dict', required=False), 
        desired_state=dict(type='str', choices=['enabled', 'disabled'], default='enabled')
    )

    module = AnsibleModule(
        argument_spec=module_args, 
        supports_check_mode=True, 
        required_if=[
            ('op_type', 'create', ['type', 'agent'])
        ]
    )

    res_name = module.params['name']
    op_type = module.params['op_type']
    
    res_exists = resource_exists(res_name)

    if op_type == 'create':
        if res_exists:
            module.exit_json(
                changed=False, 
                msg=f"Resource {res_name} already exists"
            )
        result = create_resource(module)
        module.exit_json(
            changed=True, 
            msg=f"Resource {res_name} created successfully", 
            stdout=result.stdout
        )
    else:
        if not res_exists:
            module.exit_json(
                changed=False, 
                msg=f"Resource {res_name} doesn't exist"
            )
        result = delete_resource(module)
        module.exit_json(
            changed=True, 
            msg=f"Resource {res_name} was deleted successfully"
            stdout=result.stdout
        )

if __name__ == '__main__':
    main()