# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 13:06:19 2018

@author: Okada
"""

import boto3
import os
import shutil
import threading
import string
import random
import datetime
import time
import json
import ecsub.aws
import ecsub.aws_config
import ecsub.tools
import ecsub.metrics

def read_tasksfile(tasks_file, cluster_name):
    
    tasks = []
    header = []

    for line in open(tasks_file).readlines():
        text = line.rstrip("\r\n")
        if len(text.rstrip()) == 0:
            continue
        if header == []:
            if text.startswith("#"):
                continue
            for item in text.split("\t"):
                v = item.strip(" ").split(" ")
                if v[0] == "":
                    header.append({"type": "", "recursive": False, "name": ""})
                
                elif v[0].lower() == "--env":
                    header.append({"type": "env", "recursive": False, "name": v[-1]})
                elif v[0].lower() == "--secret-env":
                    header.append({"type": "secret-env", "recursive": False, "name": v[-1]})
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
        
        items = text.split("\t")
        for i in range(len(items)):
            if header[i]["type"] in ["input", "output"]:
                if items[i] == "":
                    continue
                if not items[i].startswith("s3://"):
                    print (ecsub.tools.error_message(cluster_name, None, "'%s' is invalid S3 path." % (items[i])))
                    return None
            
        tasks.append(items)

    return {"tasks": tasks, "header": header}


def write_runsh(task_params, runsh, shell, is_request_payer):
   
    run_template = """set -ex
pwd

SCRIPT_SETENV_NAME=`basename ${{SCRIPT_SETENV_PATH}}`
SCRIPT_RUN_NAME=`basename ${{SCRIPT_RUN_PATH}}`
SCRIPT_DOWNLOADER_NAME=`basename ${{SCRIPT_DOWNLOADER_PATH}}`
SCRIPT_UPLOADER_NAME=`basename ${{SCRIPT_UPLOADER_PATH}}`

aws s3 cp {option} ${{SCRIPT_SETENV_PATH}} ${{SCRIPT_SETENV_NAME}} --only-show-errors
aws s3 cp {option} ${{SCRIPT_RUN_PATH}} ${{SCRIPT_RUN_NAME}} --only-show-errors
aws s3 cp {option} ${{SCRIPT_DOWNLOADER_PATH}} ${{SCRIPT_DOWNLOADER_NAME}} --only-show-errors
aws s3 cp {option} ${{SCRIPT_UPLOADER_PATH}} ${{SCRIPT_UPLOADER_NAME}} --only-show-errors

source ${{SCRIPT_SETENV_NAME}}
df -h

{shell} ${{SCRIPT_DOWNLOADER_NAME}}

# run main script
{shell} ${{SCRIPT_RUN_NAME}}

#if [ $? -gt 0 ]; then exit $?; fi

# upload
{shell} ${{SCRIPT_UPLOADER_NAME}}
"""
    option = ""
    if is_request_payer:
        option = "--request-payer requester"
        
    open(runsh, "w").write(run_template.format(
        shell = shell,
        option = option
    ))
    
def write_s3_scripts(task_params, payer_buckets, setenv, downloader, uploader, no):
   
    sec_env_text = """set -e
set +x
cat << EOF > ./ecsub_json_query.py
import json, sys
print(json.loads(sys.argv[1])["Plaintext"])
EOF

