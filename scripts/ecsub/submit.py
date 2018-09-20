# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 13:06:19 2018

@author: Okada
"""

import os
import shutil
from multiprocessing import Process
import string
import random
import ecsub.aws
import ecsub.tools
import ecsub.metrics

def read_tasksfile(tasks_file, cluster_name):
    
    tasks = []
    header = []

    for line in open(tasks_file).readlines():
        if header == []:
            for item in line.rstrip("\r\n").split("\t"):
                v = item.strip(" ").split(" ")
                if v[0] == "":
                    header.append({"type": "", "recursive": False, "name": ""})
                
                elif v[0].lower() == "--env":
                    header.append({"type": "env", "recursive": False, "name": v[-1]})
                elif v[0].lower() == "--input-recursive":
                    header.append({"type": "input", "recursive": True, "name": v[-1]})
                elif v[0].lower() == "--input":
                    header.append({"type": "input", "recursive": False, "name": v[-1]})
                elif v[0].lower() == "--output-recursive":
                    header.append({"type": "output", "recursive": True, "name": v[-1]})
                elif v[0].lower() == "--output":
                    header.append({"type": "output", "recursive": False, "name": v[-1]})
                else:
                    print (ecsub.tools.error_message (cluster_name, None, "type %s is not support." % (v[0])))
                    return None
            continue
        
        tasks.append(line.rstrip("\r\n").split("\t"))

    return {"tasks": tasks, "header": header}


def write_runsh(task_params, runsh, shell):
   
    run_template = """set -ex

SCRIPT_ENVM_NAME=`basename ${{SCRIPT_ENVM_PATH}}`
SCRIPT_EXEC_NAME=`basename ${{SCRIPT_EXEC_PATH}}`

aws s3 cp ${{SCRIPT_ENVM_PATH}} /${{SCRIPT_ENVM_NAME}} --only-show-errors
aws s3 cp ${{SCRIPT_EXEC_PATH}} /${{SCRIPT_EXEC_NAME}} --only-show-errors

source /${{SCRIPT_ENVM_NAME}}

{download_script}
df -h

# exec
{shell} /${{SCRIPT_EXEC_NAME}}

#if [ $? -gt 0 ]; then exit $?; fi

