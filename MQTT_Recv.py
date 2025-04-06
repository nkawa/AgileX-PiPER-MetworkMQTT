import json
from paho.mqtt import client as mqtt
import multiprocessing as mp
import multiprocessing.shared_memory
import socket

from multiprocessing import Process, Queue

import sys
import os
from datetime import datetime
import math
import numpy as np
import time

## ここでUUID を使いたい
import uuid

from dotenv import load_dotenv
import ipget


load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))

MQTT_SERVER = os.getenv("MQTT_SERVER", "192.168.207.22")
MQTT_CTRL_TOPIC ="piper/vr" # MANAGE_RECV_TOPIC で動的に変更される

ROBOT_UUID = os.getenv("ROBOT_UUID","no-uuid")
ROBOT_MODEL = os.getenv("ROBOT_MODEL","piper")
MQTT_MANAGE_TOPIC = os.getenv("MQTT_MANAGE_TOPIC", "dev")
MQTT_MANAGE_RCV_TOPIC = os.getenv("MQTT_MANAGE_RCV_TOPIC", "dev")+"/"+ROBOT_UUID

def get_ip_list():
    ll = ipget.ipget()
    flag = False
    ips = []
    for p in ll.list:
        if flag:
            flag=False
            if p == "127.0.0.1/8":
                continue
            ips.append(p)
        if p == "inet":
            flag = True
    return ips

class MQTT_Recv:
    def __init__(self):
        self.start = -1

    def on_connect(self,client, userdata, flag, rc):
        print("MQTT:Connected with result code " + str(rc), "subscribe ctrl", MQTT_CTRL_TOPIC)  # 接続できた旨表示
        self.client.subscribe(MQTT_CTRL_TOPIC) #　connected -> subscribe

        # ここで、MyID Register すべき
        my_info = {
            "date" :  str(datetime.today()),
            "version": "0.0.1",
            "devType": "robot",
            "robotModel": ROBOT_MODEL,
            "codeType": "PiPER-control",
            "IP": get_ip_list(),
            "devId": ROBOT_UUID 
        }
        self.client.publish("mgr/register", json.dumps(my_info))
        print("Publish",json.dumps(my_info))

        self.client.subscribe(MQTT_MANAGE_RCV_TOPIC) #　connected -> subscribe

# ブローカーが切断したときの処理
    def on_disconnect(self,client, userdata, rc):
        if  rc != 0:
            print("Unexpected disconnection.")

    def on_message(self,client, userdata, msg):
        global MQTT_CTRL_TOPIC
#        print("Message",msg.payload)
        if msg.topic == MQTT_MANAGE_RCV_TOPIC:  # 受信先を指定された場合
            js = json.loads(msg.payload)
            if "controller" in js:
                if "devId" in js:
                    MQTT_CTRL_TOPIC = "control/"+js["devId"]
                    self.client.subscribe(MQTT_CTRL_TOPIC) #　connected -> subscribe
                    print("Receive Contoller msg, then listen", MQTT_CTRL_TOPIC)
            
        if msg.topic == MQTT_CTRL_TOPIC:
            js = json.loads(msg.payload)
            rot =js["joints"]
#            print(rot)
            joint_q = [
                int(rot[0]*1000),
                int((rot[1]+85)*1000),
                int((rot[2]-170)*1000),
                int(rot[3]*1000),
                int((rot[4]-270)*1000),                
                int(rot[5]*1000),
                int(rot[6]*1000)
            ]
        # このjoint 情報も Shared Memoryに保存すべし！
            self.pose[8:15] = joint_q 
#            print("Set Joints:",joint_q)
        # Target 情報を保存するだけ
        else:
            print("not subscribe msg",msg.topic)


    def connect_mqtt(self):

        self.client = mqtt.Client()  
# MQTTの接続設定
        self.client.on_connect = self.on_connect         # 接続時のコールバック関数を登録
        self.client.on_disconnect = self.on_disconnect   # 切断時のコールバックを登録
        self.client.on_message = self.on_message         # メッセージ到着時のコールバック
        self.client.connect(MQTT_SERVER, 1883, 60)
#  client.loop_start()   # 通信処理開始
        self.client.loop_forever()   # 通信処理開始

    def run_proc(self):
        self.sm = mp.shared_memory.SharedMemory("PiPER")
        self.pose = np.ndarray((16,), dtype=np.dtype("float32"), buffer=self.sm.buf)

        self.connect_mqtt()