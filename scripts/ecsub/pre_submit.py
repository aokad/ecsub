#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 22 12:11:29 2019

@author: aokada
"""

import boto3
import os
import ecsub.aws
import ecsub.aws_config
import ecsub.tools
import ecsub.metrics

def read_tasksfile(tasks_file, cluster_name):
    
    tasks = []
    header = []

    for line in open(tasks_file).readlines():
        text = line.rstrip("\r\n")
        if text == "":
            continue
        if header == []:
            for item in text.split("\t"):
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
   
    env_text = "set -x \n"
    dw_text = "set -x \n"
    up_text = "set -x \n"
    
    for i in range(len(task_params["tasks"][no])):
        
        if task_params["header"][i]["type"] == "env":
            env_text += 'export %s="%s"\n' % (task_params["header"][i]["name"], task_params["tasks"][no][i])
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

    open(setenv, "w").write(env_text)
    open(downloader, "w").write(dw_text)
    open(uploader, "w").write(up_text)
    
def check_inputfiles_collect(files, dirs, cluster_name):
    
    uncheck_dirs = []
    uncheck_dirs.extend(dirs)
    for d in dirs:
        for f in files:
            if f.startswith(d):
                uncheck_dirs.remove(d)
                break

    tree = {}
    for path in files:
        bucket = path.split("/")[0]
        if not bucket in tree:
            tree[bucket] = {}
            tree[bucket]["files"] = []
            tree[bucket]["dirs"] = []
        tree[bucket]["files"].append(path.replace(bucket + "/", "", 1))

    for path in uncheck_dirs:
        bucket = path.split("/")[0]
        if not bucket in tree:
            tree[bucket] = {}
            tree[bucket]["files"] = []
            tree[bucket]["dirs"] = []
        tree[bucket]["dirs"].append(path.replace(bucket + "/", "", 1))
    
    s3 = boto3.resource('s3')
    for key in tree:
        bucket = s3.Bucket(key)
        ecsub.tools.info_message (cluster_name, None, "checking s3 bucket '%s'..." % (key))
        for obj in bucket.objects.all():
            if obj.key in tree[key]["files"]:
                tree[key]["files"].remove(obj.key)

            match = [s for s in tree[key]["dirs"] if obj.key.startswith(s)]
            for d in match:
                tree[key]["dirs"].remove(d)
            if len(tree[key]["files"]) == 0 and len(tree[key]["dirs"]) == 0:
                break

    result = []
    for key in tree:
        for typ in tree[key]:
            for path in tree[key][typ]:
                result.append("%s/%s" % (key, path))
    
    return result
    
def check_inputfiles_partial(aws_instance, files, dirs):
        
    for path in files + dirs:
        if not aws_instance.check_file(path):
            return [path]

    return []

def check_bucket_location(pathes):
    buckets = []
    for p in pathes:
        path = p.replace("s3://", "", 1).strip("/").rstrip("/").split("/")[0]
        if path == "":
            continue
        buckets.append(path)
    
    client = boto3.client("s3")
    regions = []
    for bucket in sorted(list(set(buckets))):
        response = client.get_bucket_location(Bucket=bucket)
        regions.append(response['LocationConstraint'])
    
    current_session = boto3.session.Session()
    regions.append(current_session.region_name)
    regions = sorted(list(set(regions)))
    
    return regions

def check_inputfiles(aws_instance, task_params, cluster_name, payer_buckets, work_bucket):
    
    files = []
    dirs = []
    files_rp = []
    dirs_rp = []
    outputs = []
    for task in task_params["tasks"]:
        for i in range(len(task)):
            if task_params["header"][i]["type"] == "output":
                outputs.append(task[i])
                
            if task_params["header"][i]["type"] != "input":
                continue
            
            path = task[i].replace("s3://", "", 1).strip("/").rstrip("/")
            if path == "":
                continue
            
            if ecsub.tools.is_request_payer_bucket(task[i], payer_buckets):
                if task_params["header"][i]["recursive"]:
                    dirs_rp.append(path)
                else:
                    files_rp.append(path)
            else:
                if task_params["header"][i]["recursive"]:
                    dirs.append(path)
                else:
                    files.append(path)
    
    regions = check_bucket_location(dirs + files + [work_bucket] + outputs)
          
    invalid_files = []
    invalid_files += check_inputfiles_collect(sorted(list(set(files))), sorted(list(set(dirs))), cluster_name)
    invalid_files += check_inputfiles_partial(aws_instance, sorted(list(set(files_rp))), sorted(list(set(dirs_rp))))
    
    return (regions, invalid_files)

def upload_scripts(task_params, aws_instance, local_root, s3_root, script, cluster_name, shell, request_payer):

    runsh = local_root + "/run.sh"
    s3_runsh = s3_root + "/run.sh"
    write_runsh(task_params, runsh, shell, ecsub.tools.is_request_payer_bucket(s3_root, request_payer))
    
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
        
        write_s3_scripts(task_params, request_payer, setenv, downloader, uploader, i)
        s3_setenv_list.append(s3_setenv)
        s3_downloader_list.append(s3_downloader)
        s3_uploader_list.append(s3_uploader)
        
    aws_instance.s3_copy(local_root, s3_root, True)
    
    s3_script = s3_root + "/userdata/" + os.path.basename(script)
    aws_instance.s3_copy(script, s3_script, False)
    
    pathes = []
    for p in [s3_runsh, s3_script] + s3_setenv_list + s3_downloader_list + s3_uploader_list:
        pathes.append(p.replace("s3://", "", 1).strip("/").rstrip("/"))
        
    invalid_files = check_inputfiles_collect(pathes, [], cluster_name)
    #invalid_files = check_inputfiles_partial(aws_instance, [s3_runsh, s3_script] + s3_setenv_list + s3_downloader_list + s3_uploader_list, [])
    if len(invalid_files) > 0:
        return False
    
    aws_instance.set_s3files(s3_runsh, s3_script, s3_setenv_list, s3_downloader_list, s3_uploader_list)
    
    return True

if __name__ == "__main__":
    pass
