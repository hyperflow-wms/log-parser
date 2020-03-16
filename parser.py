import os
import json
import re
from datetime import datetime
import argparse


SOURCE_DIR = 'logs-hf'
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
        os.makedirs(os.path.dirname(self.file_name), exist_ok=True)

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
        os.makedirs(os.path.dirname(self.file_name), exist_ok=True)

    def append(self, log):
        log['jobId'] = self.job_id
        self.log_list.append(log)

    def save(self):
        save_log_list(self.log_list, self.file_name)
        self.log_list.clear()


class JobDescriptionLogger:
    def __init__(self, source_dir, file_name=JOB_DESCRIPTIONS_FILE):
        self.log_map = {}
        self.time_format = '%Y-%m-%dT%H:%M:%S.%f'
        self.file_name = os.path.join(source_dir, file_name)
        os.makedirs(os.path.dirname(self.file_name), exist_ok=True)
        self.job_start_time = 0

    def set_job_start_time(self, job_start_time):
        self.job_start_time = int(datetime.strptime(job_start_time, self.time_format).timestamp() * 1000)

    def add_dict(self, new_dict):
        self.log_map.update(new_dict)

    def set_job_end_time(self, job_end_time):
        self.log_map['execTimeMs'] = int(datetime.strptime(job_end_time, self.time_format).timestamp() * 1000) - self.job_start_time

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
        return re.match('handler exiting.*', text, re.I)

    @staticmethod
    def parse_job_command(text):
        return re.match('Job command[^\']*\'([^\']*).*', text, re.I)

    @staticmethod
    def parse_procusage(text):
        return re.match('Procusage: pid: ([0-9])+[^{]*({.*})', text, re.I)

    @staticmethod
    def parse_io(text):
        return re.match('IO[^{]*({.*})', text, re.I)

    @staticmethod
    def parse_netdev(text):
        return re.match('NetDev: pid: ([0-9])+[^\[]*(\[.*\])', text, re.I)

    @staticmethod
    def parse_sysinfo(text):
        return re.match('Sysinfo[^{]*({.*})', text, re.I)


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
    matches = re.match(r'.*task-([A-Za-z0-9]+)__(\d+)__(\d+)__\d+\.log', filename)
    hf_id = matches.group(1)
    app_id = matches.group(2)
    proc_id = matches.group(3)

    return {"hyperflowId": hf_id, "workflowId": "{}-{}".format(hf_id, app_id), "jobId": "{}-{}-{}".format(hf_id, app_id, proc_id)}


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
        message_dict.pop('task_id', None)
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

    return None


def parse_and_save_json_log_file(basedir, dest_dir, filename):
    full_file_name = os.path.join(basedir, filename)
    lines = load_file_lines(full_file_name)
    context_info = extract_job_info(full_file_name)

    # loggers initialization
    job_description_logger = JobDescriptionLogger(dest_dir)
    sys_info_logger = SystemInfoLogger(context_info['jobId'], dest_dir)
    metrics_logger = MetricsLogger(context_info['workflowId'], context_info['jobId'], dest_dir)

    for line_dict in lines:
        parse_single_log(line_dict, job_description_logger, sys_info_logger, metrics_logger)

    job_description_logger.save()
    sys_info_logger.save()
    metrics_logger.save()


def parse_and_save_logs(base_dir, dest_dir):
    for file in os.listdir(base_dir):
        if file.endswith("1.log"):
            parse_and_save_json_log_file(base_dir, dest_dir, file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Workflow logs parser!')
    parser.add_argument('-s', type=str, default=SOURCE_DIR, help='Logs source directory')
    parser.add_argument('-d', type=str, default=DEST_DIR, help='Logs destination directory')
    args = parser.parse_args()

    parse_and_save_logs(args.s, args.d)
