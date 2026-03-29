#!/usr/bin/python3

# -*- coding: utf-8 -*-

DOCUMENTATION = r'''
---
module: constraint_manager
short_description: Manage cluster constraints
description:
    Manage cluster constraints.
author: "Maxim Olzeev"
options:
    op_type:
        description:
            Create/delete
        required: true
        choices: ['create', 'delete']
    name:
        description:
            Identifier of the constraint.
        required: false
        type: str
    actions:
        description:
            Actions for each resource
        required: false
        type: list
        elements: dict
        suboptions:
            action_name:
                description: name of the action 
                type: str
                required: true
                choices: ['start', 'stop', 'promote', 'demote']
            res_name:
                description: name of the resource to execute action 
                type: str
                required: true
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
  description: Whether the constraint was changed.
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


def constraint_exists(module): # check whether resource exists
    cns_name = module.params['name']
    if cns_name is None:
        return False
    cmd = ['pcs', 'constraint', 'config', '--full']
    
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        return False
    
    return (f"id: {cns_name}" in res.stdout)


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


def create_constraint(module):
    cns_name = module.params['name']
    cmd = ['pcs', 'constraint', 'order']
    if cns_name is not None:
        cmd.append(f"id={module.params['name']}")
    actions = module.params['actions']
    seq = []
    for action in actions:
        seq.append(f"{action['action_name']} {action['res_name']}")
    seq = " then ".join(seq)
    cmd += seq.split(' ')

    result = run_cmd(module, cmd)
    return result

def delete_constraint(module):
    cmd = ['pcs', 'constraint', 'delete', module.params['name']]

    result = run_cmd(module, cmd)
    return result


def main():
    module_args = dict(
        op_type=dict(type='str', required=True, choices=['create', 'delete']), 
        name=dict(type='str', required=False),  
        actions=dict(type='list', elements='dict', required=False)
    )

    module = AnsibleModule(
        argument_spec=module_args, 
        supports_check_mode=True, 
        required_if=[
            ('op_type', 'create', ['actions']), 
            ('op_type', 'delete', ['name'])
        ]
    )
    cns_name = module.params['name']
    op_type = module.params['op_type']
    
    cns_exists = constraint_exists(module)

    if op_type == 'create':
        if cns_exists:
            module.exit_json(
                changed=False, 
                msg=f"Constraint {cns_name} already exists"
            )
        result = create_constraint(module)
        module.exit_json(
            changed=True, 
            msg=f"Constraint {cns_name} created successfully", 
            stdout=result.stdout
        )
    elif op_type == 'delete':
        if not cns_exists:
            module.exit_json(
                changed=False, 
                msg=f"Constraint {cns_name} doesn't exist"
            )
        result = delete_constraint(module)
        module.exit_json(
            changed=True, 
            msg=f"Constraint {cns_name} was deleted successfully",
            stdout=result.stdout
        )

if __name__ == '__main__':
    main()