#!/usr/bin/env python3
import argparse
import json
import os
import re
import ast
from datetime import datetime

SOURCE_DIR = 'logs-hf'
WORKFLOW_JSON = 'workflow.json'
FILE_SIZES_DIR = 'logs-hf'
METRICS_FILE = 'metrics.jsonl'
DEST_DIR = './'
JOB_DESCRIPTIONS_FILE = 'job_descriptions.jsonl'
SYS_INFO_FILE = 'sys_info.jsonl'


class MetricsLogger:
    def __init__(self, workflow_id, job_id, source_dir, file_name=METRICS_FILE):
        self.log_list = []
        self.custom_fields = {
            'workflowId': workflow_id,
            'jobId': job_id
        }
        self.file_name = os.path.join(source_dir, file_name)

    def append_log(self, base_log, parameter, value):
        base_log.update(self.custom_fields)
        base_log['parameter'] = parameter
        base_log['value'] = value
        self.log_list.append(base_log)

    def add_custom_fields(self, custom_fields):
        self.custom_fields = custom_fields
        for log in self.log_list:
            log.update(custom_fields)

    def add_custom_field(self, key, value):
        self.custom_fields[key] = value
        for log in self.log_list:
            log[key] = value

    def save(self):
        save_log_list(self.log_list, self.file_name)
        self.log_list.clear()


class SystemInfoLogger:
    def __init__(self, job_id, source_dir, file_name=SYS_INFO_FILE):
        self.log_list = []
        self.job_id = job_id
        self.file_name = os.path.join(source_dir, file_name)

    def append(self, log):
        log['jobId'] = self.job_id
        self.log_list.append(log)

    def save(self):
        save_log_list(self.log_list, self.file_name)
        self.log_list.clear()


class JobDescriptionLogger:
    def __init__(self, hyperflow_id, job_id, source_dir, workflow_info, file_name=JOB_DESCRIPTIONS_FILE):
        self.log_map = {
            'workflowName': workflow_info['workflowName'],
            'size': workflow_info['size'],
            'version': workflow_info['version'],
            'hyperflowId': hyperflow_id,
            'jobId': job_id
        }
        self.time_format = '%Y-%m-%dT%H:%M:%S.%f'
        self.file_name = os.path.join(source_dir, file_name)
        self.job_start_time = 0

    def set_job_start_time(self, job_start_time):
        self.job_start_time = int(datetime.strptime(job_start_time, self.time_format).timestamp() * 1000)

    def add_dict(self, new_dict):
        self.log_map.update(new_dict)

    def set_job_end_time(self, job_end_time):
        self.log_map['execTimeMs'] = int(
            datetime.strptime(job_end_time, self.time_format).timestamp() * 1000) - self.job_start_time

    def append(self, key, value):
        self.log_map[key] = value

    def save(self):
        save_log(self.log_map, self.file_name)
        self.log_map.clear()


class LogParser:
    @staticmethod
    def parse_job_message(text):
        return re.match('jobMessage[^{]*({[^\']*).*', text, re.I)

    @staticmethod
    def parse_handler_started(text):
        return re.match('handler started.*', text, re.I)

    @staticmethod
    def parse_job_started(text):
        return re.match('job started.*', text, re.I)

    @staticmethod
    def parse_job_finished(text):
        return re.match('job successful.*', text, re.I)

    @staticmethod
    def parse_handler_finished(text):
        # New format
        match = re.match('handler finished.*', text, re.I)
        if match is not None:
            return match
        # Backward compatibility with old job-executor format
        return re.match('handler exiting.*', text, re.I)

    @staticmethod
    def parse_job_command(text):
        return re.match('Job command[^\']*\'([^\']*).*', text, re.I)

    @staticmethod
    def parse_procusage(text):
        return re.match('Procusage: pid: (\d+)[^{]*({.*})', text, re.I)

    @staticmethod
    def parse_io(text):
        return re.match('IO[^{]*({.*})', text, re.I)
    
    @staticmethod
    def parse_command(text):
        return re.match('command[^{]*({.*})', text, re.I)

    @staticmethod
    def parse_netdev(text):
        return re.match('NetDev: pid: (\d+)[^\[]*(\[.*\])', text, re.I)

    @staticmethod
    def parse_sysinfo(text):
        return re.match('Sysinfo[^{]*({.*})', text, re.I)
    
    @staticmethod
    def parse_inputs(text):
        return re.match('Job\sinputs:\s+(\[.*\])', text, re.I)
    
    @staticmethod
    def parse_outputs(text):
        return re.match('Job\soutputs:\s+(\[.*\])', text, re.I)

    @staticmethod
    def parse_env_vars(text):
        return re.match('Environment\s+variables\s+\(HF_LOG\):(.*)', text, re.I)

