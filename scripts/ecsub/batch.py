# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 13:06:19 2018

@author: Okada
"""

import boto3
import os
import shutil
import threading
import datetime
import time
import ecsub.aws_batch
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
                if task_params["header"][i]["type"] == "env":
                    continue
                bucket = task[i].replace("s3://", "").split("/")[0]
                buckets_raw.append(bucket)
                
        buckets = sorted(list(set(buckets_raw + work_bucket)))
        buckets.remove("")
        return buckets

    buckets = tasks_to_buckets(task_params, work_bucket)
    client = boto3.client("s3")
    regions = []
    for bucket in sorted(list(set(buckets))):
        try:
            response = client.get_bucket_location(Bucket=bucket)
        except Exception as e:
            print (ecsub.tools.error_message (cluster_name, None, e))
            return None
        
        if response['LocationConstraint'] == None:
            print (ecsub.tools.warning_message (cluster_name, None, "Failure get_bucket_location '%s'..." % (bucket)))
        else:
            regions.append(response['LocationConstraint'])
    
    current_session = boto3.session.Session()
    regions.append(current_session.region_name)
    regions = sorted(list(set(regions)))
    
    return regions

def check_inputfiles(cluster_name, task_params, payer_buckets):
    
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
    
    def __check_file(ctx, path):
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
                if response['Contents']['KeyCout'] > 0:
                    exit_code = 0
            else:
                for c in response['Contents']:
                    if c['Prefix'] == path["key"]:
                        exit_code = 0
            
            if exit_code == 1:
                print(ecsub.tools.error_message (cluster_name, None, "s3-path '%s' is invalid." % (path)))
            else:
                print(ecsub.tools.info_message (cluster_name, None, "check s3-path '%s'...ok" % (path)))
                
        except Exception as e:
            print(e)
            print(ecsub.tools.error_message (cluster_name, None, "s3-path '%s' is invalid." % (path)))
            
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
                    
            jobs = 10 - alives
            submitted = len(thread_list)
            for i in range(jobs):
                no = i + submitted
                if no >= len(pathes):
                    break

                thread_name = "thread_%03d" % (no)
                th = threading.Thread(
                    target = __check_file, 
                    name = thread_name, 
                    args = ((ctx, pathes[no]))
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
            print ("Success")
            return True
        
    except Exception as e:
        print (e)
        
    except KeyboardInterrupt:
        print ("KeyboardInterrupt")
        
    return False

def upload_scripts(task_params, aws_instance, local_root, s3_root, script, cluster_name, shell, request_payer_bucket, not_verify_bucket):

    def upload_file (local_file, s3_path):
        s3 = boto3.resource('s3')
        bucket = s3_path.replace("s3://", "").split("/")[0]
        key = s3_path.replace("s3://" + bucket + "/", "")
        s3.Object(bucket, key).upload_file(local_file)
        
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

def submit_task(ctx, thread_name, aws_instance, no):
    exit_code = aws_instance.submit_job(no)
    ctx[thread_name] = exit_code

import ctypes
def terminate_thread(thread):
    """
    Terminates a python thread from another thread.

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

    try:
        # set stack_name
        params["stack_name"] = params["task_name"]
        if params["stack_name"] == "":
            now = datetime.datetime.now()
            basename = os.path.splitext(os.path.basename(params["tasks"]))[0].replace(".", "_")
            for t in basename:
                if params["stack_name"] == "" and not t.isalpha():
                    continue
                params["stack_name"] += t
                    
            params["stack_name"] += "-" + now.strftime("%Y%m%d-%H%M%S")
                
        # instance_types
        instance_types = params["aws_ec2_instance_types"].replace(" ", "")
        for itype in instance_types.split(","):
            if itype.startswith("t"):
                print (ecsub.tools.error_message (params["stack_name"], None, "One of --aws-ec2-instance-type option and --aws-ec2-instance-type-list option is required."))
                return 1
        params["aws_ec2_instance_types"] = instance_types
        
        # request_payer_bucket
        request_payer_bucket = params["request_payer_bucket"].replace(" ", "")
        params["request_payer_bucket"] = request_payer_bucket.split(",")
        params["request_payer_bucket"].remove("")
            
        # read tasks file
        task_params = read_tasksfile(params["tasks"], params["stack_name"])
        if task_params == None:
            #print (ecsub.tools.error_message (params["stack_name"], None, "task file is invalid."))
            return 1
        
        if task_params["tasks"] == []:
            print (ecsub.tools.info_message (params["stack_name"], None, "Task file is empty."))
            return 0
        
        subdir = params["stack_name"]
        
        params["wdir"] = params["wdir"].rstrip("/") + "/" + subdir
        params["aws_s3_bucket"] = params["aws_s3_bucket"].rstrip("/") + "/" + subdir
        
        if os.path.exists (params["wdir"]):
            shutil.rmtree(params["wdir"])
            print (ecsub.tools.info_message (params["stack_name"], None, "'%s' existing directory was deleted." % (params["wdir"])))
            
        os.makedirs(params["wdir"])
        os.makedirs(params["wdir"] + "/log")
        os.makedirs(params["wdir"] + "/conf")
        os.makedirs(params["wdir"] + "/script")

        # disk-size
        if params["disk_size"] < 1:
            print (ecsub.tools.error_message (params["stack_name"], None, "disk-size %d is smaller than expected size 1GB." % (params["disk_size"])))
            return 1
            
        aws_instance = ecsub.aws_batch.Aws_ecsub_control(params, len(task_params["tasks"]))
        
        # check task-param
        if not aws_instance.check_awsconfigure():
            return 1

        # check s3-files path
        if params["not_verify_bucket"] == False:
            regions = check_bucket_location(params["stack_name"], task_params, params["aws_s3_bucket"])
            if regions == None:
                return 1
            if len(regions) > 1:
                if params["ignore_location"]:
                    print (ecsub.tools.warning_message (params["stack_name"], None, "your task uses multipule regions '%s'." % (",".join(regions))))
                else:
                    print (ecsub.tools.error_message (params["stack_name"], None, "your task uses multipule regions '%s'." % (",".join(regions))))
                    return 1
                
            if not check_inputfiles(task_params, params["stack_name"], params["request_payer_bucket"], params["aws_s3_bucket"]):
                return 1
        
        # write task-scripts, and upload to S3
        local_script_dir = params["wdir"] + "/script"
        s3_script_dir = params["aws_s3_bucket"].rstrip("/") + "/script"
        if not upload_scripts(task_params, 
                       aws_instance, 
                       local_script_dir, 
                       s3_script_dir,
                       params["script"],
                       params["stack_name"],
                       params["shell"],
                       params["request_payer_bucket"],
                       params["not_verify_bucket"]):
            print (ecsub.tools.error_message (params["stack_name"], None, "failure upload files to s3 bucket: %s." % (params["aws_s3_bucket"])))
            return 1
        
    except KeyboardInterrupt:
        print ("KeyboardInterrupt")
        return 1
    
    # run purocesses
    thread_list = []
    ctx = {}
    
    try:
        # run CloudFormation create_stack
        if not aws_instance.create_batch_env():
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
                        args = ((ctx, thread_name, aws_instance, no))
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
        
        if params["wait"] == False:
            aws_instance.clean_up()
            
        # SUCCESS?
        if [0] == list(set(exitcodes)):
            print ("ecsub completed successfully!")
            return 0
        
    except Exception as e:
        print (e)
        print (ecsub.tools.important_message (params["stack_name"], None, "Wait until clear up the resources."))
        for th in thread_list:
            terminate_thread(th)
        print (ecsub.tools.important_message (params["stack_name"], None, "Wait until clear up the resources."))
        aws_instance.clean_up()
        
    except KeyboardInterrupt:
        print ("KeyboardInterrupt")
        print (ecsub.tools.important_message (params["stack_name"], None, "Wait until clear up the resources."))
        for th in thread_list:
            terminate_thread(th)
        print (ecsub.tools.important_message (params["stack_name"], None, "Wait until clear up the resources."))
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
        self.s3_bucket = ""
        self.instance_types = "optimal"
        self.vcpu = 2
        self.memory = 8
        self.disk_size = 22
        self.processes = 20
        self.security_groups = ""
        self.key_name = ""
        self.subnet_ids = ""
        self.spot = False
        self.request_payer_bucket = ""
        self.ignore_location = False
        self.not_verify_bucket = False
        self.wait = False
        
        # The followings are not optional
        self.root_disk_size = 22
        self.setx = "set -x"
        self.aws_account_id = ""
        self.aws_region = ""
        
        # remove ?
        self.aws_log_group_name = ""        
        
        
if __name__ == "__main__":
    pass

