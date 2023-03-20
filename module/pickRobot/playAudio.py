# -*- coding: utf-8 -*-
# @Date: 2023/02/21
# @Author: zhong
# @File: playAudio.py
# @Version: 1.1
# @Project: 定制化动态播放指定音频
# @Description: 在指定区域内执行任务时，播放指定的音频；导航经过时不播放音频，只在执行任务时播放
# @Coding:
# @Update:

import math
import time

from rbkSim import SimModule
from robot import ModuleTool


class PlayAudio:
    def __init__(self):
        # 各定制播放区域包含的站点
        self.area_ready = ["AP71", "AP72", "AP74", "AP75", "AP115", "AP116", "AP117", "AP118"]
        self.area_check = ["AP19", "AP20", "AP21", "AP22"]
        self.area_container = ["AP39", "AP40", "AP41", "AP42"]
        self.area_five_container = ["AP123", "AP124", "AP125", "AP126"]
        self.area_six_container = ["AP15", "AP16", "AP17", "AP18"]
        self.area_seven_container = ["AP11", "AP12", "AP13", "AP14"]
        self.area_two_device = ["AP35", "AP36", "AP37", "AP38", ""]
        self.area_three_device = ["AP133", "AP134", "AP135", "AP136"]
        self.area_four_device = ["AP137", "AP138", "AP139", "AP140", "AP141", "AP142", "AP143", "AP144"]
        # 音频名称
        self.audios = ["ready_1", "check_1", "container_1", "five_container_1", "six_container_1",
                       "seven_container_1", "two_device_1", "three_device_1", "four_device_1"]
        # 定制播放区域，与音频名称一一对应
        self.areas = [self.area_ready, self.area_check, self.area_container, self.area_five_container,
                      self.area_six_container, self.area_seven_container, self.area_two_device,
                      self.area_three_device, self.area_four_device]
        self.radius = 2   # 区域半径（米）
        self.start_time = time.time()
        self.duration = 30  # 音频播放持续时间（秒）
        self.circle_count = 0

    def play(self, r: SimModule):
        audio_name = self.getAudioName(r)
        if audio_name is not None:
            if self.circle_count == 0:
                r.setSound(audio_name, False)
            else:
                if r.sound().get('status', -1) == 0:
                    self.circle_count += 1
                    if ModuleTool.delay(3):
                        r.setSound(audio_name, False)
        else:
            r.stopSound(True)

        if time.time() - self.start_time > self.duration:
            r.stopSound(True)

        if self.circle_count > 3:
            r.stopSound(True)

    def getAudioName(self, r):
        x = r.loc().get('x', 0)
        y = r.loc().get('y', 0)
        for area in self.areas:
            for loc in area:
                try:
                    if math.sqrt((r.getLM(loc, True)[0] - x) ** 2 + (r.getLM(loc, True)[1] - y) ** 2) <= self.radius:
                        return self.audios[self.areas.index(area)]
                except Exception as e:
                    r.setError(f"{e}")