def save_log(log, dest_file):
    with open(dest_file, "a", encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False)
        f.write(os.linesep)


def save_log_list(logs, dest_file):
    with open(dest_file, "a", encoding='utf-8') as f:
        for log in logs:
            json.dump(log, f, ensure_ascii=False)
            f.write(os.linesep)


def extract_job_info(filename):
    matches = re.match(r'.*task-([A-Za-z0-9\-_]+)__(\d+)__(\d+)__\d+\.log', filename)
    if matches:
        hf_id = matches.group(1)
        app_id = matches.group(2)
        proc_id = matches.group(3)
    else:
        print("Did not match .log file.")

    return {"hyperflowId": hf_id, "workflowId": "{}-{}".format(hf_id, app_id),
            "jobId": "{}-{}-{}".format(hf_id, app_id, proc_id)}


def split_logs(log_fd):
    current_list = []
    for line in log_fd:
        matches = re.match(r'^\[([0-9]+[^\]]*)][^\-]+-(.*)', line)
        if matches:
            if current_list:
                yield current_list
            current_list = {"time": matches.group(1), "text": matches.group(2).strip()}
        else:
            current_list["text"] += line.strip()
    yield current_list


def load_file_lines(full_file_name):
    with open(full_file_name) as fd:
        return list(split_logs(fd))


def extend_with_sizes(files_list, file_name_size_map):
    result = []
    for entry_map in files_list:
        name = entry_map['name']
        result.append({'name': name, 'size': file_name_size_map[name]})

    return result


def parse_single_log(log, job_description_logger, sys_info_logger, metrics_logger):
    text = log['text']
    new_log = {'time': log['time']}

    metric = LogParser.parse_job_started(text)
    if metric:
        job_description_logger.set_job_start_time(new_log['time'])
        metrics_logger.append_log(new_log, 'event', 'jobStart')
        return

    metric = LogParser.parse_job_finished(text)
    if metric:
        job_description_logger.set_job_end_time(new_log['time'])
        metrics_logger.append_log(new_log, 'event', 'jobEnd')
        return

    metric = LogParser.parse_handler_started(text)
    if metric:
        metrics_logger.append_log(new_log, 'event', 'handlerStart')
        return

    metric = LogParser.parse_handler_finished(text)
    if metric:
        metrics_logger.append_log(new_log, 'event', 'handlerEnd')
        return

    metric = LogParser.parse_job_message(text)
    if metric:
        message_dict = eval(metric.group(1))
        message_dict.pop('redis_url', None)
        message_dict.pop('taskId', None)
        metrics_logger.add_custom_field('name', message_dict['name'])
        job_description_logger.add_dict(message_dict)
        return

    metric = LogParser.parse_job_command(text)
    if metric:
        job_description_logger.append('command', metric.group(1))
        return

    metric = LogParser.parse_procusage(text)
    if metric:
        new_log['pid'] = metric.group(1)
        procusage = eval(metric.group(2))
        metrics_logger.append_log(new_log.copy(), 'cpu', procusage['cpu'])
        metrics_logger.append_log(new_log.copy(), 'memory', procusage['memory'])
        metrics_logger.append_log(new_log.copy(), 'ctime', procusage['ctime'])
        return

    metric = LogParser.parse_io(text)
    if metric:
        io_log = eval(metric.group(1))
        io_log.pop('ppid', None)
        io_log.pop('name', None)
        new_log['pid'] = io_log.pop('pid', None)
        metrics_logger.append_log(new_log, 'io', io_log)
        return
    
    # Optional: parsing command (redundant - job_command does essentially the same)
    # metric = LogParser.parse_command(text)
    # if metric:
    #     command_log = eval(metric.group(1))
    #     command_log.pop('ppid', None)
    #     command_log.pop('name', None)
    #     new_log['pid'] = command_log.pop('pid', None)
    #     metrics_logger.append_log(new_log, 'io', command_log)
    #     return

    metric = LogParser.parse_netdev(text)
    if metric:
        new_log['pid'] = metric.group(1)
        network = eval(metric.group(2))
        network = network[0] if network[0]['name'] == 'eth' else network[1]
        metrics_logger.append_log(new_log, 'network', network)
        return

    metric = LogParser.parse_sysinfo(text)
    if metric:
        sys_info_logger.append(eval(metric.group(1)))
        return
    
    metric = LogParser.parse_inputs(text)
    if metric:
        file_dict_tuple = ast.literal_eval(metric.group(1).strip())
        file_sizes_dict = {}
        for file_dict in file_dict_tuple:
            file_sizes_dict.update(file_dict)
        job_description_logger.log_map['inputs'] = extend_with_sizes(job_description_logger.log_map['inputs'], file_sizes_dict)
        return
    
    metric = LogParser.parse_outputs(text)
    if metric:
        file_dict_tuple = ast.literal_eval(metric.group(1).strip())
        file_sizes_dict = {}
        for file_dict in file_dict_tuple:
            file_sizes_dict.update(file_dict)
        job_description_logger.log_map['outputs'] = extend_with_sizes(job_description_logger.log_map['outputs'], file_sizes_dict)
        return
    
    metric = LogParser.parse_env_vars(text)
    if metric:
        env_dict = json.loads(metric.group(1))
        job_description_logger.append('env', env_dict )
        job_description_logger.append('nodeName', env_dict["nodeName"])
        return

    return None


