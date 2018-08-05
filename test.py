#!/usr/bin/env python
# -*- coding: utf-8 -*-
from aip import AipOcr
from demo import apiutil
import pylab
import imageio
import skimage
import httplib
from skimage import io,transform,exposure
import numpy as np
import Levenshtein
from pydub import AudioSegment
import collections
import sys
import os
import wave
import argparse
import time
from time import sleep

parser = argparse.ArgumentParser()
#parser.add_argument('--root_dir', type=str,default='/Users/comjia/Downloads/code/pytorch_seq2seq/pytorch_seq2seq',help='输入aishell数据所在的主目录path')
parser.add_argument("--start_df", type=float, default=-0.2,help="字幕开头需要滞后的时间（单位:s),负数表示需要字幕提前出现")
parser.add_argument("--end_df", type=float, default=0.2,help="字幕结尾需要滞后的时间（单位:s),负数表示需要字幕提前结束")
parser.add_argument("--video_name", type=str, default=u'/mnt/steven/data/movie/rmdmy/rmdmy_ep03.mp4',help="视频path")
parser.add_argument("--wav_name", type=str, default=u'/mnt/steven/data/movie/rmdmy/rmdmy_ep03.wav',help="音频path")
parser.add_argument("--ocr_source", type=str, default="tecent",help="baidu or tecent")
parser.add_argument("--movie_name", type=str, default="rmdmy",help="电视剧名称")
parser.add_argument("--srt_and_wav", type=int,default=1,help="是否srt 和 wav同时处理")
parser.add_argument("--account_index", type=int, default=0,help="有三组账号，分别是0，1，2")
opt = parser.parse_args()
print opt
# imageio.plugins.ffmpeg.download()

def contain_chinese_ratio(check_str):
    num = 0
    for ch in check_str:
        if u'\u4e00' <= ch <= u'\u9fff':
            num = num+1
    return num * 1.0 / len(check_str)

def img_to_str(client,image_path,avg_char_width,flag = 1,retry_times= 5,last_result=""):
    with open(image_path, 'rb') as fp:
        image = fp.read()
    if opt.ocr_source == "baidu":
        result = client.basicGeneral(image)
        if 'words_result' in result:
            if len(result['words_result']) > 2:
                return "",None,avg_char_width,result
            else:
                return '\n'.join([w['words'] for w in result['words_result']]),None,avg_char_width,result
    elif opt.ocr_source == "tecent":
        if opt.account_index == 0:
            app_id = '1106978111'
            app_key = '9hUBH27QnbtCWZ2x'
        elif opt.account_index == 1:
            app_id = '2107593814'
            app_key = 'bbUG12n1tnJ9FT8Q'
        elif opt.account_index == 2:
            app_id = '2107564974'
            app_key = 'wRuva6dRRQKD5fCd'
        else:
            None

        while True:
            try:
                client = apiutil.AiPlat(app_id, app_key)
                rsp = client.getOcrGeneralocr(image)
                if rsp['ret'] != 0:
                    return "", None, avg_char_width, rsp

                break
            except httplib.BadStatusLine :
                if retry_times > 0:
                    retry_times = retry_times - 1
                    print 'it retry for times:%d' %(retry_times)
                    sleep(1)
                    continue
                else:
                    msg = 'it retry 5 times. But it does not run successfully! Please check it.'
                    raise Exception(msg)

        if rsp['ret'] == 0 :
            if len(rsp['data']['item_list']) == 1:

                #i["itemcoord"][0]["y"],i["itemcoord"][0]["height"]
                #找出list中字数最多的那个case,索引放到max_word_index，返回该索引下的字符串和对应的概率
                # max_word_list = [len(item["itemstring"]) for item in rsp['data']['item_list'] ]
                # max_word_index = max_word_list.index(max(max_word_list))
                # fit_sentence = rsp['data']['item_list'][max_word_index]
                fit_sentence = rsp['data']['item_list'][0]
                print fit_sentence['itemstring'].encode('utf-8')
                #如果包含的中文字符少，那么不合格
                char_ratio = contain_chinese_ratio(fit_sentence["itemstring"])
                if char_ratio <= 0.5:
                    return "", None, avg_char_width,rsp

                # 如果文字宽度不满足要求，也不合格
                # 如果宽度符合要求的，那么累积求平均
                # if avg_char_width == -1:
                #     avg_char_width = fit_sentence["itemcoord"][0]["width"] *1.0/len(fit_sentence["itemstring"])
                # else:
                #     if abs( avg_char_width - fit_sentence["itemcoord"][0]["width"] *1.0/len(fit_sentence["itemstring"])) < 3:
                #
                #         avg_char_width += fit_sentence["itemcoord"][0]["width"] *1.0/len(fit_sentence["itemstring"])
                #         avg_char_width = avg_char_width / 2
                #     else:
                #         return "", None, avg_char_width
                #返回的文字，需要去除特殊字符
                #返回的参数是： 文字，概率，每个字宽
                return "".join([cha for cha in fit_sentence["itemstring"] if cha.isalnum()]) \
                    ,[prob["confidence"] for prob in fit_sentence["words"]] \
                    ,avg_char_width,rsp
            elif len(rsp['data']['item_list']) > 1:
                max_ratio_index = 0
                max_ratio = 0
                if last_result != "":
                    for index,i in enumerate(rsp['data']['item_list']):
                        print i['itemstring'].encode('utf-8')

                        ratio = Levenshtein.ratio(last_result, i['itemstring'])
                        if ratio > max_ratio:
                            max_ratio_index = index

                fit_sentence = rsp['data']['item_list'][max_ratio_index]
                char_ratio = contain_chinese_ratio(fit_sentence["itemstring"])
                if char_ratio <= 0.5:
                    return "", None, avg_char_width,rsp
                else:
                    return "".join([cha for cha in fit_sentence["itemstring"] if cha.isalnum()]) \
                        ,[prob["confidence"] for prob in fit_sentence["words"]] \
                        ,avg_char_width,rsp

            else:
                return "",None,avg_char_width,rsp


