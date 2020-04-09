"""
The file path only has the operation count , the DB type and the thread cnt
The format is {DB}-{oprCount}-{threadCnt}-{workloadName}.result
"""
import os
import sys

import pandas as pd
import pyecharts
from pyecharts import Page


def read_workload():
    ans = {}
    df = pd.read_csv('workloadmapping.csv')
    for i, row in df.iterrows():
        ans.update({row['title']: row['subtitle']})
    return ans


class YCSB_analyser:
    def __init__(self, root_path):
        self.ops_key = 'Throughput(ops/sec)'
        self.workload_key = 'workload'
        self.db_type_key = 'DB'
        self.root_path = root_path
        self.x_labels = ['operation_count', 'number_of_threads']
        self.db_type_cnt = 0

    def paint(self):
        # Fetch data of y-axis from all of files (end with .result)
        y_kv = self.analyse_y_axis()
        # Fetch data of x-axis from filename
        raw_x_kv = self.analyse_x_axis(y_kv)
        # split the x_kvs into multiple barrels
        patches = self.kv_patch(raw_x_kv)
        # paint each graph according to current x-label types
        page = Page()

        for confine_label, v in patches.items():
            for confine_value, x_data in v.items():
                page.add(
                    self.construct_graph(x_data, y_kv, [item for item in self.x_labels if item != confine_label][0]))
        result_html_path = "{}/index.html".format(self.root_path)
        if not os.path.exists(result_html_path):
            os.system('touch {}'.format(result_html_path))
        page.render(result_html_path)

    def analyse_y_axis(self):
        """
        Read from local file system and fetch all filenames which end with .result
        :return: y-axis label and data. Now they are 'ops' and 'runtime'
        """
        target_file_list = []
        for root, dirs, filenames in os.walk(self.root_path):
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

    def analyse_x_axis(self, y_kv):
        x_kv = {}
        db_set = set()
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
                operation_count=oprCount,
                number_of_threads=threadCnt,
                workload=workload
            ))
            db_set.add(DB)
        self.db_type_cnt = len(db_set)
        return x_kv

    def kv_patch(self, raw_x_kv):
        """
        Split the raw kv data into different patches
        :param raw_x_kv:
        :return:
        """
        # {'thread_count': 4, 'opr_count': 500000, 'workload': 'workloada', 'DB': 'AnnaMaster'}
        barrels = {}
        for cur_key in self.x_labels:
            value_set = sorted(list(set([v[cur_key] for v in raw_x_kv.values()])))
            barrels.update({cur_key: value_set})

        kvs = {}
        for i, cur_key in enumerate(self.x_labels):
            val_map = {}
            for label_val in barrels[cur_key]:
                pre = val_map.get(label_val) if label_val in val_map else {}
                for k, v in [[k, v] for k, v in raw_x_kv.items() if v[cur_key] == label_val]:
                    pre.update({k: v})
                val_map.update({label_val: pre})
            # clean up single node
            true_map = {}
            for k, v in val_map.items():
                if len(val_map[k]) > self.db_type_cnt:
                    true_map.update({k: v})
            kvs.update({cur_key: true_map})
        return kvs

    def construct_graph(self, x_kv, y_kv, x_label_name):
        """
        construct graph (x axis is the thread count)
        :param x_kv:
        :param y_kv:
        :param x_label_name:
        :return:
        """
        lines = {}
        for x_value in x_kv.values():
            db_type = x_value.get(self.db_type_key)
            if lines.get(db_type) is None: lines.setdefault(db_type, [])

        x_tmp_list = []
        for k, x_value in x_kv.items():
            y_value = y_kv.get(k)
            db_type = x_value.get(self.db_type_key)
            x, y = x_value.get(x_label_name), y_value.get(self.ops_key)
            x_tmp_list.append(x)
            li = lines.get(db_type)
            li += [(x, y)]
            lines.update({db_type: li})

        # sort by x value
        for k in lines.keys():
            lines.update({k: sorted(lines.get(k), key=lambda item: item[0])})

        # Now every line could construct the single line in the graph
        # Every line denotes the target DB type
        workload_map = read_workload()
        title = x_value[self.workload_key].title()
        sub_title = workload_map[x_value[self.workload_key]] if x_value[self.workload_key] in workload_map else ''

        line = pyecharts.Line(title,
                              sub_title,
                              height=300,
                              title_text_size=14,
                              subtitle_text_size=10,
                              title_pos='center')
        # https://pyecharts.readthedocs.io/en/latest/zh-cn/%E5%9B%BE%E5%BD%A2%E7%AF%87/
        for label, v in lines.items():
            X, y = [str(item[0]) for item in v], [item[1] for item in v]
            line.add(label, X, y,
                     xaxis_name=' '.join(x_label_name.split('_')),
                     yaxis_name=self.ops_key,
                     xaxis_name_pos='middle',
                     yaxis_name_pos='end',
                     legend_pos='right',
                     legend_orient='vertical'
                     )
        return line


if __name__ == '__main__':
    path = os.getcwd() if len(sys.argv) < 2 else sys.argv[1]
    YCSB_analyser(path).paint()
