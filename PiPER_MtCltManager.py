

import multiprocessing as mp
import multiprocessing.shared_memory as shm
from multiprocessing import Process, Queue
import sys
import os

import json

from datetime import datetime
import math
import numpy as np
import time

import PiPER_Monitor
import PiPER_Control
import MQTT_Recv
   

class PiperMtClientManager:
    def __init__(self):
        mp.set_start_method('spawn')
        sz = 32* np.dtype('float').itemsize
        try:
            self.sm = shm.SharedMemory(create=True,size = sz, name='PiPER')
        except FileExistsError:
            self.sm = shm.SharedMemory(size = sz, name='PiPER')
        self.ar = np.ndarray((16,), dtype=np.dtype("float32"), buffer=self.sm.buf) # 共有メモリ上の Array

    def startRecvMQTT(self):
        self.recv = MQTT_Recv.MQTT_Recv()
        self.recvP = Process(target=self.recv.run_proc, args=(),name="MQTT-recv")
        self.recvP.start()

    def startMonitor(self):
        self.mon = PiPER_Monitor.PiPER_MON()
        self.monP = Process(target=self.mon.run_proc, args=(),name="PiPER-monitor")
        self.monP.start()

    def startControl(self):
        self.ctrl = PiPER_Control.PiPER_CON()
        self.ctrlP = Process(target=self.ctrl.run_proc, args=(),name="PiPER-control")
        self.ctrlP.start()

    def checkSM(self):
        while True:
            diff = self.ar[0:7]-self.ar[8:15]
            diff *=1000
            diff = diff.astype('int')
#            print(self.ar[:6],self.ar[6:])
            print(diff)
            time.sleep(2)
    
                                

if __name__ == '__main__':
#        
    mcm = PiperMtClientManager()
    try:
        print("Start Monitor!")
        mcm.startMonitor()
        print("Start MQTT!")
        mcm.startRecvMQTT()
        print("Start Control")
        mcm.startControl()
        print("Check!")
        mcm.checkSM() # infinite loop
    except KeyboardInterrupt:
        print("Stop!")
        mcm.close()
        mcm.unlink()
