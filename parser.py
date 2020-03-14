import os
import json
import re

base_dir = 'logs-hf'
file = 'task-HbD2SFH5__16__29__1.log'
metrics_file = 'metrics.jsonl'
jobs_descriptionS_file = 'job_descriptions.jsonl'
sys_info_file = 'sys_info.jsonl'


def save_log(log, dest_file):
    with open(dest_file, "a", encoding='utf-8') as f:
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


def create_single_log(log, context_info):
    text = log['text']

    new_log = context_info.copy()
    new_log['time'] = log['time']

    metric = parse_job_message(text)
    if metric:
        mess_dict = eval(metric.group(1))
        mess_dict.pop('redis_url', None)
        mess_dict.pop('task_id', None)
        name = mess_dict['name']
        new_log['procusage'] = eval(metric.group(1))
        return new_log

    metric = parse_procusage(text)
    if metric:
        new_log['procusage'] = eval(metric.group(1))
        return new_log

    metric = parse_io(text)
    if metric:
        new_log['io'] = eval(metric.group(1))
        return new_log

    metric = parse_netdev(text)
    if metric:
        new_log['net'] = eval(metric.group(1))
        return new_log

    metric = parse_sysinfo(text)
    if metric:
        new_log['sysinfo'] = eval(metric.group(1))
        return new_log

    return None


def parse_job_message(text):
    return re.match('jobMessage[^{]*({[^\']*).*', text, re.I)


def parse_procusage(text):
    return re.match('Procusage[^{]*({.*})', text, re.I)


def parse_io(text):
    return re.match('IO[^{]*({.*})', text, re.I)


def parse_netdev(text):
    return re.match('NetDev[^\[]*(\[.*\])', text, re.I)


def parse_sysinfo(text):
    return re.match('Sysinfo[^{]*({.*})', text, re.I)


def parse_and_save_json_log_file(basedir, filename, destfile):
    full_file_name = os.path.join(basedir, filename)
    lines = load_file_lines(full_file_name)
    context_info = extract_job_info(full_file_name)

    for line_dict in lines:
        log = create_single_log(line_dict, context_info)
        if log:
            save_log(log, destfile)


if __name__ == '__main__':
    parse_and_save_json_log_file(base_dir, file, metrics_file)
