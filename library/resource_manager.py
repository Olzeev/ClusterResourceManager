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
        default: "ocf:pacemaker:Dummy"
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
    state:
        description: 
            State of the resource
        required: false
        type: str
        choices: ['enabled', 'disabled']
        default: "enabled"
'''


EXAMPLES = r'''
- name: Create a primitive dummy resource
  resource_manager:
    name: test_res
    agent: ocf:heartbeat:Dummy
    state: present
'''

RETURN = r'''
changed:
  description: Whether the resource was changed.
  type: bool
  returned: always
msg:
  description: Output message from the operation.
  type: str
  returned: always
stdout:
  description: Standard output from pcs command.
  type: str
  returned: on success
stderr:
  description: Standard error from pcs command.
  type: str
  returned: on error
'''

import subprocess
import time
from ansible.module_utils.basic import AnsibleModule


def resource_exists(module): # check whether resource exists
    cmd = ['pcs', 'resource', 'status', module.params['name']]
    
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return (res.returncode == 0)


def run_cmd(module, cmd): # run pcs command
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
    res_type = module.params['type']
    cmd1 = ['pcs', 'resource', 'create', module.params['name'], f'ocf:pacemaker:{'Stateful' if res_type == 'promotable' else 'Dummy'}']
    
    res_state = module.params['state']
    if res_state == 'disabled':
        cmd.append('--disabled')    

    result = run_cmd(module, cmd1)
    
    if res_type == 'primitive':
        return result

    cmd2 = ['pcs', 'resource', 'promotable', module.params['name']]
    result = run_cmd(module, cmd2)
    return result


def delete_resource(module):
    cmd = ['pcs', 'resource', 'delete', module.params['name']]

    result = run_cmd(module, cmd)
    return result


def main():
    module_args = dict(
        name=dict(type='str', required=True), 
        op_type=dict(type='str', required=False, default='create', choices=['create', 'delete']), 
        type=dict(type='str', required=False, choices=["primitive", "promotable"], default='primitive'), 
        agent=dict(type='str', required=False, default='ocf:pacemaker:Dummy'), 
        meta_attrs=dict(type='dict', required=False), 
        instance_attrs=dict(type='dict', required=False), 
        state=dict(type='str', choices=['enabled', 'disabled'], default='enabled')
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
    
    res_exists = resource_exists(module)

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
    elif op_type == 'delete':
        if not res_exists:
            module.exit_json(
                changed=False, 
                msg=f"Resource {res_name} doesn't exist"
            )
        result = delete_resource(module)
        module.exit_json(
            changed=True, 
            msg=f"Resource {res_name} was deleted successfully",
            stdout=result.stdout
        )
    '''
    elif op_type == 'manage':
        if not res_exists:
            module.exit_json(
                changed=False,
                msg=f"Resource {res_name} doesn't exist"
            )
        result = manage_resource(module)
        module.exit_json(
            changed=True, 
            msg=f"Operations for resource {res_name} executed successfully"
            stdout=result.stdout
        )
    '''

if __name__ == '__main__':
    main()