# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 13:06:19 2018

@author: Okada
"""

import os
import shutil
from multiprocessing import Process, Array
import string
import random
import datetime
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
pwd

SCRIPT_ENVM_NAME=`basename ${{SCRIPT_ENVM_PATH}}`
SCRIPT_EXEC_NAME=`basename ${{SCRIPT_EXEC_PATH}}`

aws s3 cp ${{SCRIPT_ENVM_PATH}} ${{SCRIPT_ENVM_NAME}} --only-show-errors
aws s3 cp ${{SCRIPT_EXEC_PATH}} ${{SCRIPT_EXEC_NAME}} --only-show-errors

source ${{SCRIPT_ENVM_NAME}}
df -h

{download_script}

# exec
{shell} ${{SCRIPT_EXEC_NAME}}

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
            f.write('export %s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i].replace("s3://", "/scratch/AWS_DATA/")))
        elif task_params["header"][i]["type"] == "output":
            f.write('export S3_%s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i]))
            f.write('export %s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i].replace("s3://", "/scratch/AWS_DATA/")))
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

def submit_task_ondemand(aws_instance, no):

    if aws_instance.set_ondemand_price(no):
        if aws_instance.run_instances_ondemand (no):
            (instance_id, exit_code, stop) = aws_instance.run_task(no)
            if instance_id != None:
                aws_instance.terminate_instances(instance_id, no)
                return (exit_code, instance_id)
        
    return (1, None)

def submit_task_spot(aws_instance, no):
    
    retry = False
    exit_code = 1
    instance_id = None
    
    for itype in aws_instance.aws_ec2_instance_type_list:
        aws_instance.task_param[no]["aws_ec2_instance_type"] = itype
        if not aws_instance.set_ondemand_price(no):
            continue
        if not aws_instance.set_spot_price(no):
            continue
                
        if aws_instance.run_instances_spot (no):
            (instance_id, exit_code, stop) = aws_instance.run_task(no)
            if stop:
                retry = True
                
            if instance_id != None:
                aws_instance.terminate_instances(instance_id, no)
                aws_instance.cancel_spot_instance_requests (no = no, instance_id = instance_id)
                if exit_code == 0:
                    break
    else:
        retry = True
    
    if aws_instance.retry_od == False:
        retry = False
    return (exit_code, instance_id, retry)

def _hour_delta(start_t, end_t):
    return (end_t - start_t).total_seconds()/3600.0
    
def _set_job_info(task_param, start_t, end_t, instance_id, exit_code):
    return {
        "Ec2instancetype": task_param["aws_ec2_instance_type"],
        "End": end_t,
        "ExitCode": exit_code,
        "InstanceId": instance_id,
        "OdPrice": task_param["od_price"],
        "Start": start_t,
        "Spot": task_param["spot"],
        "SpotAz": task_param["spot_az"],
        "SpotPrice": task_param["spot_price"],
        "WorkHours": _hour_delta(start_t, end_t),
    }

def _save_summary_file(job_summary):
    
    import json
    
    template = " + instance-type %s (%s) %.3f USD (%s: %.3f USD), running-time %.3f Hour"
    costs = 0.0
    items = []
    for job in job_summary["Jobs"]:
        wtime = _hour_delta(job["Start"], job["End"])
        
        if job["Spot"]:
            costs += job["SpotPrice"] * wtime
            items.append(template % (job["Ec2instancetype"], "spot", job["SpotPrice"], "od", job["OdPrice"], wtime))
        else:
            costs += job["OdPrice"] * wtime
            items.append(template % (job["Ec2instancetype"], "ondemand", job["OdPrice"], "spot", job["SpotPrice"], wtime))            
        
        job["Start"] = str(job["Start"])
        job["End"] = str(job["End"])
        
    message = "The cost of this job is %.3f USD. \n%s" % (costs, "\n".join(items))
    print (ecsub.tools.info_message (job_summary["ClusterName"], job_summary["No"], message))

    log_file = "%s/log/summary.%03d.log" % (job_summary["Wdir"], job_summary["No"]) 
    json.dump(job_summary, open(log_file, "w"), indent=4, separators=(',', ': '), sort_keys=True)
    
def submit_task(aws_instance, no, shared_code, spot):
    
    job_summary = {
        "AccountId": aws_instance.aws_accountid,
        "AmiId": aws_instance.aws_ami_id,
        "ClusterName": aws_instance.cluster_name,
        "ClusterArn": aws_instance.cluster_arn,
        "Ec2InstanceDiskSize": aws_instance.aws_ec2_instance_disk_size,
        "EcsTaskMemory": aws_instance.aws_ecs_task_memory,
        "EcsTaskVcpu": aws_instance.aws_ecs_task_vcpu,
        "End": None,
        "Image": aws_instance.image,
        "KeyName": aws_instance.aws_key_name,
        "LogGroupName": aws_instance.log_group_name,
        "No": no,
        "Region": aws_instance.aws_region,
        "S3RunSh": aws_instance.s3_runsh,
        "S3Script": aws_instance.s3_script,
        "S3Setenv": aws_instance.s3_setenv,
        "SecurityGroupId": aws_instance.aws_security_group_id,
        "Shell": aws_instance.shell,
        "Spot": aws_instance.spot,
        "Start": str(datetime.datetime.now()),
        "SubnetId": aws_instance.aws_subnet_id,
        "TaskDefinitionAn": aws_instance.task_definition_arn,
        "UseAmazonEcr": aws_instance.use_amazon_ecr,
        "Wdir": aws_instance.wdir,
        "Jobs":[]
    }
    
    if spot:
        start_t = datetime.datetime.now()
        (exit_code, instance_id, retry) = submit_task_spot(aws_instance, no)
        job_summary["Jobs"].append(_set_job_info(aws_instance.task_param[no], start_t, datetime.datetime.now(), instance_id, exit_code))
        
        if retry:
            start_t = datetime.datetime.now()
            aws_instance.task_param[no]["aws_ec2_instance_type"] = aws_instance.aws_ec2_instance_type_list[0]
            (exit_code, instance_id) = submit_task_ondemand(aws_instance, no)
            job_summary["Jobs"].append(_set_job_info(aws_instance.task_param[no], start_t, datetime.datetime.now(), instance_id, exit_code))
    else:
        start_t = datetime.datetime.now()        
        (exit_code, instance_id) = submit_task_ondemand(aws_instance, no)
        job_summary["Jobs"].append(_set_job_info(aws_instance.task_param[no], start_t, datetime.datetime.now(), instance_id, exit_code))
    
    job_summary["End"] = str(datetime.datetime.now())
    job_summary["SubnetId"] = aws_instance.aws_subnet_id
        
    _save_summary_file(job_summary)
    shared_code[no] = exit_code
    
def job_memory (itype_list):
    min_memory = 0
    for itype in itype_list:
        mem =  ecsub.aws_config.INSTANCE_TYPE[itype]["t.memory"] * 1000 - ecsub.aws_config.INSTANCE_TYPE[itype]["d.memory"]
        if min_memory == 0:
            min_memory = mem
        elif min_memory > mem:
            min_memory = mem
    return min_memory

def job_vcpu (itype_list):
    min_vcpu = 0
    for itype in itype_list:
        vcpu =  ecsub.aws_config.INSTANCE_TYPE[itype]["vcpu"]
        if min_vcpu == 0:
            min_vcpu = vcpu
        elif min_vcpu > vcpu:
            min_vcpu = vcpu
    return min_vcpu
    
def main(params):
    
    # set cluster_name
    params["cluster_name"] = params["task_name"]
    if params["cluster_name"] == "":
        params["cluster_name"] = os.path.splitext(os.path.basename(params["tasks"]))[0] \
            + '-' \
            + ''.join([random.choice(string.ascii_letters + string.digits) for i in range(5)])
            
    # check instance type and set task-memory, task-vpu
    if params["aws_ec2_instance_type"] != "":
        if params["aws_ec2_instance_type"] in ecsub.aws_config.INSTANCE_TYPE:
            if params["aws_ecs_task_memory"] == 0:
                params["aws_ecs_task_memory"] = job_memory ([params["aws_ec2_instance_type"]])
            else:
                params["aws_ecs_task_memory"] = params["aws_ecs_task_memory"] * 1000
                
            if params["aws_ecs_task_vcpu"] == 0:
                params["aws_ecs_task_vcpu"] = job_vcpu ([params["aws_ec2_instance_type"]])
            else:
                params["aws_ecs_task_vcpu"] = params["aws_ecs_task_vcpu"]
        else:
            print (ecsub.tools.error_message (params["cluster_name"], None, "instance-type %s is not defined in ecsub." % (params["aws_ec2_instance_type"])))
            return 1
            
    elif len(params["aws_ec2_instance_type_list"]) > 0:
        if not params["spot"]:
            print (ecsub.tools.error_message (params["cluster_name"], None, "--aws-ec2-instance-type-list option is not support with ondemand-instance mode."))
            return 1
        
        for itype in params["aws_ec2_instance_type_list"]:
            if not itype in ecsub.aws_config.INSTANCE_TYPE:
                print (ecsub.tools.error_message (params["cluster_name"], None, "instance-type %s is not supported in ecsub." % (itype)))
                return 1
        
        if params["aws_ecs_task_memory"] == 0:
            params["aws_ecs_task_memory"] = job_memory (params["aws_ec2_instance_type_list"])
        else:
            params["aws_ecs_task_memory"] = params["aws_ecs_task_memory"] * 1000
            
        if params["aws_ecs_task_vcpu"] == 0:
            params["aws_ecs_task_vcpu"] = job_vcpu (params["aws_ec2_instance_type_list"])
        else:
            params["aws_ecs_task_vcpu"] = params["aws_ecs_task_vcpu"]
            
    else:
        print (ecsub.tools.error_message (params["cluster_name"], None, "One of --aws-ec2-instance-type option and --aws-ec2-instance-type-list option is required."))
        return 1
    
    # read tasks file
    task_params = read_tasksfile(params["tasks"], params["cluster_name"])
    if task_params == None:
        return 1
    
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

    aws_instance = ecsub.aws.Aws_ecsub_control(params, len(task_params["tasks"]))
    
    # check task-param
    if not aws_instance.check_awsconfigure():
        return 1
    
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
            # and register-task-definition
            if aws_instance.create_cluster() and aws_instance.register_task_definition():
    
                # run instance and submit task
                process_list = []
                shared_code = Array('i', [0]*len(task_params["tasks"]))
                for i in range(len(task_params["tasks"])):
                    process = Process(target=submit_task, name="%s_%03d" % (params["cluster_name"], i), args=(aws_instance, i, shared_code, params["spot"]))
                    process.daemon == True
                    process.start()
                    process_list.append(process)
                
                for process in process_list:
                    process.join()
                
                aws_instance.clean_up()
                ecsub.metrics.entry_point(params["wdir"])
                
                #print (shared_code[:])
                # SUCCESS
                if [0] == list(set(shared_code[:])):
                    return 0
            
            else:
                aws_instance.clean_up()
            
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
        "aws_ec2_instance_type_list": args.aws_ec2_instance_type_list.replace(" ", "").split(","),
        "aws_ec2_instance_disk_size": args.disk_size,
        "aws_ecs_task_memory": args.memory,
        "aws_ecs_task_vcpu": args.vcpu,
        "aws_s3_bucket": args.aws_s3_bucket,
        "aws_security_group_id": args.aws_security_group_id,
        "aws_key_name": args.aws_key_name,
        "aws_subnet_id": args.aws_subnet_id,
        "spot": args.spot,
        "retry_od": args.retry_od,
        "set_cmd": "set -x",
    }
    return main(params)
    
if __name__ == "__main__":
    pass