#对于 一段文字在多帧展示出来，ocr识别了多帧结果，使用list保存下来，使用规则根据ocr的prob来得到最准确的该段文字

#规则如下：
#使用 两个map的list来分别保存字出现的次数和字出现的概率之和，返回字个数多的；当字的个数相同时，返回字打分高的
def same_rule(same_list):
    max_len = 0

#
    for item in same_list:
        if len(item[0]) > max_len:
            max_len = len(item[0])

    char_map_list = []
    char_map_score = []
    for i in range(max_len):
        char_map_list.append(dict())
        char_map_score.append(dict())

    for index in range(max_len):
        for i in range(len(same_list)):
            if index < len(same_list[i][0]):
                char = same_list[i][0][index]
                score = same_list[i][1][index]
            else:
                char = ""
                score = 1

            if char not in char_map_list[index]:
                char_map_list[index][char] = 1
            else:
                char_map_list[index][char] += 1

            if char not in char_map_score[index]:
                char_map_score[index][char] = score
            else:
                char_map_score[index][char] += score

    #返回个数多的；当个数相同时，返回打分高的
    result = []
    for i in range(max_len):
        result.append(sorted(char_map_list[i].items(),key=lambda item:item[1],reverse=True)[0][0])
    return "".join(result)

#根据文字切割音频段
def cut_video_based_filelist(srt_filename,wav_name):
    np_vec = np.load(srt_filename)
    time_stamp_list = np_vec["filelist"]

    path = wav_name
    format_type = path.split(".")[-1]
    if format_type == "wav":
        wav_audio = AudioSegment.from_file(path, format="wav").set_channels(1)
    elif format_type == "mp3":
        wav_audio = AudioSegment.from_file(path, format="mp3").set_channels(1)
    elif format_type == "m4a":
        wav_audio = AudioSegment.from_file(path, format="mp4").set_channels(1)

    # audio = wav_audio.raw_data
    # sample_rate = wav_audio.frame_rate
    video_name =  opt.video_name.split("/")[-1].split(".")[-2]
    audio_dir_name = opt.ocr_source +"_"+ video_name
    os.mkdir(video_name)
    start_df = opt.start_df
    end_df = opt.end_df
    with open(video_name+".txt","w") as f:
        for index,time_stamp in enumerate(time_stamp_list):
            if abs(float(time_stamp[1]) - float(time_stamp[0]) ) < 0.0001 :
                continue
            # starttime_stamp = int(((float(time_stamp[0]) - srt_df) * sample_rate * 2))
            # endtime_stamp = int(((float(time_stamp[1]) + srt_df) * sample_rate * 2))

            # audio_seg = audio[starttime_stamp:endtime_stamp]
            #假如当前的字幕结束时间比下一帧字幕的开始时间还要迟，就以下一帧字幕的开始时间作为当前帧字幕的结束时间
            if index < len(time_stamp_list) - 1 and (float(time_stamp[1]) + end_df) * 1000 > (float(time_stamp_list[index+1][0])+start_df) * 1000:
                end_stamp = (float(time_stamp_list[index+1][0])+start_df) * 1000
            else:
                end_stamp = (float(time_stamp[1]) + end_df) * 1000
            audio_seg = wav_audio[(float(time_stamp[0]) + start_df) * 1000:end_stamp]
            save_name = '%s/%0004d.wav' % (video_name,index)
            text = "".join([cha for cha in (time_stamp[2]) if cha.isalnum()])
            f.write(",".join(["/movie/wav/%s/%s/%04d.wav"%(opt.movie_name,video_name,index),text.encode("utf-8")])+"\n")
            audio_seg.export(save_name,format ="wav")

