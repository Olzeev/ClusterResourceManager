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
    constraint_type:
        description:
            Type of the constraint
        required: true
        type: str
        choices: ['order', 'colocation']
    action_1:
        description:
            Action for resource 1
        required: false
        type: str
        choices: ['start', 'stop', 'promote', 'demote']
    action_1_resource:
        desscription:
            Resource 1 name
        required: true
        type: str

    action_2:
        description:
            Action for resource 2
        required: false
        type: str
        choices: ['start', 'stop', 'promote', 'demote']
    action_2_resource:
        desscription:
            Resource 2 name
        required: true
        type: str
    
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
import xml.etree.ElementTree as ET

def constraint_exists(module): # check whether resource exists
    cns_name = module.params['name']
    if cns_name is not None:
        rc, stdout, stderr = module.run_command(['pcs', 'constraint', 'config', '--full'])
        return (rc != 0 or cns_name in stdout)
    rc, stdout, stderr = module.run_command(['pcs', 'cluster', 'cib'])
    root = ET.fromstring(stdout)

    cns_type = module.params['constraint_type']
    res1 = module.params["action_1_resource"]
    res2 = module.params["action_2_resource"]
    if cns_type == 'order':
        action1 = module.params['action_1']
        action2 = module.params['action_2']
        xpath = f".//rsc_order[@first='{res1}'][@then='{res2}'][@first-action='{action1}'][@then-action='{action2}']"
    else:
        action1 = module.params['action_1']
        if action1 is None:
            action1 = "Started"
        action2 = module.params['action_2']
        if action2 is None:
            action2 = "Started"
        xpath = f".//rsc_colocation[@rsc='{module.params["action_1_resource"]}'][@with-rsc='{module.params["action_2_resource"]}'][@rsc-role='{action1}'][@with-rsc-role='{action2}']"

        
    res = root.find(xpath)
    return (res is not None)


def run_cmd(module, cmd): # run pcs command
    rc, stdout, stderr = module.run_command(cmd)
    if rc != 0:
        module.fail_json(
            msg=f"Command '{' '.join(cmd)}' failed!", 
            stdout=result.stdout, 
            stderr=result.stderr
        )
    return (rc, stdout, stderr)


def create_constraint(module):
    cns_name = module.params['name']
    cns_type = module.params['constraint_type']
    action1 = module.params['action_1']
    action2 = module.params['action_2']
    res1 = module.params['action_1_resource']
    res2 = module.params['action_2_resource']
    cmd = []
    if cns_type == 'order':
        cmd = ['pcs', 'constraint', 'order', action1, res1, 'then', action2, res2]
    elif cns_type == 'colocation':
        cmd = ['pcs', 'constraint', 'colocation', 'add']
        if action1 is not None:
            cmd.append(action1)
        cmd += [res1, 'then']
        if action2 is not None:
            cmd.append(action2)
        cmd.append(res2)

    if cns_name is not None:
        cmd.append(f"id={module.params['name']}")

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
        constraint_type=dict(type='str', required=True),
        action_1=dict(type='str', required=False),
        action_2=dict(type='str', required=False),
        action_1_resource=dict(type='str', required=True),
        action_2_resource=dict(type='str', required=False),
    )

    module = AnsibleModule(
        argument_spec=module_args, 
        supports_check_mode=True, 
        required_if=[
            ('op_type', 'create', ['action_1_resource', 'action_2_resource']), 
            ('constraint_type', 'order', ['action_1', 'action_2']),
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
                msg=f"Constraint already exists"
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