def prepare_logs_dest_dir(dest_dir, workflow_info):
    logs_dir_name = os.path.join(dest_dir, "{}__{}__{}__{}".format(workflow_info['workflowName'],
                                                                   workflow_info['size'],
                                                                   workflow_info['version'],
                                                                   datetime.now().strftime('%Y-%m-%d-%H-%M-%S')))
    os.makedirs(logs_dir_name, exist_ok=True)
    return logs_dir_name


def parse_and_save_json_log_file(basedir, dest_dir, filename, workflow_info):
    full_file_name = os.path.join(basedir, filename)
    lines = load_file_lines(full_file_name)
    context_info = extract_job_info(full_file_name)

    # loggers initialization
    job_description_logger = JobDescriptionLogger(context_info['hyperflowId'], context_info['jobId'], dest_dir,
                                                  workflow_info)
    sys_info_logger = SystemInfoLogger(context_info['jobId'], dest_dir)
    metrics_logger = MetricsLogger(context_info['workflowId'], context_info['jobId'], dest_dir)

    for line_dict in lines:
        parse_single_log(line_dict, job_description_logger, sys_info_logger, metrics_logger)

    job_description_logger.save()
    sys_info_logger.save()
    metrics_logger.save()


def extract_workflow_info(workflow_json_path):
    with open(workflow_json_path) as workflow:
        source_json = json.load(workflow)

    workflow_info = {
        "workflowName": source_json['name'] if 'name' in source_json else "undefined",
        "size": source_json['size'] if 'size' in source_json else len(source_json['processes']),
        "version": source_json['version'] if 'version' in source_json else "1.0.0"
    }
    return workflow_info


def parse_and_save_logs(base_dir, dest_dir, workflow_json_path, omit):
    workflow_info = extract_workflow_info(workflow_json_path)
    logs_dest_dir = dest_dir if omit else prepare_logs_dest_dir(dest_dir, workflow_info) 
    for file in os.listdir(base_dir):
        if file.endswith("1.log"):
            parse_and_save_json_log_file(base_dir, logs_dest_dir, file, workflow_info)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Workflow logs parser!')
    parser.add_argument('-s', '--source', type=str, default=SOURCE_DIR, help='logs source directory')
    parser.add_argument('-d', '--destination', type=str, default=DEST_DIR, help='parsed logs destination directory')
    parser.add_argument('-w', '--workflow', type=str, default=WORKFLOW_JSON, help='workflow.json path')
    parser.add_argument('-o', '--omit', default=False, action='store_true', help='omit creating dedicated new directory in the destination directory')
    args = parser.parse_args()
    parse_and_save_logs(args.source, args.destination, args.workflow, args.omit)