# upload
{upload_script}
"""

    dw_text = ""
    up_text = ""    
    for i in range(len(task_params["header"])):

        if task_params["header"][i]["type"] == "input":
            cmd_template = 'if test -n "${name}"; then aws s3 cp --only-show-errors {r_option} $S3_{name} ${name}; fi\n'
            r_option = ""
            if task_params["header"][i]["recursive"]:
                r_option = "--recursive"
            dw_text += cmd_template.format(
                r_option = r_option,
                name = task_params["header"][i]["name"])
            
        elif task_params["header"][i]["type"] == "output":
            cmd_template = 'if test -n "${name}"; then aws s3 cp --only-show-errors {r_option} ${name} $S3_{name}; fi\n'
            r_option = ""
            if task_params["header"][i]["recursive"]:
                r_option = "--recursive"
            up_text += cmd_template.format(
                r_option = r_option,
                name = task_params["header"][i]["name"])
            
    open(runsh, "w").write(run_template.format(
        shell = shell,
        download_script = dw_text,
        upload_script = up_text
    ))
    
def write_setenv(task_params, setenv, no):
   
    f = open(setenv, "w")
    
    for i in range(len(task_params["tasks"][no])):
        
        if task_params["header"][i]["type"] == "input":
            f.write('export S3_%s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i]))
            f.write('export %s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i].replace("s3://", "/AWS_DATA/")))
        elif task_params["header"][i]["type"] == "output":
            f.write('export S3_%s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i]))
            f.write('export %s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i].replace("s3://", "/AWS_DATA/")))
        elif task_params["header"][i]["type"] == "env":
            f.write('export %s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i]))
            
    f.close()

def upload_scripts(task_params, aws_instance, local_root, s3_root, script, cluster_name, shell):

    runsh = local_root + "/run.sh"
    s3_runsh = s3_root + "/run.sh"
    write_runsh(task_params, runsh, shell)
    aws_instance.s3_copy(runsh, s3_runsh, False)

    s3_setenv_list = []
    for i in range(len(task_params["tasks"])):
        setenv = local_root + "/setenv.%d.sh" % (i)
        s3_setenv = s3_root + "/setenv.%d.sh" % (i)
        write_setenv(task_params, setenv, i)
        aws_instance.s3_copy(setenv, s3_setenv, False)
        s3_setenv_list.append(s3_setenv)
        
    s3_script = s3_root + "/" + os.path.basename(script)
    aws_instance.s3_copy(script, s3_script, False)
    
    aws_instance.set_s3files(s3_runsh, s3_script, s3_setenv_list)
    
    return True

def submit_task(aws_instance, no):
    
    if aws_instance.run_instances(no):
        instance_id = aws_instance.run_task(no)
        if instance_id != None:
            aws_instance.terminate_instances(no, instance_id)
    
def main(params):
    
    # check instance type and set memory, vpu
    undefined = False
    if params["aws_ec2_instance_type"] in ecsub.aws_config.INSTANCE_TYPE:
        if params["aws_ecs_task_memory"] == 0:
            params["aws_ecs_task_memory"] = ecsub.aws_config.INSTANCE_TYPE[params["aws_ec2_instance_type"]]["memory"]
        if params["aws_ecs_task_vcpu"] == 0:
            params["aws_ecs_task_vcpu"] = ecsub.aws_config.INSTANCE_TYPE[params["aws_ec2_instance_type"]]["vcpu"]
    else:
        print (ecsub.tools.info_message (params["cluster_name"], None, "instance-type %s is not defined in ecsub." % (params["aws_ec2_instance_type"])))
        if params["aws_ecs_task_memory"] == 0:
            print (ecsub.tools.error_message (params["cluster_name"], None, "--memory option is required."))
            undefined = True

        if params["aws_ecs_task_vcpu"] == 0:
            print (ecsub.tools.error_message (params["cluster_name"], None, "--vcpu option is required."))
            undefined = True
            
    if undefined:
        return -1
    
    # read tasks file
    params["cluster_name"] = params["task_name"]
    if params["cluster_name"] == "":
        params["cluster_name"] = os.path.splitext(os.path.basename(params["tasks"]))[0] \
            + '-' \
            + ''.join([random.choice(string.ascii_letters + string.digits) for i in range(5)])

    task_params = read_tasksfile(params["tasks"], params["cluster_name"])
    if task_params == None:
        return -1
    
    if task_params["tasks"] == []:
        return 0
    
    subdir = params["cluster_name"]
    
    params["wdir"] = params["wdir"].rstrip("/") + "/" + subdir
    params["aws_s3_bucket"] = params["aws_s3_bucket"].rstrip("/") + "/" + subdir
    
    if os.path.exists (params["wdir"]):
        shutil.rmtree(params["wdir"])
        print (ecsub.tools.info_message (params["cluster_name"], None, "'%s' existing directory was deleted." % (params["wdir"])))
        
    os.makedirs(params["wdir"])
    os.makedirs(params["wdir"] + "/log")
    os.makedirs(params["wdir"] + "/conf")
    os.makedirs(params["wdir"] + "/script")

    aws_instance = ecsub.aws.Aws_ecsub_control(params)
    
    # check task-param
    if aws_instance.check_inputfiles(task_params):

        # tasts to scripts and upload S3
        upload_scripts(task_params, 
                       aws_instance, 
                       params["wdir"] + "/script", 
                       params["aws_s3_bucket"].rstrip("/") + "/script",
                       params["script"],
                       params["cluster_name"],
                       params["shell"])

        try:
            # create-cluster
            # register-task-definition
            if aws_instance.create_cluster() and aws_instance.register_task_definition():
    
                # run instance and submit task
                process_list = []
                for i in range(len(task_params["tasks"])):
                    process = Process(target=submit_task, name="%s_%03d" % (params["cluster_name"], i), args=(aws_instance, i))
                    process.daemon == True
                    process.start()
                    process_list.append(process)
                
                for process in process_list:
                    process.join()
    
            aws_instance.clean_up()
            ecsub.metrics.entry_point(params["wdir"])
            
            return 0
            
        except Exception as e:
            print (ecsub.tools.error_message (params["cluster_name"], None, e))
            aws_instance.clean_up()
            
        except KeyboardInterrupt:
            aws_instance.clean_up()
    
    return 1
    
def entry_point(args, unknown_args):
    
    params = {
        "wdir": args.wdir,
        "image": args.image,
        "shell": args.shell,
        "use_amazon_ecr": args.use_amazon_ecr,
        "script": args.script,
        "tasks": args.tasks,
        "task_name": args.task_name,
        "aws_ec2_instance_type": args.aws_ec2_instance_type,
        "aws_ec2_instance_disk_size": args.disk_size,
        "aws_ecs_task_memory": args.memory,
        "aws_ecs_task_vcpu": args.vcpu,
        "aws_s3_bucket": args.aws_s3_bucket,
        "aws_security_group_id": args.aws_security_group_id,
        "aws_key_name": args.aws_key_name,
        "aws_subnet_id": args.aws_subnet_id,
        "set_cmd": "set -x",
    }
    return main(params)
    
if __name__ == "__main__":
    pass
