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
        required: true
        type: str
        choices: ['create', 'delete', 'enable', 'disable']
    operations:
        description: List of operations for the resource.
        type: list
        elements: dict
        suboptions:
            action:
                description: Operation name (start, stop, monitor, promote, unpromote).
                type: str
                required: true
            interval:
                description: Operation interval (e.g., '10s', '5m').
                type: str
                default: '0s'
            timeout:
                description: Operation timeout (e.g., '20s', '60s').
                type: str
                default: '60s'
            on_fail:
                description: Action on failure.
                type: str
                choices: ['ignore', 'block', 'restart', 'fail', 'stop', 'demote']
                default: 'ignore'
    
    agent:
        description:
            Agent of the resource
        required: false
        type: str

    meta_attrs:
        description:
            Meta attributes of the resource
        required: false
        type: dict
    instance_attrs:
        description:
            Instance attributes of the resource
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
    op_type: create
    type: primitive
    state: enabled
- name: Delete a resource
    resource_manager:
        name: test_res
        op_type: delete
- name: Enable resource
    resource_manager:
        name: test_res
        op_type: enable
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
    
    rc, stdout, stderr = module.run_command(cmd)
    return (rc == 0)


def run_cmd(module, cmd): # run pcs command
    rc, stdout, stderr = module.run_command(cmd)
    if rc != 0:
        module.fail_json(
            msg=f"Command '{' '.join(cmd)}' failed!", 
            stdout=stdout, 
            stderr=stderr
        )
    return (rc, stdout, stderr)

def add_operations(module):
    operations = module.params['operations']
    cmd = []
    if operations is None:
        return []
    for op in operations:
        cmd += [
            'op', 
            op['action'], 
            f"interval={op['interval']}", 
            f"timeout={op['timeout']}", 
            f"on-fail={op['on_fail']}"
        ]
    return cmd

def add_meta_attrs(module):
    cmd = ['meta']
    meta = module.params['meta_attrs']
    if meta is None:
        return []
    for el in meta.keys():
        cmd.append(f"{el}={meta[el]}")
    return cmd


def add_instance_attrs(module):
    cmd = []
    instance = module.params['instance_attrs']
    if instance is None:
        return []
    for el in instance.keys():
        cmd.append(f"{el}={instance[el]}")
    return cmd


def create_resource(module):
    if module.check_mode:
        module.exit_json(
            changed=True, 
            msg=f"Would create {module.params['state']} {module.params['type']} resource {module.params['name']} (check_mode)"
        )
    agent = module.params['agent']
    
    cmd1 = ['pcs', 'resource', 'create', module.params['name'], agent] \
        + add_instance_attrs(module) + add_meta_attrs(module) + add_operations(module)
    
    res_state = module.params['state']
    if res_state == 'disabled':
        cmd1.append('--disabled')    

    result = run_cmd(module, cmd1)
    
    if agent.split(':')[-1] == 'Stateful':
        cmd2 = ['pcs', 'resource', 'promotable', module.params['name']]
        result = run_cmd(module, cmd2)
    return result


def delete_resource(module):
    if module.check_mode:
        module.exit_json(
            changed=True, 
            msg=f"Would delete resource {module.params['name']} (check mode)"
        )
    cmd = ['pcs', 'resource', 'delete', module.params['name']]

    result = run_cmd(module, cmd)
    return result


def main():
    module_args = dict(
        name=dict(type='str', required=True), 
        op_type=dict(type='str', required=False, default='create', choices=['create', 'delete', 'enable', 'disable']), 
        agent=dict(type='str', required=False),
        operations=dict(type='list', elements='dict', required=False, 
            options=dict(
                action=dict(type='str', requires=True), 
                interval=dict(type='str', default='0s'), 
                timeout=dict(type='str', default='60s'), 
                on_fail=dict(type='str', choices=['ignore', 'block', 'restart', 'fail', 'stop', 'demote'], default='ignore')
            )),
        meta_attrs=dict(type='dict', required=False), 
        instance_attrs=dict(type='dict', required=False), 
        state=dict(type='str', choices=['enabled', 'disabled'], default='enabled'),
    )

    module = AnsibleModule(
        argument_spec=module_args, 
        supports_check_mode=True, 
        required_if=[
            ('op_type', 'create', ['agent'])
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
            stdout=result[1]
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
            stdout=result[1]
        )
    elif op_type == 'enable':
        if not res_exists:
            module.exit_json(
                changed=False, 
                msg=f"Resource {res_name} doesn't exist"
            )
        if module.check_mode:
            module.exit_json(
                changed=True, 
                msg=f"Would enable resource {res_name} (check mode)"
            )
        result = run_cmd(module, ['pcs', 'resource', 'enable', res_name])
        module.exit_json(
            changed=True, 
            msg=f"Resource {res_name} enabled successfully", 
            stdout=result[1]
        )
    elif op_type == 'disable':
        if not res_exists:
            module.exit_json(
                changed=False, 
                msg=f"Resource {res_name} doesn't exist"
            )
        if module.check_mode:
            module.exit_json(
                changed=True, 
                msg=f"Would disable resource {res_name} (check mode)"
            )
        result = run_cmd(module, ['pcs', 'resource', 'disable', res_name])
        module.exit_json(
            changed=True, 
            msg=f"Resource {res_name} disabled successfully", 
            stdout=result[1]
        )

if __name__ == '__main__':
    main()