decrypt () {
    echo $1 | base64 -d > ./ecsub_encrypted.txt
    response=$(aws kms decrypt --ciphertext-blob fileb://ecsub_encrypted.txt)
    echo $(python ./ecsub_json_query.py "$response" | base64 -d)
}
"""
    env_text = "set -x\n"
    dw_text = "set -x\n"
    up_text = "set -x\n"
    
    for i in range(len(task_params["tasks"][no])):
        
        if task_params["header"][i]["type"] == "env":
            env_text += 'export %s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i])
            continue
        
        if task_params["header"][i]["type"] == "secret-env":
            sec_env_text += 'export %s=$(decrypt "%s")\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i])
            continue
                
        s3_path = task_params["tasks"][no][i]
        scratch_path = task_params["tasks"][no][i].replace("s3://", "/scratch/AWS_DATA/")
    
        env_text += 'export S3_%s="%s"\n' % (task_params["header"][i]["name"], s3_path)
        env_text += 'export %s="%s"\n' % (task_params["header"][i]["name"], scratch_path)
    
        if s3_path == "":
            continue
        
        cmd_template = 'aws s3 cp --only-show-errors {option} {path1} {path2}\n'
        
        option = []
        if task_params["header"][i]["recursive"]:
            option.append("--recursive")
        
        if ecsub.tools.is_request_payer_bucket(s3_path, payer_buckets):
            option.append("--request-payer requester")
        
        if task_params["header"][i]["type"] == "input":
            dw_text += cmd_template.format(option = " ".join(option), path1 = s3_path, path2 = scratch_path)
            
        elif task_params["header"][i]["type"] == "output":
            up_text += cmd_template.format(option = " ".join(option), path1 = scratch_path, path2 = s3_path)

    open(setenv, "w").write(sec_env_text + env_text)
    open(downloader, "w").write(dw_text)
    open(uploader, "w").write(up_text)

def check_bucket_location(cluster_name, task_params, work_bucket):
    
    def tasks_to_buckets(task_params, work_bucket):
        buckets_raw = []
        for task in task_params["tasks"]:
            for i in range(len(task)):
                if task_params["header"][i]["type"] in ["env", "secret-env"]:
                    continue
                bucket = task[i].replace("s3://", "").split("/")[0]
                buckets_raw.append(bucket)
                
        buckets = sorted(list(set(buckets_raw + [work_bucket.replace("s3://", "").split("/")[0]])))
        if "" in buckets:
            buckets.remove("")
        return buckets
    
    buckets = tasks_to_buckets(task_params, work_bucket)
    client = boto3.client("s3")
    regions = []
    for bucket in sorted(list(set(buckets))):
        try:
            response = client.get_bucket_location(Bucket=bucket)
        except Exception as e:
            print (ecsub.tools.error_message (cluster_name, None, "Failure get_bucket_location '%s'" % (bucket)))
            print (ecsub.tools.error_message (cluster_name, None, e))
            return None
        
        if response['LocationConstraint'] == None:
            print (ecsub.tools.warning_message (cluster_name, None, "Failure get_bucket_location '%s'" % (bucket)))
        else:
            regions.append(response['LocationConstraint'])
    
    current_session = boto3.session.Session()
    regions.append(current_session.region_name)
    regions = sorted(list(set(regions)))
    
    return regions

def check_inputfiles(cluster_name, task_params, payer_buckets, job_max = 10):
    
    def __tasks_to_pathes(cluster_name, task_params, payer_buckets):
        pathes = []
        keys = []
        for task in task_params["tasks"]:
            for i in range(len(task)):
                if task_params["header"][i]["type"] != "input":
                    continue
                
                bucket = task[i].replace("s3://", "").split("/")[0]
                key = task[i].replace("s3://", "").replace(bucket, "")
                if key.startswith("/"):
                    key = key[1:]
                if key == "":
                    continue
                
                if not [bucket, key] in keys:
                    keys.append([bucket, key])
                    pathes.append({
                        "bucket": bucket,
                        "key": key,
                        "request_payer": ecsub.tools.is_request_payer_bucket(task[i], payer_buckets),
                        "recursive": task_params["header"][i]["recursive"]
                    })
        return pathes
    
    def __check_file(ctx, thread_name, path):
        exit_code = 1
        try:
            if path["request_payer"]:
                response = boto3.client("s3").list_objects_v2(
                    Bucket=path["bucket"],
                    Prefix=path["key"],
                    MaxKeys=10,
                    RequestPayer='requester'
                )
            else:
                response = boto3.client("s3").list_objects_v2(
                    Bucket=path["bucket"],
                    Prefix=path["key"],
                    MaxKeys=10,
                )
            if path["recursive"]:
                if len(response['Contents']) > 0:
                    exit_code = 0
            else:
                for c in response['Contents']:
                    if c['Key'] == path["key"]:
                        exit_code = 0
            
            if exit_code == 1:
                print(ecsub.tools.error_message (cluster_name, None, "s3 path s3://%s/%s is invalid." % (path["bucket"], path["key"])))
            else:
                print(ecsub.tools.info_message (cluster_name, None, "check s3 path s3://%s/%s ...ok" % (path["bucket"], path["key"])))
        
        except Exception as e:
            print(ecsub.tools.error_message (cluster_name, None, "s3 path s3://%s/%s is invalid." % (path["bucket"], path["key"])))
            print(ecsub.tools.error_message (cluster_name, None, e))
        
        ctx[thread_name] = exit_code
    
    pathes = __tasks_to_pathes(cluster_name, task_params, payer_buckets)
    if len(pathes) == 0:
        return True
    
    import threading
    
    # run thread
    thread_list = []
    ctx = {}
    
    try:
        while len(thread_list) < len(pathes):
            alives = 0
            for th in thread_list:
                if th.is_alive():
                   alives += 1
                    
            jobs = job_max - alives
            submitted = len(thread_list)
            for i in range(jobs):
                no = i + submitted
                if no >= len(pathes):
                    break
    
                thread_name = "thread_%03d" % (no)
                th = threading.Thread(
                    target = __check_file, 
                    name = thread_name, 
                    args = ((ctx, thread_name, pathes[no]))
                )
                th.daemon == True
                th.start()
                
                thread_list.append(th)
                
        exitcodes = []
        for th in thread_list:
            th.join()
            exitcodes.append(ctx[th.getName()])
    
        # SUCCESS?
        if [0] == list(set(exitcodes)):
            print(ecsub.tools.info_message (cluster_name, None, "success s3 path check"))
            return True
        else:
            print(ecsub.tools.error_message (cluster_name, None, "failure s3 path check"))
            
    except Exception as e:
        print(ecsub.tools.error_message (cluster_name, None, e))
    except KeyboardInterrupt:
        print(ecsub.tools.error_message (cluster_name, None, "keyboardInterrupt"))
        
    return False

def upload_scripts(task_params, aws_instance, local_root, s3_root, script, cluster_name, shell, request_payer_bucket, not_verify_bucket):

    def upload_file (local_file, s3_path):
        s3 = boto3.resource('s3')
        bucket = s3_path.replace("s3://", "").split("/")[0]
        key = s3_path.replace("s3://" + bucket + "/", "")
        try:
            s3.Object(bucket, key).upload_file(local_file)
            print(ecsub.tools.info_message (cluster_name, None, "upload %s ---> s3://%s/%s" % (local_file, bucket, key)))
            return True
        except Exception as e:
            print(ecsub.tools.error_message (cluster_name, None, e))
        return False
    
    runsh = local_root + "/run.sh"
    s3_runsh = s3_root + "/run.sh"
    write_runsh(task_params, runsh, shell, ecsub.tools.is_request_payer_bucket(s3_root, request_payer_bucket))
    if not upload_file(runsh, s3_runsh):
        return False
    
    s3_setenv_list = []
    s3_downloader_list = []
    s3_uploader_list = []
    for i in range(len(task_params["tasks"])):
        setenv = local_root + "/setenv.%d.sh" % (i)
        s3_setenv = s3_root + "/setenv.%d.sh" % (i)
        downloader = local_root + "/downloader.%d.sh" % (i)
        s3_downloader = s3_root + "/downloader.%d.sh" % (i)
        uploader = local_root + "/uploader.%d.sh" % (i)
        s3_uploader = s3_root + "/uploader.%d.sh" % (i)
        
        write_s3_scripts(task_params, request_payer_bucket, setenv, downloader, uploader, i)
        if not upload_file(setenv, s3_setenv):
            return False
        if not upload_file(downloader, s3_downloader):
            return False
        if not upload_file(uploader, s3_uploader):
            return False
        
        s3_setenv_list.append(s3_setenv)
        s3_downloader_list.append(s3_downloader)
        s3_uploader_list.append(s3_uploader)
        
    s3_script = s3_root + "/userdata/" + os.path.basename(script)
    if not upload_file(script, s3_script):
        return False
    
    aws_instance.set_s3files(s3_runsh, s3_script, s3_setenv_list, s3_downloader_list, s3_uploader_list)
    return True

def _run_task(aws_instance, no, instance_id):
    
    system_error = False
    exit_code = 1
    task_log = None
    
    try:
        (exit_code, task_log) = aws_instance.run_task(no, instance_id)
        #print([exit_code, task_log])
        #if exit_code == 127:
        #    system_error = True
    
    except Exception as e:
        print (ecsub.tools.error_message (aws_instance.cluster_name, no, e))
    
    if aws_instance.flyaway and exit_code == 0:
        return (exit_code, task_log, system_error)
        
    aws_instance.terminate_instances(instance_id, no)
    
    return (exit_code, task_log, system_error)

def submit_task_ondemand(aws_instance, no):
    
    exit_code = 1
    task_log = None
    
    if not aws_instance.set_ondemand_price(no):
        return (exit_code, task_log)
    
    for i in range(3):
        instance_id = aws_instance.run_instances_ondemand (no)
        if instance_id == None:
            break
        
        (exit_code, task_log, system_error) = _run_task(aws_instance, no, instance_id)
            
        if system_error:
            continue
        else:
            return (exit_code, task_log)
        
    return (exit_code, task_log)

def submit_task_spot(aws_instance, no):

    exit_code = 1
    task_log = None
    
    for itype in aws_instance.aws_ec2_instance_type_list:
        
        aws_instance.task_param[no]["aws_ec2_instance_type"] = itype
        
        if not aws_instance.set_ondemand_price(no):
            continue
        if not aws_instance.set_spot_price(no):
            continue
        
        for i in range(3):
            instance_id = aws_instance.run_instances_spot (no)
            if instance_id == None:
                break

            (exit_code, task_log, system_error) = _run_task(aws_instance, no, instance_id)
            if aws_instance.flyaway and exit_code == 0:
                return (exit_code, task_log, False)
                
            aws_instance.cancel_spot_instance_requests (no = no, instance_id = instance_id)
                
            if system_error:
                continue
            elif exit_code == -1:
                break
            else:
                return (exit_code, task_log, False)
    
    return (exit_code, task_log, True)

def _hour_delta(start_t, end_t):
    return (end_t - start_t).total_seconds()/3600.0

def _set_job_info(task_param, start_t, end_t, task_log, exit_code):
    
    info = {
        "Ec2InstanceType": task_param["aws_ec2_instance_type"],
        "End": end_t,
        "ExitCode": exit_code,
        "LogLocal": task_log, 
        "OdPrice": task_param["od_price"],
        "Start": start_t,
        "Spot": task_param["spot"],
        "SpotAz": task_param["spot_az"],
        "SpotPrice": task_param["spot_price"],
        "WorkHours": _hour_delta(start_t, end_t),
        "InstanceId": "",
        "SubnetId": "",
        "Memory": 0,
        "vCpu": 0,
    }
    
    if task_log == None:
        return info
    
    task = json.load(open(task_log))["tasks"][0]
    info["InstanceId"] = task["instance_id"]
    info["SubnetId"] = task["subnet_id"]
    info["Memory"] = task["overrides"]["containerOverrides"][0]["memory"]
    info["vCpu"] = task["overrides"]["containerOverrides"][0]["cpu"]

    return info

def _save_summary_file(task_summary, print_cost):
    
    template_ec2 = " + instance-%d: $%.3f, instance-type %s (%s) $%.3f (if %s: $%.3f), running-time %.3f Hour"
    template_ebs = " + volume-%d: $%.3f, attached %d (GiB), $%.3f per GB-month of General Purpose SSD (gp2), running-time %.3f Hour"
    
    disk_size = task_summary["Ec2InstanceDiskSize"]
    
    total_cost = 0.0
    items = []
    i = 1
    for job in task_summary["Jobs"]:
        wtime = _hour_delta(job["Start"], job["End"])
        
        if job["Spot"]:
            cost = job["SpotPrice"] * wtime
            total_cost += cost
            
            items.append(template_ec2 % (i, cost, job["Ec2InstanceType"], "spot", job["SpotPrice"], "od", job["OdPrice"], wtime))
        else:
            cost = job["OdPrice"] * wtime
            total_cost += cost
            
            items.append(template_ec2 % (i, cost, job["Ec2InstanceType"], "ondemand", job["OdPrice"], "spot", job["SpotPrice"], wtime))
        
        cost = disk_size * task_summary["EbsPrice"] * wtime / 24 / 30
        total_cost += cost
        items.append(template_ebs % (i, cost, disk_size, task_summary["EbsPrice"], wtime))
        
        job["Start"] = ecsub.tools.datetime_to_standardformat(job["Start"])
        job["End"] = ecsub.tools.datetime_to_standardformat(job["End"])
        
        i += 1
        
    if print_cost:        
        message = "The cost of this task is $%.3f. \n%s" % (total_cost, "\n".join(items))
        print (ecsub.tools.info_message (task_summary["ClusterName"], task_summary["No"], message))
    
    task_summary["Price"] = "%.5f" % (total_cost)
    log_file = "%s/log/summary.%03d.log" % (task_summary["Wdir"], task_summary["No"]) 
    json.dump(task_summary, open(log_file, "w"), indent=4, separators=(',', ': '), sort_keys=True)
    
def submit_task(ctx, thread_name, aws_instance, no, task_params, spot):
    
    task_summary = {
        "AccountId": aws_instance.aws_accountid,
        "AmiId": aws_instance.aws_ami_id,
        "AutoKey": aws_instance.aws_key_auto,
        "ClusterName": aws_instance.cluster_name,
        "ClusterArn": aws_instance.cluster_arn,
        "Ec2InstanceDiskSize": aws_instance.disk_size,
        "EbsPrice": aws_instance.ebs_price,
        "End": None,
        "Image": aws_instance.image,
        "KeyName": aws_instance.aws_key_name,
        "LogGroupName": aws_instance.log_group_name,
        "No": no,
        "Price": 0,
        "Region": aws_instance.aws_region,
        "RequestPayerBucket": aws_instance.request_payer_bucket,
        "S3RunSh": aws_instance.s3_runsh,
        "S3Script": aws_instance.s3_script,
        "S3Setenv": aws_instance.s3_setenv[no],
        "SecurityGroupId": aws_instance.aws_security_group_id,
        "Shell": aws_instance.shell,
        "Spot": aws_instance.spot,
        "Start": ecsub.tools.datetime_to_standardformat(datetime.datetime.now()),
        "TaskDefinitionAn": aws_instance.task_definition_arn,
        "UseAmazonEcr": aws_instance.use_amazon_ecr,
        "Wdir": aws_instance.wdir,
        "Jobs":[]
    }
    #if aws_instance.flyaway == False:
    if True:
        _save_summary_file(task_summary, False)

    if spot:
        start_t = datetime.datetime.now()
        (exit_code, task_log, retry) = submit_task_spot(aws_instance, no)
        task_summary["Jobs"].append(_set_job_info(
            aws_instance.task_param[no], start_t, datetime.datetime.now(), task_log, exit_code
        ))
        
        if aws_instance.retry_od and retry:
            start_t = datetime.datetime.now()
            aws_instance.task_param[no]["aws_ec2_instance_type"] = aws_instance.aws_ec2_instance_type_list[0]
            (exit_code, task_log) = submit_task_ondemand(aws_instance, no)
            task_summary["Jobs"].append(_set_job_info(
                aws_instance.task_param[no], start_t, datetime.datetime.now(), task_log, exit_code
            ))
    else:
        start_t = datetime.datetime.now()
        (exit_code, task_log) = submit_task_ondemand(aws_instance, no)
        task_summary["Jobs"].append(_set_job_info(
            aws_instance.task_param[no], start_t, datetime.datetime.now(), task_log, exit_code
        ))
    
    task_summary["SubnetId"] = aws_instance.aws_subnet_id
    task_summary["End"] = ecsub.tools.datetime_to_standardformat(datetime.datetime.now())
    
    if aws_instance.flyaway == False:
        ecsub.metrics.entry_point(aws_instance.wdir, no)
        _save_summary_file(task_summary, True)
       
    #exit (exit_code)
    ctx[thread_name] = exit_code

import ctypes
def terminate_thread(thread):
    
    """Terminates a python thread from another thread.

    :param thread: a threading.Thread instance
    """
    if not thread.isAlive():
        return

    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread.ident), exc)
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
        
def main(params):
    def __split_param(text):
        formatted = text.strip()
        if formatted == "":
            return []
        return formatted.split(",")
            
    try:
        # set cluster_name
        params["cluster_name"] = params["task_name"]
        if params["cluster_name"] == "":
            params["cluster_name"] = os.path.splitext(os.path.basename(params["tasks"]))[0].replace(".", "_") \
                + '-' \
                + ''.join([random.choice(string.ascii_letters + string.digits) for i in range(5)])
                
        # "aws_ec2_instance_type"
        instance_type_list1 = __split_param(params["aws_ec2_instance_type"])
        instance_type_list2 = __split_param(params["aws_ec2_instance_type_list"])
        if len(instance_type_list1) == 0 and len(instance_type_list2) == 0:
            print (ecsub.tools.error_message (params["cluster_name"], None, "One of --aws-ec2-instance-type option and --aws-ec2-instance-type-list option is required."))
            return 1
        elif len(instance_type_list1) > 0 and len(instance_type_list2) > 0:
            print (ecsub.tools.error_message (params["cluster_name"], None, "--aws-ec2-instance-type option and --aws-ec2-instance-type-list option cannot be specified at the same time."))
            return 1
        
        if len(instance_type_list1) > 0:
            params["aws_ec2_instance_type_list"] = instance_type_list1
        else:
            params["aws_ec2_instance_type_list"] = instance_type_list2

        if len(params["aws_ec2_instance_type_list"]) > 1 and not params["spot"]:
            print (ecsub.tools.error_message (params["cluster_name"], None, "multiple instance-type option is not support with ondemand-instance mode."))
            return 1
        
        # "aws-subnet-id": 
        params["aws_subnet_id"] = __split_param(params["aws_subnet_id"])
        if len(params["aws_subnet_id"]) > 1 and not params["spot"]:
            print (ecsub.tools.error_message (params["cluster_name"], None, "multiple aws-subnet-id option is not support with ondemand-instance mode."))
            return 1

        # "request_payer_bucket": 
        params["request_payer_bucket"] = __split_param(params["request_payer_bucket"])

        # read tasks file
        task_params = read_tasksfile(params["tasks"], params["cluster_name"])
        if task_params == None:
            #print (ecsub.tools.error_message (params["cluster_name"], None, "task file is invalid."))
            return 1
        
        if task_params["tasks"] == []:
            print (ecsub.tools.info_message (params["cluster_name"], None, "task file is empty."))
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

        # disk-size
        if params["disk_size"] < 0:
            print (ecsub.tools.error_message (params["cluster_name"], None, "disk-size %d is smaller than expected size 0GB." % (params["disk_size"])))
            return 1
            
        # Adding requested disk size to the default EBS size of Amazon Linux 2
        # AMI to be consistent with the previous versions of ecsub using
        # Amazon Linux 1
        params["disk_size"] += 30

        aws_instance = ecsub.aws.Aws_ecsub_control(params, len(task_params["tasks"]))
        
        # check task-param
        if not aws_instance.check_awsconfigure():
            return 1

        # check s3-files path
        if params["not_verify_bucket"] == False:
            regions = check_bucket_location(params["cluster_name"], task_params, params["aws_s3_bucket"])
            if regions == None:
                return 1
            if len(regions) > 1:
                if params["ignore_location"]:
                    print (ecsub.tools.warning_message (params["cluster_name"], None, "your task uses multipule regions '%s'." % (",".join(regions))))
                else:
                    print (ecsub.tools.error_message (params["cluster_name"], None, "your task uses multipule regions '%s'." % (",".join(regions))))
                    return 1
                
            if not check_inputfiles(params["cluster_name"], task_params, params["request_payer_bucket"], params["processes_file_check"]):
                return 1
        
        # write task-scripts, and upload to S3
        local_script_dir = params["wdir"] + "/script"
        s3_script_dir = params["aws_s3_bucket"].rstrip("/") + "/script"
        if not upload_scripts(
            task_params, 
            aws_instance, 
            local_script_dir, 
            s3_script_dir,
            params["script"],
            params["cluster_name"],
            params["shell"],
            params["request_payer_bucket"],
            params["not_verify_bucket"]
         ):
            print (ecsub.tools.error_message (params["cluster_name"], None, "failure upload files to s3 bucket: %s." % (params["aws_s3_bucket"])))
            return 1
        
        # Ebs Price
        if not aws_instance.set_ebs_price ():
            return 1
        
    except KeyboardInterrupt:
        print ("KeyboardInterrupt")
        return 1
    
    # run purocesses
    thread_list = []
    ctx = {}
    
    try:
        # create-cluster
        # and register-task-definition
        if not aws_instance.create_cluster():
            aws_instance.clean_up()
            return 1
        if not aws_instance.register_task_definition():
            aws_instance.clean_up()
            return 1
        
        while len(thread_list) < len(task_params["tasks"]):
            alives = 0
            for th in thread_list:
                if th.is_alive():
                   alives += 1
                    
            jobs = params["processes"] - alives
            submitted = len(thread_list)
            
            for i in range(jobs):
                no = i + submitted
                if no >= len(task_params["tasks"]):
                    break

                thread_name = "%s_%03d" % ("thread", no)
                th = threading.Thread(
                        target = submit_task, 
                        name = thread_name, 
                        args = ((ctx, thread_name, aws_instance, no, task_params, params["spot"]))
                )
                th.daemon == True
                th.start()
                
                thread_list.append(th)
                
                time.sleep(5)
            
            time.sleep(5)
        
        exitcodes = []
        for th in thread_list:
            th.join()
            exitcodes.append(ctx[th.getName()])
        
        if params["flyaway"] == False:
            aws_instance.clean_up()
            
        # SUCCESS?
        if [0] == list(set(exitcodes)):
            print ("ecsub completed successfully!")
            return 0
        
    except Exception as e:
        print (e)
        print (ecsub.tools.important_message (params["cluster_name"], None, "Wait until clear up the resources."))
        for th in thread_list:
            terminate_thread(th)
        print (ecsub.tools.important_message (params["cluster_name"], None, "Wait until clear up the resources."))
        aws_instance.clean_up()
        
    except KeyboardInterrupt:
        print ("KeyboardInterrupt")
        print (ecsub.tools.important_message (params["cluster_name"], None, "Wait until clear up the resources."))
        for th in thread_list:
            terminate_thread(th)
        print (ecsub.tools.important_message (params["cluster_name"], None, "Wait until clear up the resources."))
        aws_instance.clean_up()
    
    print ("ecsub failed.")
    return 1

def set_param(args, env_options = None):
    
    default = Argments()
    
    params = {}
    for key in default.__dict__.keys():
        params[key] = default.__dict__[key]
    
    for key in args.__dict__.keys():
        params[key] = args.__dict__[key]
    
    if env_options != None:
        params["env_options"] = env_options
        
    return params

def entry_point(args):
    
    params = set_param(args)
    return main(params)
    
def entry_point_flyaway(args, env_options = None):
    
    """
    # add proj from function call
    env_options = [
        { "name": "PROJECT_NAME", "value": "moogle"}
    ]
    """
    
    params = set_param(args, env_options = env_options)
    params["flyaway"] = True
    return main(params)

class Argments:
    def __init__(self):
        self.wdir = "./"
        self.image = "python:2.7.14"
        self.use_amazon_ecr = False
        self.shell = "/bin/bash"
        self.setup_container_cmd = "apt update; apt install -y python-pip; pip install awscli --upgrade; aws configure list"
        self.dind = False
        self.script = ""
        self.tasks = ""
        self.task_name = ""
        self.aws_s3_bucket = ""
        self.aws_ec2_instance_type = ""
        self.aws_ec2_instance_type_list = ""
        self.aws_ecs_instance_role_name = "ecsInstanceRole"
        self.disk_size = 0
        self.processes = 20
        self.processes_file_check = 10
        self.aws_security_group_id = ""
        self.aws_log_group_name = ""
        self.aws_key_name = ""
        self.aws_subnet_id = ""
        self.spot = False
        self.retry_od = False
        self.request_payer_bucket = ""
        self.ignore_location = False
        self.not_verify_bucket = False
        self.skip_price = False
        self.waiter_delay = 15
        self.goofys = False

        # The followings are not optional
        self.setx = "set -x"
        self.flyaway = False
        self.aws_account_id = ""
        self.aws_region = ""
        
if __name__ == "__main__":
    pass