#从视频中提取文字
def pull_srt_from_video(video_name,save_srt_name):
    if opt.ocr_source == "baidu":
        APP_ID = '11531274'
        API_KEY = 'nl59T9O2lmZ7iAD2wttS457F'
        SECRET_KEY = 'U0VztUf0QKwjfTxzxIcG1CWf9qz9Sobf'

        client = AipOcr(APP_ID, API_KEY, SECRET_KEY)
    elif opt.ocr_source == "tecent":
        app_id = '1106978111'
        app_key = '9hUBH27QnbtCWZ2x'
        client = apiutil.AiPlat(app_id, app_key)


    vid = imageio.get_reader(video_name,  'ffmpeg')

    all_frames = vid.get_length()
    filelist = [[0,0,u""]]#格式为：[starttime , endtime, data]
    interval_frame = 5
    framerate = vid.get_meta_data()['fps']

    same_list = []
    avg_char_width = -1


    if opt.movie_name == "rmdmy":
        start_frame = (1 * 60 + 30 ) * 25
        end_frame = (43 * 60 + 30 ) * 25
    elif opt.movie_name == "wdqbs":
        start_frame = (1 * 60 + 30 ) * 25
        end_frame = all_frames - start_frame
    elif opt.movie_name == "bly":
        start_frame = (2 * 60 + 30 ) * 25
        end_frame = all_frames - ((3 * 60 + 40 ) * 25)
    elif opt.movie_name == "nrb":
        start_frame = (0 * 60 + 5 ) * 25
        end_frame = all_frames

    print "all_frames = %d,end_frame = %d" %(all_frames,end_frame)
    last_result = ""
    try:
        for num in range(all_frames):
            if num < start_frame or num > end_frame:
                continue
            im = vid.get_data(num)
            if num % interval_frame != 0: #每10帧是40ms，帧率是25hz
                continue
            print num

            image = im#skimage.img_as_float(im).astype(np.float64)
            # if flag == 0:
            #     imageio.imsave("abcd.jpg", image[image.shape[0] * 2 /3:,:])
            #     words_tmp, porb_tmp, item = img_to_str(client, "abcd.jpg", avg_char_width,flag=flag)
            #     if words_tmp=="":
            #         continue
            #     y = item[0]["y"]
            #     height = item[0]["height"]
            #     if y > 0:
            #         flag = 1
            if opt.movie_name == "rmdmy":
                tmp = image[(image.shape[0] * 2 / 3 + 100):(image.shape[0] * 2 / 3 + 200), 200:1000]
            elif opt.movie_name == "wdqbs":
                tmp = image[(image.shape[0] * 2 /3 + 180):(image.shape[0] * 2 /3 + 320),int(image.shape[1] * 0.15) :int(image.shape[1] * 0.78)]
            elif opt.movie_name == "bly":
                tmp = image[(image.shape[0] * 2 / 3 + 180):(image.shape[0] * 2 / 3 + 320),
                      int(image.shape[1] * 0.15):int(image.shape[1] * 0.78)]
            elif opt.movie_name == "nrb":
                tmp = image[(image.shape[0] * 2 / 3 + 120):(image.shape[0] * 2 / 3 + 320),
                      int(image.shape[1] * 0.17):int(image.shape[1] * 0.88)]
            save_file_name = "%s_%d.jpg"%(save_srt_name,num)
            imageio.imsave(save_file_name,tmp)

            result , porb,avg_char_width, rsp  = img_to_str(None,save_file_name,avg_char_width,last_result)
            if rsp['ret'] != 0 or (rsp['ret'] == 0 and result == ""):
                gam2 = exposure.adjust_gamma(tmp, 0.5)
                imageio.imsave(save_file_name, gam2)
                result , porb,avg_char_width, rsp  = img_to_str(None,save_file_name,avg_char_width,last_result)
            last_result = result
            os.remove(save_file_name)

            print result.encode("utf-8")
            if result != "" :
                if len(same_list) > 0:
                    ratio = Levenshtein.ratio(result, filelist[-1][-1])

                    if ratio < 0.5:
                        filelist[-1][2] = same_rule(same_list)
                        same_list = [(result, porb)]
                        filelist.append(
                            [num * 1.0 / framerate, num * 1.0 / framerate, result])
                    else:
                        same_list.append((result,porb))
                        filelist[-1][1] = num * 1.0 / framerate
                else:
                    same_list = [(result, porb)]
                    filelist.append(
                        [num * 1.0 / framerate, num * 1.0 / framerate, result])  # 格式为：[starttime , endtime, data]
            #for reply system busy
            # elif result == "" and porb == -1:
            #     None
            else:
                if len(same_list) > 0:
                    filelist[-1][2] = same_rule(same_list)
                    same_list = []

    except IOError:
        print('可能是ioerror ')
    finally:
        np.savez(save_srt_name,
                 filelist=filelist
                 )
if __name__ == '__main__':
    save_srt_name = "%s_%s_movie_srt.npz" % (opt.video_name.split("/")[-1].split(".")[-2],opt.ocr_source)
    if opt.srt_and_wav == 1:
        pull_srt_from_video(video_name = opt.video_name,save_srt_name = save_srt_name )
    cut_video_based_filelist(srt_filename=save_srt_name,wav_name = opt.wav_name)



