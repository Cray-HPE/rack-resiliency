#!/usr/bin/python3
#
# MIT License
#
# (C) Copyright 2025 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

#This script is used to apply CEPH zoning
#The objective of CEPH zoning is to make sure data gets replicated at rack level, so there would not be data loss incase of a rack failure

import json
import subprocess
import re
import sys


def create_and_map_racks():
    #Create buckets for racks and add them to the hierarchy under root=default
    for racknum, (rack, nodes) in enumerate(positions_dict.items()):
        racknum = "rack" + str(racknum+1)
        print("Rack number is ", racknum)
    
        command1 = "ceph osd crush add-bucket "+racknum+" rack"
        print(command1)
        result = subprocess.run(command1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        print('Result for add-bucket command', result.returncode)
        print('Output for add-bucket command', result.stdout)
    
        command2 = "ceph osd crush move "+racknum+" root=default"
        print(command2)
        result = subprocess.run(command2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        print('Result for crush move command', result.returncode)
        print('Output for crush move command', result.stdout)
    
        #Move the storage hosts to the rack based on the discovered placement obtained from the input file
        print(nodes)
        for node in nodes:
            print(node)
            if re.match(r"^.*ncn-s00[0-9]$", node):
                print("Node is storage node")
                command3="ceph osd crush move "+node+" rack="+racknum
                print(command3)
                result = subprocess.run(command3, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
                print('Result for crush move command', result.returncode)
                print('Output for crush move command', result.stdout)

def create_and_apply_rules():
    #Create a CRUSH rule with Rack as the failure domain
    command4="ceph osd crush rule create-replicated replicated_rule_with_rack_failure_domain default rack"
    print(command4)
    result = subprocess.run(command4, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
    print('Result for rule creation command', result.returncode)
    print('Output for rule creation command', result.stdout)

    #Apply the above created rule to the CEPH pools
    command5="ceph osd pool ls"
    print(command5)
    result = subprocess.run(command5, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
    print('Result for pool listing command', result.returncode)
    ceph_pools = result.stdout.splitlines()
    print('Output for pool listing command', ceph_pools)
    for pool in ceph_pools:
        print(pool)
        command6="ceph osd pool set "+pool+" crush_rule replicated_rule_with_rack_failure_domain"
        print(command6)
        result = subprocess.run(command6, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        print('Result for pool setting with rule command', result.returncode)
        print('Output for pool setting with rule command', result.stdout)

def main():
    if len(sys.argv) != 2:
        print("Usage: python ceph_zoning.py <rack_placement file>")
        sys.exit(1)
    
    #Obtain the placement file as an input and load the JSON data
    file_path = sys.argv[1]
    with open(file_path, 'r') as file:
        positions = file.read()
    #positions = '{"x3000":["ncn-m001","ncn-w001","ncn-w004","ncn-w007","ncn-s001"],"x3001":["ncn-m002","ncn-w002","ncn-w006","ncn-s003"],"x3002":["ncn-m003","ncn-w003","ncn-w009","ncn-b005","ncn-s002"]}'
    print(positions)
    positions_dict = json.loads(positions)

    # Create buckets for rack and map hosts to racks
    create_and_map_racks()
    # Create CRUSH rule and apply it to pools
    create_and_apply_rules()

if __name__ == "__main__":
    main()
