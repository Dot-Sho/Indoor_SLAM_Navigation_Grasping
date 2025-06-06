#!/usr/bin/env python3
#coding=UTF-8 
import sys 
sys.path.append("./")
from std_msgs.msg import String
import rospy
from Sparkapi import Ws_Param
import json
from bm25 import BM25
import time

wavflag = 0
cur_pos = ""

nav_goal = rospy.Publisher("nav_goal", String, queue_size = 5)
msg_node = rospy.Publisher("msg", String, queue_size = 1)
tts = rospy.Publisher("tts", String, queue_size = 5)

file_path = '/home/handsfree/handsfree/handsfree_ros_ws/src/handsfree/robot/script/utils/load_file.txt'
BM = BM25(file_path = file_path)

def get_context_and_locs(s):
    context, source_json = BM.get_context(query=s)
    dt = json.loads(source_json)

    locs = ""
    for k, v in list(dt.items()):
        if "title" in k:
            locs += v
            locs += "、"
    l = list(locs)
    l = l[:len(l) - 1]
    locs = "".join(l)
    return context, locs

def get_detail_context_and_loc(s):
    context, source_json = BM.get_context(query=s, top_k = 1)

    dt = json.loads(source_json)
    detail_loc = ""
    for k, v in list(dt.items()):
        if "title" in k:
            detail_loc = v
            break
    return context, detail_loc 

# 处理PCM
def callback_tcpclient(endflag):
    flag = endflag.data
    if flag == 1:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_host = "172.16.11.37"  # 服务器的IP地址或主机名
        server_port = 6000          # 服务器端口号
        BUFFER_SIZE = 1024
        client_socket.connect((server_host, server_port))
        filename='/home/handsfree/handsfree/handsfree_ros_ws/src/handsfree/handsfree_speech/res/speaking_ok.wav'
        file_size=os.stat(filename).st_size #huoqu wenjiandaxiao
        client_socket.send(str(file_size).encode(encoding="utf-8"))
        
        # 发送音频文件给服务器
        with open(filename, "rb") as audio_file:
            while True:
                data = audio_file.read(1024)
                if not data:
                    break
                client_socket.send(data)
        print("音频文件发送完成")

        # 接收并打印回复的转录文本  
        text=client_socket.recv(1024).decode('utf-8')

        print(("Transcript:", text))

        msg = String()
        msg.data = transcribed_text
        msg_node.publish(msg)
        client_socket.close()


def callback_msg(msg):
    global cur_pos
    wav = String()

    rospy.loginfo(msg.data)

    prompt1 = normal_identif_setting(msg.data, cur_pos)
    res1 = sparkllm(question=prompt1)
    rospy.loginfo(prompt1)
    rospy.loginfo(res1)
    wav.data = res1

    # 调用播放模块播放res1
    tts.publish(wav)
    time.sleep(6)

    _, locs = get_context_and_locs(msg.data)
    prompt2 = action_point(msg.data, locs, cur_pos)
    res2 = sparkllm(question=prompt2)
    rospy.loginfo(prompt2)
    rospy.loginfo(res2)
    context, detail_loc = get_detail_context_and_loc(res2)
    rospy.loginfo(detail_loc)
    if cur_pos != detail_loc:
        pos = String()
        pos.data = detail_loc
        nav_goal.publish(pos)
        time.sleep(9)
        cur_pos = detail_loc

        prompt3 = introduc_from_materi(cur_pos, context)
        res3 = sparkllm(question=prompt3)
        rospy.loginfo(prompt3)
        rospy.loginfo(res3)
        #调用播放模块播放res3
        wav.data = res3
        tts.publish(wav)
        
    

if __name__ == '__main__':
    rospy.init_node('main')
    rospy.Subscriber("/record_end_flag", int, callback_tcpclient) #订阅 录音结束话题，并且回调相关函数
    rospy.Subscriber("/msg", String, callback_msg) #接受topic
    rospy.spin()
