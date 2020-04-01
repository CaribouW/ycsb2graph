"""
The file path only has the operation count , the DB type and the thread cnt
The format is {DB}-{oprCount}-{threadCnt}-{workloadName}.result
"""
import os
import sys

import pyecharts
from pyecharts import Page


def constructor(root_dir):
    """
    Read from local file system and fetch all filenames which end with .result
    :param root_dir: Root directory name
    :return: y-axis label and data
    """
    target_file_list = []
    for root, dirs, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.result'):
                whole_path = '/'.join([root, filename])
                target_file_list.append(whole_path)
    # triple list for further analysis
    ans = {}
    for filename in target_file_list:
        with open(filename) as f:
            cur_hash = {}
            for line in f:
                split_li = line.split(',')
                if split_li[0] == '[OVERALL]':
                    cur_hash.setdefault(split_li[-2].strip(), float(split_li[-1].strip()))
            ans.setdefault(filename, cur_hash)
    return ans


def construct_graph(x_kv, y_kv, x_label_name):
    """
    construct data (x axis is the thread count)
    legend is the DB type , the x label is thread count , and the y label is ops
    :param x_kv:
    :param y_kv:
    :return:
    """
    lines = {}
    for x_value in x_kv.values():
        db_type = x_value.get('DB')
        if lines.get(db_type) is None: lines.setdefault(db_type, [])

    x_tmp_list = []
    for k, x_value in x_kv.items():
        y_value = y_kv.get(k)
        db_type = x_value.get('DB')
        x, y = x_value.get(x_label_name), y_value.get('Throughput(ops/sec)')
        if x in x_tmp_list:
            continue
        else:
            x_tmp_list.append(x)
        li = lines.get(db_type)
        li += [(x, y)]
        lines.update({db_type: li})

    # sort by x value
    for k in lines.keys():
        lines.update({k: sorted(lines.get(k), key=lambda item: item[0])})

    # Now every line could construct the single line
    line = pyecharts.Line("{}\ntype :{}".format(x_value['workload'], x_label_name), '2020-03-30')
    for label, v in lines.items():
        X, y = [str(item[0]) for item in v], [item[1] for item in v]
        line.add(label, X, y)
    return line


if __name__ == '__main__':
    path = sys.argv[1]
    y_kv = constructor(path)
    x_kv = {}
    for file_name in y_kv.keys():
        split_li = file_name.split('/')[-1] \
            .split('.')[-2] \
            .split('-')
        if len(split_li) < 3:
            print('Error ! The format should be {DB}-{oprCount}-{threadCnt}-{workloadName}.result')
            break
        DB, oprCount, threadCnt, workload = split_li[0], int(split_li[1]), int(split_li[2]), split_li[3]
        x_kv.setdefault(file_name, dict(
            DB=DB,
            opr_count=oprCount,
            thread_count=threadCnt,
            workload=workload
        ))
    page = Page()
    for label in ['opr_count', 'thread_count']:
        page.add(construct_graph(x_kv, y_kv, label))
    page.render("index.html")
