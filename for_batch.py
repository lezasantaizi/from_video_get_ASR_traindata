#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/24 19:45
# @Author  : renxiaoming@julive.com
# @Site    : 
# @File    : for_batch.py.py
# @Software: PyCharm

import argparse
import os
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--video_path", type=str, default="/movie/movie/bly",help="")
parser.add_argument("--mode", type=str, default="single",help="单线程还是并发")
parser.add_argument("--index", type=int, default=0,help="index")

opt = parser.parse_args()
print opt

def single_mode_run(video_path):
    done_dirs = []
    for root, dirs, files in os.walk("."):
        for dir in dirs:
            done_dirs.append(dir.split("_",1)[-1]+".mp4")
        break


    listfile = os.listdir(video_path)
    for item in listfile:
        while True:
            ps_result = int(os.popen("ps -ef|grep test.py | grep %s |wc -l"%video_path.split("/")[-1], "r").read()[:-1])
            if ps_result < 10:
                if item in done_dirs:
                    continue
                item_list = item.split(".")
                if item_list[-1] == "mp4":
                    cmd = "nohup python -u test.py --account_index=%d --video_name=%s --wav_name=%s --movie_name=%s > %s_log & "\
                          %(opt.index,os.path.join(video_path,item),os.path.join(video_path,item_list[0]+".wav"),opt.video_path.split("/")[-1],item_list[0])
                    os.system(cmd)
                break
            else:
                time.sleep(600)#600s


def batch_run(video_path):
    done_dirs = []
    for root, dirs, files in os.walk("."):
        for dir in dirs:
            done_dirs.append(dir.split("_",1)[-1]+".mp4")
        break

    listfile = os.listdir(video_path)
    for item in listfile:
        if item in done_dirs:
            continue
        item_list = item.split(".")
        if item_list[-1] == "mp4":
            cmd = "nohup python -u test.py --video_name=%s --wav_name=%s --movie_name=%s --srt_and_wav=0 > %s_log &" \
                  %(os.path.join(video_path,item),os.path.join(video_path,item_list[0]+".wav"),opt.video_path.split("/")[-1],item_list[0])
            os.system(cmd)

if __name__ == '__main__':
    if opt.mode =="single":
        single_mode_run(opt.video_path)
    else:
        batch_run(opt.video_path)
