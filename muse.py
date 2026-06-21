import pygame

import tkinter
import tkinter.ttk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk

import platform
import subprocess
import os
import sys
import time
import hashlib
import shutil
import json
import datetime
import random
import re
import socket
import threading
import pyperclip

from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup
import requests
import urllib.parse
import base64

import eyed3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, Encoding
from mutagen.mp3 import MP3


# 主类开始位置 ******************************  主类开始位置 ******************************************************主类开始位置
class Application(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.widgets = {}  # 初始化 Tkinter控件引用字典
        self.variables = {}  # 初始化 Tkinter变量字典
        self.driver = None  # 初始化 web driver实例
        self.tools = None  # 初始化 MP3TOOLS 窗口实例（toplevel）
        self.mp3libery = None  # 初始化 mp3库路径

        self.mp3fn = None  # 初始化 mp3文件名
        self.mp3info = None  # 初始化 mp3信息
        self.mp3len = 0  # 初始化 mp3时长
        self.playlist = []  # 初始化 播放列表
        self.index = 0  # 初始化 播放列表索引

        self.lrcfn = None  # 初始化 lrc文件名
        self.lrclist = []  # 初始化 时间戳+歌词文本列表
        self.i = 0  # 初始化 时间戳+歌词文本列表索引

        self.mode = 1  # 初始化歌曲播放模式 1单曲 2列表 3随机
        self.stop = None  # 停止标志
        self.pause = None  # 暂停标志
        self.is_seeking = False  # 初始化拖动滚动条标志
        self.seek_offset_ms = 0  # <<<< 新增：用于跟踪跳转位置的偏移量

        self.picpath = None  # 初始化 徽标闪烁图片目录
        self.false_flag = None  # 初始化徽标闪烁事件

        self._ipc_sock = None  # 初始化 单实例 IPC 套接字

        self.win_set()  # 设置窗口
        self.creat_frame()  # 创建控件
        self.init_player()  # 系统初始化
        self.start_ipc_server()  # 启动单实例监听（供双击mp3转发）

    def win_set(self):
        '''设置窗口标题、大小、位置,
        项目名释义： Muse（灵感之源）
        '''
        # 设置屏幕尺寸
        x = 348
        y = 600

        self.title("Muse")
        self.geometry(f"{x}x{y}+10+10")
        self.iconbitmap(r'images\v2.ico')

    def creat_frame(self):
        ''' 创建控件'''
        with open("config/widgets.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            self.create_widgets(data["widgets"], self)

    def create_widgets(self, data, parent):
        # 从json配置文件读取数据创建界面控件。
        for widget_data in data:
            widget_type = widget_data["type"]
            widget_name = widget_data.get("name")
            options = widget_data.get("options", {})
            grid_options = widget_data.get("grid", {})
            pack_options = widget_data.get("pack", {})

            widget_class = getattr(tkinter.ttk, widget_type, None)
            # 尝试从 ttk 获取控件类，如果失败则从 tkinter 获取
            if not widget_class:
                widget_class = getattr(tkinter, widget_type, None)

            # 特别处理 Button,兼容 macos
            if platform.system() != 'Windows' and widget_type == 'Button':
                widget_class = tkinter.Button

            # 特别处理 Scale
            if widget_type == 'Scale':
                widget_class = tkinter.Scale

            # 特别处理 ScrolledText
            if widget_type == 'ScrolledText':
                widget_class = ScrolledText

            # 处理特殊选项，command，textvariable,variable,image
            if "command" in options:
                command_name = options.pop("command")
                options["command"] = getattr(self, command_name, lambda: None)

            if "image" in options:
                image_path = options.pop("image")
                pil_image = Image.open(image_path)
                imageVer = ImageTk.PhotoImage(pil_image)
                options["image"] = imageVer

            if "textvariable" in options:
                var_name = options.pop("textvariable")
                if var_name not in self.variables:
                    self.variables[var_name] = tkinter.StringVar()  # 创建StringVar
                options["textvariable"] = self.variables[var_name]

            if "variable" in options:
                var_name = options.pop("variable")
                if var_name not in self.variables:
                    # 只有当变量尚未创建时才创建IntVar
                    self.variables[var_name] = tkinter.IntVar()  # 创建IntVar
                options["variable"] = self.variables[var_name]

            # 创建控件
            if widget_class:
                widget = widget_class(parent, **options)
                if "image" in options:
                    # 保持对图片的引用，防止图片被垃圾回收
                    widget.image = imageVer

                if grid_options:  # 获取 grid 布局选项
                    widget.grid(**grid_options)
                elif pack_options:  # 获取 pack 布局选项
                    widget.pack(**pack_options)
                else:  # 使用默认的 pack 布局
                    widget.pack(padx=5, pady=5)

                self.widgets[widget_name] = widget
                # 递归创建子控件
                children = widget_data.get("children", [])
                self.create_widgets(children, widget)

    def delete_widgets(self, data):
        # 依据json内容，递归删除控件 与字典键值
        if isinstance(data, dict):
            # 如果当前元素是字典，检查其中的 "name" 键
            if "name" in data and data['name'] in self.widgets:
                self.widgets[data['name']].destroy()
                del self.widgets[data['name']]
            # 递归遍历字典的每一个值
            for value in data.values():
                self.delete_widgets(value)
        elif isinstance(data, list):
            # 如果当前元素是列表，递归遍历列表的每一个元素
            for item in data:
                self.delete_widgets(item)

    def init_player(self):
        # 系统初始化

        pygame.mixer.init()
        pygame.mixer.music.set_volume(1)  # 设置音量

        self.protocol('WM_DELETE_WINDOW', self.on_quit_savelist)
        self.widgets['scrb1'].config(command=self.widgets['lisb1'].yview)  # 给列表框配置滚动条
        self.widgets['lisb1'].config(yscrollcommand=self.widgets['scrb1'].set, selectbackground='#9ACD32')
        self.widgets['lisb1'].bind('<<ListboxSelect>>', self.item_select)  # 列表框绑定虚拟选择
        self.widgets['lisb1'].bind('<Button-1>', self.getIndex)  # 列表框单击绑定 选择项目
        self.widgets['lisb1'].bind('<B1-Motion>', self.dragJob)  # 列表框拖拽绑定 交换位置
        self.widgets['lisb1'].bind('<Double-Button-1>', self.play_bind)  # 列表框双击绑定 播放

        # 绑定进度条事件
        self.widgets['scam1'].bind("<ButtonPress-1>", self.start_seek)
        self.widgets['scam1'].bind("<ButtonRelease-1>", self.seek)
        self.widgets['scam1'].bind("<B1-Motion>", self.update_seek_label)

        # 配置按钮提示词
        with open('config/tooltip.txt', 'r', encoding='utf-8') as f:
            tips = f.readlines()
        tipdic = {}
        for tip in tips:
            value = tip.strip().split('：')
            tipdic[value[0]] = value[1]
        for k, v in tipdic.items():
            create_tooltip(self.widgets[k], v)

        lst = 'config/_quit_save.lst'
        if os.path.exists(lst):
            with open(lst, 'r', encoding='utf-8') as f:
                content = f.readlines()
            # 解析存档：首行=索引，其余=播放列表。对损坏/空列表/索引越界做保护，
            # 避免单曲播放残留或列表变短时 playlist[index] 越界崩溃。
            try:
                self.index = int(content[0].strip()) if content else 0
            except (ValueError, IndexError):
                self.index = 0
            self.playlist = [x.rstrip() for x in content[1:] if x.strip()]
            if not self.playlist:
                return  # 无可恢复曲目，跳过恢复
            if not (0 <= self.index < len(self.playlist)):
                self.index = 0  # 索引越界 → 归零到第一首
            self.mp3fn = self.playlist[self.index]
            if os.path.exists(self.mp3fn):
                self.mp3len = mp3info_extract(self.mp3fn)[1] * 1000

            for rep in self.playlist:
                self.widgets['lisb1'].insert('end', os.path.basename(rep).replace('.mp3', ''))
            self.widgets['lisb1'].selection_set(self.index)
            self.widgets['lisb1'].see(self.index)
            self.variables['play_mode'].set(2)

    #  按钮功能区 ******************************************  功能区 ********************************************* 功能区

    def load_list(self):
        # 载入列表文件
        mp3fns = load_open_path(self.load_list, 1, 'lst')
        # 显式验证路径
        if not isinstance(mp3fns, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not mp3fns:
            self.variables['lrcshow'].set(f"路径为空！")
            return

        if os.path.isfile(mp3fns):
            self.list_clear()  # 同时清空播放列表和列表框
            self.variables['play_mode'].set(2)
            try:
                with open(mp3fns, "r", encoding='utf-8') as f:
                    self.playlist = [x.rstrip() for x in f.readlines()]
            except UnicodeDecodeError:
                try:
                    with open(mp3fns, "r", encoding='gbk') as f:
                        self.playlist = [x.rstrip() for x in f.readlines()]
                except UnicodeDecodeError:
                    with open(mp3fns, "r", encoding='utf-8', errors='ignore') as f:
                        self.playlist = [x.rstrip() for x in f.readlines()]

            for rep in self.playlist:
                self.widgets['lisb1'].insert('end', os.path.basename(rep).replace('.mp3', ''))

    def getIndex(self, event):  # 列表框单击取得选择项目索引 绑定单击
        self.widgets['lisb1'].index = self.widgets['lisb1'].nearest(event.y)
        # nearest()方法用于查找鼠标事件event发生的位置
        # event.y表示事件发生的垂直位置，并返回最接近该位置的项目的索引。

    def item_select(self, event):
        # 列表框项目选择变动 绑定虚拟选择
        obj = event.widget
        try:
            self.index = obj.curselection()[0]
            self.with_selitem()

        except IndexError:
            pass

    def with_selitem(self):
        # 列表框项目选择变动时更新mp3文件信息

        piclst = ['images/aaa', 'images/bbb', 'images/ccc']
        self.picpath = random.choice(piclst)

        self.mp3fn = self.playlist[self.index]
        self.mp3len = mp3info_extract(self.mp3fn)[1] * 1000

        self.variables['mp3pres'].set(f'00:00:00')
        self.variables['mp3lens'].set(milliseconds_to_hms(self.mp3len))
        self.variables['mp3info'].set(f"{os.path.basename(self.mp3fn)}")

    def dragJob(self, event):  # 列表框项目交换位置更新索引，绑定拖拽
        newIndex = self.widgets['lisb1'].nearest(event.y)

        if newIndex < self.widgets['lisb1'].index:
            x = self.widgets['lisb1'].get(newIndex)
            lx = self.playlist.pop(newIndex)
            self.widgets['lisb1'].delete(newIndex)
            self.widgets['lisb1'].insert(newIndex + 1, x)
            self.widgets['lisb1'].index = newIndex

            self.playlist.insert(newIndex + 1, lx)
            self.index = newIndex

        elif newIndex > self.widgets['lisb1'].index:
            x = self.widgets['lisb1'].get(newIndex)
            lx = self.playlist.pop(newIndex)
            self.widgets['lisb1'].delete(newIndex)
            self.widgets['lisb1'].insert(newIndex - 1, x)
            self.widgets['lisb1'].index = newIndex

            self.playlist.insert(newIndex - 1, lx)
            self.index = newIndex

    def list_clear(self):
        # 清空列表框 从后向前删除
        for i in range(self.widgets['lisb1'].size())[::-1]:
            self.widgets['lisb1'].delete(i)
            self.widgets['lisb1'].update()
        self.playlist.clear()
        self.index = 0

    def save_list(self):
        # 保存列表文件
        filename = load_open_path(self.save_list, 4, 'lst')
        # 显式验证路径
        if not isinstance(filename, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not filename:
            self.variables['lrcshow'].set(f"路径为空！")
            return

        content = '\n'.join(self.playlist)
        with open(filename, "w", encoding='utf-8') as f:
            f.write(content)

    def on_quit_savelist(self):
        # 退出时保存列表（对空列表/越界索引做保护，避免写出坏存档导致下次启动越界崩溃）
        lst = 'config/_quit_save.lst'
        if not self.playlist:
            # 无曲目：清除旧存档，避免残留索引指向空列表
            try:
                os.remove(lst)
            except OSError:
                pass
            self.destroy()
            return
        idx = self.index if 0 <= self.index < len(self.playlist) else 0
        content = f"{idx}\n" + '\n'.join(self.playlist)
        with open(lst, 'w', encoding='utf-8') as f:
            f.write(content)
        self.destroy()

    def add_mp3(self):
        # 添加曲目到列表框
        music_file = load_open_path(self.add_mp3, 2, 'mp3')
        # 显式验证路径

        if not music_file:
            self.variables['lrcshow'].set(f"路径为空！")
            return

        for fn in music_file:
            self.widgets['lisb1'].insert('end', os.path.basename(fn).replace('.mp3', ''))
            self.playlist.append(fn)

    def del_mp3(self):
        # 从列表框删除曲目
        for rep in self.widgets['lisb1'].curselection()[::-1]:  # 用户在列表框上的选择，它返回一个元组，（单选也是返回一个元素的元组）
            # 删除列表框项目要从后向前删除，如果正向删除，每当删除一个项目，都会扰乱列表其余部分的索引，你将不能得到正确的结果
            self.widgets['lisb1'].delete(rep)
            self.playlist.pop(rep)

    def play(self):
        #播放
        if not self.mp3fn or not os.path.exists(self.mp3fn):
            self.variables['lrcshow'].set('⚠️ 文件不存在，已跳过此曲')
            return
        if pygame.mixer_music.get_busy():
            self.mystop()

        self.seek_offset_ms = 0  # <<<< 新增：为新歌曲重置偏移量

        self.lrcfn = self.mp3fn.replace('.mp3','.lrc')
        if os.path.exists(self.lrcfn):
            self.lrclist = lrcfile_to_sec_tex(self.lrcfn)
        else:
            self.lrclist = []
        self.i = 0

        pygame.mixer.music.load(self.mp3fn)
        pygame.mixer.music.play()

        self.pause = False
        self.stop = False
        self.pause_reset()

        self.cover_show()
        self.mp3_progress()


    def play_bind(self, event):
        # 播放 快捷键双击
        self.play()

    def mypause(self):
        # 暂停
        pygame.mixer.music.pause()
        self.pause = True

        pil_image = Image.open('images/unpause.png')
        imageVer = ImageTk.PhotoImage(pil_image)
        self.widgets['butt2'].config(image=imageVer, command=self.myunpause)
        self.widgets['butt2'].image = imageVer

    def pause_reset(self):
        # 暂停按钮复位
        self.pause = False
        pil_image = Image.open('images/pause.png')
        imageVer = ImageTk.PhotoImage(pil_image)
        self.widgets['butt2'].config(image=imageVer, command=self.mypause)
        self.widgets['butt2'].image = imageVer

    def myunpause(self):
        # 暂停后恢复播放
        pygame.mixer.music.unpause()
        self.pause_reset()

    def mystop(self):
        # 停止播放
        pygame.mixer.music.stop()
        self.stop = True

    def mymute(self):
        # 设置静音
        pygame.mixer.music.set_volume(0)
        pil_image = Image.open('images/speaker.png')
        imageVer = ImageTk.PhotoImage(pil_image)
        self.widgets['butt4'].config(image=imageVer, command=self.myspeaker)
        self.widgets['butt4'].image = imageVer

    def myspeaker(self):
        # 取消静音
        pygame.mixer.music.set_volume(1)
        pil_image = Image.open('images/mute.png')
        imageVer = ImageTk.PhotoImage(pil_image)
        self.widgets['butt4'].config(image=imageVer, command=self.mymute)
        self.widgets['butt4'].image = imageVer

    def start_seek(self, event):
        """当用户点击进度条时调用。"""
        if pygame.mixer.music.get_busy() or self.pause:
            self.is_seeking = True

    def seek(self, event):
        """当用户释放进度条时调用。"""
        if not self.is_seeking:
            return

        self.is_seeking = False

        # 如果音乐已停止，则不执行任何操作
        if not pygame.mixer.music.get_busy() and not self.pause:
            return

        was_paused = self.pause

        # 从滑块获取位置 (0-100)
        seek_percentage = self.widgets['scam1'].get()
        # 计算秒的位置
        seek_seconds = (self.mp3len / 1000.0) * (seek_percentage / 100.0)

        # <<<< 修改：存储偏移量（毫秒）
        self.seek_offset_ms = seek_seconds * 1000

        # pygame.mixer.music.play() 有一个 'start' 参数
        # 它会从该点重新开始播放音乐。
        pygame.mixer.music.play(start=seek_seconds)

        # 我们需要重新找到歌词的位置
        self.i = 0
        if self.lrclist:
            for index, (lrc_time, _) in enumerate(self.lrclist):
                if lrc_time >= seek_seconds:
                    self.i = index - 1
                    if self.i < 0: self.i = 0
                    break

        # 如果在拖动前是暂停的，则在新的位置暂停。
        if was_paused:
            pygame.mixer.music.pause()
            # <<<< 新增：手动更新一次UI以反映新的暂停位置
            self.widgets['scam1'].set(seek_percentage)
            self.variables['mp3pres'].set(milliseconds_to_hms(int(self.seek_offset_ms)))
        else:
            # 如果是播放状态，确保暂停按钮处于正确状态
            self.pause_reset()

    def update_seek_label(self, event):
        """当用户拖动滑块时更新时间标签。"""
        if not self.is_seeking:
            return

        seek_percentage = self.widgets['scam1'].get()
        seek_time_ms = self.mp3len * (seek_percentage / 100)
        self.variables['mp3pres'].set(milliseconds_to_hms(int(seek_time_ms)))

    def mp3_progress(self):
        # 显示播放进度和动态歌词

        # 如果用户正在拖动，则不更新
        if self.is_seeking:
            self.after(100, self.mp3_progress)
            return

        if pygame.mixer.music.get_busy():
            # <<<< 修改：计算包含偏移量的总播放时间
            total_elapsed_ms = self.seek_offset_ms + pygame.mixer.music.get_pos()

            # 防止因计时误差导致进度超出总长
            if total_elapsed_ms > self.mp3len:
                total_elapsed_ms = self.mp3len

            current_pos_percentage = (total_elapsed_ms / self.mp3len) * 100 if self.mp3len > 0 else 0
            self.widgets['scam1'].set(current_pos_percentage)

            if len(self.lrclist) > 1:
                # <<<< 修改：使用总播放时间（秒）同步歌词
                total_elapsed_sec = total_elapsed_ms / 1000
                if self.i + 1 < len(self.lrclist) and total_elapsed_sec > self.lrclist[self.i + 1][0]:
                    if self.i < len(self.lrclist) - 2:
                        self.i += 1
                self.variables['lrcshow'].set(self.lrclist[self.i][1])

            # <<<< 修改：使用总播放时间更新时间显示
            self.variables['mp3pres'].set(milliseconds_to_hms(int(total_elapsed_ms)))
            self.after(100, self.mp3_progress)

        elif self.stop:
            self.variables['lrcshow'].set('用户终止播放')
            self.variables['mp3pres'].set(f'00:00:00')
            self.widgets['scam1'].set(0)
            return

        elif self.pause:
            if self.variables['lrcshow'].get() != '现在暂停中...':
                self.variables['lrcshow'].set('现在暂停中...')
            self.after(1000, self.mp3_progress)  # 每1000毫秒检查一次

        elif self.variables['play_mode'].get() == 2:
            # 播放模式为列表循环,翻页逻辑
            self.variables['lrcshow'].set('现在列表播放模式，下一首...')
            self.index += 1
            if self.index <= len(self.playlist) - 1:
                self.mp3fn = self.playlist[self.index]
                self.widgets['lisb1'].selection_clear(0, tkinter.END)
                self.widgets['lisb1'].selection_set(self.index)
                self.widgets['lisb1'].see(self.index)
                self.variables['mp3info'].set(f"{os.path.basename(self.mp3fn)} ")
                self.mp3len = mp3info_extract(self.mp3fn)[1] * 1000
                self.widgets['scam1'].set(0)
                self.play()
            else:
                self.variables['lrcshow'].set('列表曲目已播放完毕')
                self.index = 0
                self.widgets['scam1'].set(0)
                return

        elif self.variables['play_mode'].get() == 3:
            self.variables['lrcshow'].set('现在随机播放模式，正在摇骰子选下一首...')
            if not self.playlist:
                self.widgets['scam1'].set(0)
                return
            # randrange 覆盖全部曲目（含最后一首）；列表仅 1 首时也安全，不再 range(0) 崩溃
            self.index = random.randrange(len(self.playlist))
            self.mp3fn = self.playlist[self.index]
            self.widgets['lisb1'].selection_clear(0, tkinter.END)
            self.widgets['lisb1'].selection_set(self.index)
            self.widgets['lisb1'].see(self.index)
            self.variables['mp3info'].set(f"{os.path.basename(self.mp3fn)} ")
            self.mp3len = mp3info_extract(self.mp3fn)[1] * 1000
            self.widgets['scam1'].set(0)
            self.play()

        else:
            self.variables['lrcshow'].set('现在指定播放模式，播放完毕！')
            self.variables['mp3pres'].set(f'00:00:00')
            self.widgets['scam1'].set(0)

    def false_images(self):
        # 徽标闪烁
        self.widgets['butt7'].config(command=self.cover_show)
        if pygame.mixer_music.get_busy():
            frames = []
            for ima in os.listdir(self.picpath):
                if ima.endswith('.jpg') or ima.endswith('.png'):
                    frames.append(os.path.join(self.picpath, ima))

            image = Image.open(random.choice(frames))
            image = image.resize((340, 160), resample=Image.LANCZOS)
            iming = ImageTk.PhotoImage(image)
            self.widgets['labe1'].config(image=iming, anchor='center')  # 用画布显示图片
            self.widgets['labe1'].image = iming  # 防止垃圾回收机制
            self.false_flag = self.after(500, self.false_images)

    def cover_show(self):
        # 显示封面
        self.widgets['butt7'].config(command=self.false_images)
        if self.false_flag:
            self.after_cancel(self.false_flag)

        if get_mp3image(self.mp3fn):
            image = Image.open("images/extracted_cover.jpg")
        else:
            image = Image.open("images/nocover.png")
        # 调整图像大小
        image = image.resize((340, 160), resample=Image.LANCZOS)
        # 创建PhotoImage对象并更新Label
        iming = ImageTk.PhotoImage(image)
        self.widgets['labe1'].config(image=iming, anchor='center')  # 用画布显示图片
        self.widgets['labe1'].image = iming  # 防止垃圾回收机制

    def next(self):
        # 播放下一首
        if self.index < len(self.playlist) - 1:
            self.mystop()
            self.index += 1
            self.mp3fn = self.playlist[self.index]
            self.widgets['lisb1'].selection_clear(0, tkinter.END)
            self.widgets['lisb1'].selection_set(self.index)
            self.variables['mp3info'].set(f"{os.path.basename(self.mp3fn)} ")
            self.play()
        else:
            self.variables['lrcshow'].set('已经是最后一首')

    def previous(self):
        # 播放上一首
        if self.index > 0:
            self.mystop()
            self.index -= 1
            self.mp3fn = self.playlist[self.index]
            self.widgets['lisb1'].selection_clear(0, tkinter.END)
            self.widgets['lisb1'].selection_set(self.index)
            self.variables['mp3info'].set(f"{os.path.basename(self.mp3fn)} ")
            self.play()
        else:
            self.variables['lrcshow'].set('已经是第一首！')

    def mp3_tools(self):

        if self.tools:
            self.variables['lrcshow'].set(f"MP3工具窗口已启动！")
            return
        self.tools = True
        self.lddc = None
        self.tpl = tkinter.Toplevel(self)
        self.tpl.title('老王的MP3工具')
        self.tpl.geometry('720x950')
        self.tpl.iconbitmap(r'images\v2_tools.ico')
        self.tpl.protocol('WM_DELETE_WINDOW', self.closed_tools)

        with open("config/mp3_tools.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        self.create_widgets(data["widgets"], self.tpl)
        with open('config/mp3_tooltip.txt', 'r', encoding='utf-8') as f:
            tips = f.readlines()
        tipdic = {}
        for tip in tips:
            value = tip.strip().split('：')
            tipdic[value[0]] = value[1]
        for k, v in tipdic.items():
            create_tooltip(self.widgets[k], v)

        self.tp_mp3path = None
        self.tp_mp3info = f"MP3元数据:\n\n标题：\n专辑：\n演唱："
        self.variables['mp3info_show'].set(self.tp_mp3info)
        self.widgets['tp_trel1'].bind('<<TreeviewSelect>>', self.on_tree_select)

        dic = {}
        try:
            with open('config/funpath.ini', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:  # 跳过空行
                        key, value = line.split(' ', 1)
                        dic[key] = value
        except FileNotFoundError:
            os.makedirs('config', exist_ok=True)
            open('config/funpath.ini', 'w').close()
        except Exception as e:
            print(f"读取配置文件出错: {e}")
            return None

        # 获取上次使用的目录
        self.mp3libery = dic.get('setpath_mp3lib_3', os.getcwd())

        if self.mp3libery:
            for item in self.widgets['tp_trel1'].get_children():
                self.widgets['tp_trel1'].delete(item)

            for filename in os.listdir(self.mp3libery):
                # 遍历目录中的所有文件，检查文件名是否符合条件
                if filename.endswith('.mp3'):
                    # 使用 os.path.normpath 规范路径格式
                    path = os.path.join(self.mp3libery, filename)
                    normalized_path = os.path.normpath(path).replace("\\", "/")
                    self.widgets['tp_trel1'].insert('', 'end', text=filename.replace('.mp3', ''),
                                                    values=normalized_path)

            first_item = self.widgets['tp_trel1'].get_children()[0]  # 获取所有子项的第一个
            self.widgets['tp_trel1'].selection_set(first_item)  # 选中
            self.widgets['tp_trel1'].focus(first_item)  # 聚焦（高亮显示）

        else:
            print('您还没有选择MP3目录，请选择...')
            self.setpath_mp3lib()

    def closed_tools(self):
        # 关闭tools窗口
        if self.tools:
            self.tools = False
        with open("config/mp3_tools.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        self.delete_widgets(data)
        self.tpl.destroy()

    def setpath_mp3lib(self):
        # 更新曲库路径,lrc 应与 mp3 同目录
        self.mp3libery = load_open_path(self.setpath_mp3lib, 3, title='请选择曲库目录(文件夹中至少包含一个mp3文件)')
        # 显式验证路径
        if not isinstance(self.mp3libery, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not self.mp3libery:
            return

        for item in self.widgets['tp_trel1'].get_children():
            self.widgets['tp_trel1'].delete(item)

        for filename in os.listdir(self.mp3libery):
            # 遍历目录中的所有文件，检查文件名是否符合条件
            if filename.endswith('.mp3'):
                # 使用 os.path.normpath 规范路径格式
                path = os.path.join(self.mp3libery, filename)
                normalized_path = os.path.normpath(path).replace("\\", "/")
                self.widgets['tp_trel1'].insert('', 'end', text=filename.replace('.mp3', ''), values=normalized_path)

        first_item = self.widgets['tp_trel1'].get_children()[0]  # 获取所有子项的第一个
        self.widgets['tp_trel1'].selection_set(first_item)  # 选中
        self.widgets['tp_trel1'].focus(first_item)  # 聚焦（高亮显示）

    def on_tree_select(self, event):
        # 绑定功能到 Treeview的虚拟选择
        mp3fn_tup = ''
        if self.widgets['tp_trel1'].selection():
            item_id = self.widgets['tp_trel1'].selection()[0]
            mp3fn_tup = self.widgets['tp_trel1'].item(item_id, 'values')

        if len(mp3fn_tup) == 1:
            self.tp_mp3path = mp3fn_tup[0]
        else:
            self.tp_mp3path = ' '.join(mp3fn_tup)

        if self.tp_mp3path:
            if get_mp3image(self.tp_mp3path):
                imagefn = 'images/extracted_cover.jpg'

            else:
                imagefn = 'images/115.png'

            image = Image.open(imagefn)
            # 调整图像大小
            image = image.resize((500, 280), resample=Image.LANCZOS)
            imageVer = ImageTk.PhotoImage(image)
            self.widgets["tp_labr1"].config(image=imageVer)
            self.widgets["tp_labr1"].image = imageVer

            info = mp3info_extract(self.tp_mp3path)[0]
            mp3info = f"MP3元数据:\n\n标题：{info[0]}\n专辑：{info[1]}\n演唱：{info[2]}"
            self.variables['mp3info_show'].set(mp3info)

            if len(info) > 2:
                pyperclip.copy(f"{info[0]}+{info[2]}")

            lrc = self.tp_mp3path.replace('.mp3', '.lrc')
            if os.path.exists(lrc):
                self.show_lrc(lrc)
            else:
                content = 'Mp3没有lrc歌词！'
                self.widgets['tp_texr1'].delete("1.0", tkinter.END)
                self.widgets['tp_texr1'].insert(tkinter.END, content)  # 将 LRC 内容插入 Text 组件

    def show_lrc(self, lrc):
        # 显示lrc内容
        try:  # 先尝试以utf-8格式打开文件
            with open(lrc, "r", encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:  # 如果utf-8打开失败，则尝试用gbk格式打开
                with open(lrc, "r", encoding='gbk', errors='ignore') as f:
                    content = f.read()
            except UnicodeDecodeError:  # 如果第2次仍失败，忽略错误，以utf-8强制打开
                with open(lrc, "r", encoding='utf-8', errors='ignore') as f:
                    content = f.read()

        if 'tp_texr1' in self.widgets and content:
            self.widgets['tp_texr1'].delete("1.0", tkinter.END)  # 清空 Text 组件内容
            self.widgets['tp_texr1'].insert(tkinter.END, content)  # 将 LRC 内容插入 Text 组件

    def reload_mp3_to_treeview(self):
        # 按文件名顺序重新加载 MP3 文件到 Treeview 中 (先清空 Treeview)

        # 清空 Treeview
        for item in self.widgets['tp_trel1'].get_children():
            self.widgets['tp_trel1'].delete(item)

        # 检查 MP3 目录是否存在
        if os.path.isdir(self.mp3libery):
            # 获取目录中的所有 MP3 文件并按文件名排序
            mp3_files = sorted([f for f in os.listdir(self.mp3libery) if f.endswith('.mp3')])

            # 将排序后的 MP3 文件插入到 Treeview 中
            for filename in mp3_files:
                path = os.path.join(self.mp3libery, filename)
                normalized_path = os.path.normpath(path).replace("\\", "/")
                self.widgets['tp_trel1'].insert('', 'end', text=filename.replace('.mp3', ''), values=normalized_path)

    def reload_mp3_to_treeview_by_mtime(self):
        # 按文件修改时间 重新加载 MP3 文件到 Treeview 中 (先清空 Treeview)

        # 清空 Treeview
        for item in self.widgets['tp_trel1'].get_children():
            self.widgets['tp_trel1'].delete(item)

        # 检查 MP3 目录是否存在
        if os.path.isdir(self.mp3libery):
            mp3_files = [f for f in os.listdir(self.mp3libery) if f.endswith('.mp3')]
            # 按文件的修改时间排序
            mp3_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.mp3libery, x)), reverse=True)

            # 将排序后的 MP3 文件插入到 Treeview 中
            for filename in mp3_files:
                path = os.path.join(self.mp3libery, filename)
                normalized_path = os.path.normpath(path).replace("\\", "/")
                self.widgets['tp_trel1'].insert('', 'end', text=filename.replace('.mp3', ''), values=normalized_path)

    def lrc_format(self):
        # lrc文件内容 非法字符修正、格式化时间戳
        lrc_data = []
        text_content = self.widgets['tp_texr1'].get("1.0", tkinter.END)
        lines = text_content.strip().split('\n')
        for line in lines:
            if line.startswith("["):
                match = re.search(r'\[(\d+:\d+\.\d+)\](?!.*\[\d+:\d+\.\d+\])(.*)', line)
                if match:
                    timestamp_str, lyrics = match.groups()
                    timestamp = parse_timestamp(timestamp_str)
                    lrc_data.append((timestamp, lyrics))

        lrc_data.sort(key=lambda x: x[0])  # 根据时间戳排序歌词数据

        uplrc = []
        if lrc_data[0][0] != datetime.timedelta(0):
            acter = os.path.basename(self.tp_mp3path).split('.')[0].replace('_', ' ')
            lrc_data.insert(0, (datetime.timedelta(0), acter))

        lastime = mp3info_extract(self.tp_mp3path)[1]
        lrc_data.append((datetime.timedelta(seconds=lastime), None))

        for i, (timestamp, lyrics) in enumerate(lrc_data):
            # 特别处理最后一行：即使lyrics为None，也加入只有时间戳的行
            if lyrics or i == len(lrc_data) - 1:
                updata_content = f"[{format_timestamp(timestamp)}]{lyrics.lstrip() if lyrics else ''}"
                uplrc.append(updata_content)
        updated_content = "\n".join(uplrc)

        self.widgets['tp_texr1'].delete("1.0", tkinter.END)
        self.widgets['tp_texr1'].insert(tkinter.END, updated_content)
        lrcpath = self.tp_mp3path.replace('.mp3', '.lrc')
        with open(lrcpath, 'w', encoding='utf-8') as f:
            f.write(updated_content)

    def save_selected_items_to_lst(self):
        # 获取 Treeview 中的选择项
        selected_items = self.widgets['tp_trel1'].selection()
        if not selected_items:
            return

        filename = load_open_path(self.save_selected_items_to_lst, 4, '*.lst', title='保存为lst格式的播放列表文件')
        # 显式验证路径
        if not isinstance(filename, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not filename:
            print(f"路径不能为空！")
            return

        # 打开文件并写入所选项的值
        with open(filename, 'w', encoding='utf-8') as f:
            for item in selected_items:
                # 获取所选项的值
                item_values = self.widgets['tp_trel1'].item(item, 'values')
                if item_values:  # 确保值不为空
                    f.write(item_values[0] + '\n')  # 写入值并换行
        print(f"已成功将选择项保存到文件: {filename}")

    def check_metadata(self):
        # 检查 mp3元数据、封面、歌词是否完整
        count = 0
        strcount = 0
        mp3count = 0
        covercount = 0
        lrccount = 0
        lst = []
        strlst = []
        no_underline = []
        for filename in os.listdir(self.mp3libery):
            if len(filename.split('_', 1)) != 2:
                no_underline.append(filename)

            if filename.endswith('.mp3'):
                mp3count += 1
                mp3fn = os.path.join(self.mp3libery, filename)  # 构造完整的文件路径
                audiofile = eyed3.load(mp3fn)  # 创建一个eyed3的MP3对象
                if not audiofile.tag.images:  # 获取封面图片（如果有的话）
                    covercount += 1
                    lst.append(filename)

                lrcfn = mp3fn.replace('.mp3', '.lrc')
                if not os.path.exists(lrcfn):
                    lrccount += 1
                    strlst.append(filename)

                info = mp3info_extract(mp3fn)[0]
                if len(info) == 3:
                    for item in info:
                        # 首先检查是否为字符串类型
                        if isinstance(item, str):
                            strcount += 1
                        # 然后检查是否为TIT2类型
                        elif isinstance(item, TIT2):
                            # 这里可以根据实际情况访问item的属性
                            if item.encoding == Encoding.LATIN1:
                                strlst.append(mp3fn)
                                count += 1
                        # 可以添加更多的类型检查和相应的处理逻辑
                else:
                    self.widgets['tp_texr1'].insert(tkinter.END, f"\n{filename}的metadata信息不完事")

        self.widgets['tp_texr1'].delete("1.0", tkinter.END)
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n共计{mp3count}个mp3文件")
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n\n共{covercount}个mp3没有封面，明细如下：")
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n{lst}")
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n\n共{lrccount}个mp3没有歌词，明细如下：")
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n{strlst}")
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n\n共{count}个mp3的元数据是乱码")
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n\n共{strcount}个mp3的元数据是默认字符串的值，非TIT2对象")
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n\n共{len(no_underline)}个mp3不包含下划线")
        self.widgets['tp_texr1'].insert(tkinter.END, f"\n\n{no_underline}")
        self.format_mp3name()
        self.reload_mp3_to_treeview_by_mtime()

    def set_mp3cover(self):
        # 变更封面
        cover = load_open_path(self.set_mp3cover, 1, 'jpg')
        # 显式验证路径
        if not isinstance(cover, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not cover:
            return

        if cover:
            audiofile = eyed3.load(self.tp_mp3path)
            cover_image = open(cover, "rb").read()  # 创建封面图片对象
            # 将封面图片添加到MP3文件中（使用标签类型 3）
            audiofile.tag.images.set(3, cover_image, "image/jpeg", "Front cover")
            audiofile.tag.save()  # 保存MP3文件
            # 更新封面显示
            image = Image.open(cover)
            # 调整图像大小
            image = image.resize((500, 280), resample=Image.LANCZOS)
            imageVer = ImageTk.PhotoImage(image)
            self.widgets["tp_labr1"].config(image=imageVer)
            self.widgets["tp_labr1"].image = imageVer

    def cover_identical(self):
        # 曲库封面一致化
        cover = load_open_path(self.set_mp3cover, 1, 'jpg')
        # 显式验证路径
        if not isinstance(cover, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not cover:
            return

        if not tkinter.messagebox.askyesno('变更确认', '确定更新曲库中所有MP3封面为同一图片吗？'):
            return

        for fn in os.listdir(self.mp3libery):
            if fn.endswith('.mp3'):
                mp3fn = os.path.join(self.mp3libery, fn)
                audiofile = eyed3.load(mp3fn)
                cover_image = open(cover, "rb").read()  # 创建封面图片对象
                # 将封面图片添加到MP3文件中（使用标签类型 3）
                audiofile.tag.images.set(3, cover_image, "image/jpeg", "Front cover")

                audiofile.tag.save()  # 保存MP3文件
                self.widgets['tp_texr1'].insert(tkinter.END, f"\n{fn}封面变更完成")

    def set_metadata(self):
        # 编辑MP3原数据
        def enter_change():
            title = wid_title.get().replace('请输入新标题：', '')
            album = wid_album.get().replace('请输入新专辑：', '')
            artist = wid_artist.get().replace('请输入演唱者：', '')

            tags = ID3(self.tp_mp3path)
            tags['TIT2'] = TIT2(encoding=3, text=title)
            tags['TALB'] = TALB(encoding=3, text=album)
            tags['TPE1'] = TPE1(encoding=3, text=artist)
            # 保存修改后的元数据
            tags.save()
            canel_btn()

        def canel_btn():
            framtop.destroy()
            self.widgets['tp_texr1'].pack(side='top', fill="both", expand=1)

            info = mp3info_extract(self.tp_mp3path)[0]
            mp3info = f"MP3元数据:\n\n标题：{info[0]}\n专辑：{info[1]}\n演唱：{info[2]}"
            self.variables['mp3info_show'].set(mp3info)

            lrc = self.tp_mp3path.replace('.mp3', '.lrc')
            if os.path.exists(lrc):
                self.show_lrc(lrc)
            else:
                content = 'Mp3没有lrc歌词！'
                self.widgets['tp_texr1'].insert(tkinter.END, content)  # 将 LRC 内容插入 Text 组件

        def tit_identica():
            # 全库序列化标题
            custom = wid_title.get().replace('请输入新标题：', '')
            if not tkinter.messagebox.askyesno('变更确认', f'确定全库MP3标题序列化吗？'):
                return
            i = 1
            files = sorted(os.listdir(self.mp3libery))
            for fn in files:
                if fn.endswith('.mp3'):
                    mp3fn = os.path.join(self.mp3libery, fn)
                    title = f"第{i}集"
                    if chb_var.get():
                        title = custom + title
                    tags = ID3(mp3fn)
                    tags['TIT2'] = TIT2(encoding=3, text=title)
                    # 保存修改后的元数据
                    tags.save()
                    i += 1
            self.variables['lrcshow'].set(f"全库标题名变更完成！")
            print(f"全库标题名变更完成！")

        def alb_identica():
            # 全库变更专辑名
            album = wid_album.get().replace('请输入新专辑：', '')
            if not tkinter.messagebox.askyesno('变更确认', f'确定全库MP3专辑名变更为{album}吗？'):
                return
            for fn in os.listdir(self.mp3libery):
                if fn.endswith('.mp3'):
                    mp3fn = os.path.join(self.mp3libery, fn)
                    tags = ID3(mp3fn)
                    tags['TALB'] = TALB(encoding=3, text=album)
                    # 保存修改后的元数据
                    tags.save()
            self.variables['lrcshow'].set(f"全库专辑名变更完成！")
            print(f"全库专辑名变更完成！")

        def art_identica():
            # 全库变更演唱者
            artist = wid_artist.get().replace('请输入演唱者：', '')
            if not tkinter.messagebox.askyesno('变更确认', f'确定全库MP3演唱者变更为{artist}吗？'):
                return
            for fn in os.listdir(self.mp3libery):
                if fn.endswith('.mp3'):
                    mp3fn = os.path.join(self.mp3libery, fn)
                    tags = ID3(mp3fn)
                    tags['TPE1'] = TPE1(encoding=3, text=artist)
                    # 保存修改后的元数据
                    tags.save()
            self.variables['lrcshow'].set(f"全库演唱者变更完成！")
            print(f"全库演唱者变更完成！")

        self.widgets['tp_texr1'].pack_forget()
        framtop = tkinter.ttk.Frame(self.widgets['tp_rf'])
        framtop.pack(side='top', fill="both", expand=1)

        wid_title = tkinter.ttk.Entry(framtop)
        wid_album = tkinter.ttk.Entry(framtop)
        wid_artist = tkinter.ttk.Entry(framtop)

        enter = tkinter.ttk.Button(framtop, text="当前MP3变更确定", command=enter_change)
        alb = tkinter.ttk.Button(framtop, text="全曲库变更专辑名", command=alb_identica)
        art = tkinter.ttk.Button(framtop, text="全曲库变更演播者", command=art_identica)
        tit = tkinter.ttk.Button(framtop, text="全曲库序列化标题", command=tit_identica)
        chb_var = tkinter.BooleanVar()
        chb = tkinter.ttk.Checkbutton(framtop, text="专辑名前缀", variable=chb_var)
        canel = tkinter.ttk.Button(framtop, text="退出元数据编辑", command=canel_btn)

        wid_title.grid(row=0, column=0, columnspan=2, pady=2, sticky='nsew')
        wid_album.grid(row=1, column=0, columnspan=2, pady=2, sticky='nsew')
        wid_artist.grid(row=2, column=0, columnspan=2, pady=2, sticky='nsew')

        alb.grid(row=3, column=0, columnspan=1, pady=2, sticky='nsew')
        art.grid(row=3, column=1, columnspan=1, pady=2, sticky='nsew')
        tit.grid(row=4, column=0, columnspan=1, pady=2, sticky='nsew')
        chb.grid(row=4, column=1, columnspan=1, pady=2, sticky='nsew')

        enter.grid(row=5, column=0, columnspan=1, pady=2, sticky='nsew')
        canel.grid(row=5, column=1, columnspan=1, pady=2, sticky='nsew')

        self.tp_mp3info = mp3info_extract(self.tp_mp3path)[0]
        wid_title.insert(0, f"请输入新标题：{self.tp_mp3info[0]}")
        wid_album.insert(0, f"请输入新专辑：{self.tp_mp3info[1]}")
        wid_artist.insert(0, f"请输入演唱者：{self.tp_mp3info[2]}")

    def conver_to_mp3(self):
        # 转换成 mp3
        def conver_mp3_com():
            path = load_open_path(conver_mp3_com, 1, 'wav', 'm4a', 'aac', 'flac', 'wma', 'ogg', 'aif', 'aiff', 'amr')
            # 显式验证路径
            if not isinstance(path, (str, os.PathLike)):
                raise ValueError("必须提供有效路径！")
            if not path:
                return
            # 获取 FFmpeg 路径
            ffmpeg_path = get_ffmpeg_path()
            if not ffmpeg_path:
                messagebox.showerror("错误", "未找到 FFmpeg！请下载并放入项目/bin目录。")
                return

            # 分割路径和扩展名
            dirfn, extfn = os.path.split(path)
            basename, ext = os.path.splitext(extfn)

            # 输出目录选择（根据复选框 con_var）
            if con_var.get() == 1:
                dirfn = self.mp3libery

            # 生成输出路径（确保扩展名为 .mp3）
            outfn = os.path.join(dirfn, f"{basename}.mp3")

            # 构建 FFmpeg 命令
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', path,  # 输入文件
                '-codec:a', 'libmp3lame',
                '-q:a', '2',  # 质量参数（2=高质量，范围0-9）
                '-y',  # 覆盖已存在文件（可选）
                outfn  # 输出文件
            ]

            try:
                # 执行命令（捕获错误输出）
                subprocess.run(ffmpeg_cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=False)
                conver_info.set(f'{basename}{ext}转换为{basename}.mp3 OK!')
            except subprocess.CalledProcessError as e:
                print(f"FFmpeg 转换失败: {e.stderr}")
            except FileNotFoundError:
                print("错误: 未找到 FFmpeg，请确保已安装并添加到系统路径！")

        def canel_btn():
            framtop.destroy()
            self.widgets['tp_texr1'].pack(side='top', fill="both", expand=1)
            conver_info.set('')

            info = mp3info_extract(self.tp_mp3path)[0]
            mp3info = f"MP3元数据:\n\n标题：{info[0]}\n专辑：{info[1]}\n演唱：{info[2]}"
            self.variables['mp3info_show'].set(mp3info)

            lrc = self.tp_mp3path.replace('.mp3', '.lrc')
            if os.path.exists(lrc):
                self.show_lrc(lrc)
            else:
                content = 'Mp3没有lrc歌词！'
                self.widgets['tp_texr1'].insert(tkinter.END, content)  # 将 LRC 内容插入 Text 组件

        def extract_mp3_com():
            # 从视频提取mp3
            path = load_open_path(conver_mp3_com, 1, 'wp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'rmvb', 'ts')
            # 显式验证路径
            if not isinstance(path, (str, os.PathLike)):
                raise ValueError("必须提供有效路径！")
            if not path:
                return
            # 获取 FFmpeg 路径
            ffmpeg_path = get_ffmpeg_path()
            if not ffmpeg_path:
                messagebox.showerror("错误", "未找到 FFmpeg！请下载并放入项目/bin目录。")
                return

            # 分割路径和扩展名
            dirfn, extfn = os.path.split(path)
            basename, ext = os.path.splitext(extfn)

            # 输出目录选择（根据复选框 con_var）
            if con_var.get() == 1:
                dirfn = self.mp3libery

            # 生成输出路径（确保扩展名为 .mp3）
            outfn = os.path.join(dirfn, f"{basename}.mp3")

            # 构建 FFmpeg 命令
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', path,  # 输入文件
                '-vn',
                '-c:a',
                'libmp3lame',
                '-y',  # 覆盖已存在文件（可选）
                outfn  # 输出文件
            ]

            try:
                # 执行命令（捕获错误输出）
                subprocess.run(ffmpeg_cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=False)
                conver_info.set(f'从{basename}{ext}提取{basename}.mp3 OK!')
            except subprocess.CalledProcessError as e:
                print(f"FFmpeg 转换失败: {e.stderr}")
            except FileNotFoundError:
                print("错误: 未找到 FFmpeg，请确保已安装并添加到系统路径！")

        def conver_allmp3_com():
            # 批量转换mp3
            paths = load_open_path(conver_mp3_com, 2, 'wav', 'm4a', 'aac', 'flac', 'wma', 'ogg', 'aif', 'aiff', 'amr')
            # 显式验证路径
            if not paths:
                return

            # 获取 FFmpeg 路径
            ffmpeg_path = get_ffmpeg_path()
            if not ffmpeg_path:
                messagebox.showerror("错误", "未找到 FFmpeg！请下载并放入项目/bin目录。")
                return

            for path in paths:
                # 分割路径和扩展名
                dirfn, extfn = os.path.split(path)
                basename, ext = os.path.splitext(extfn)

                # 输出目录选择（根据复选框 con_var）
                if con_var.get() == 1:
                    dirfn = self.mp3libery

                # 生成输出路径（确保扩展名为 .mp3）
                outfn = os.path.join(dirfn, f"{basename}.mp3")

                if os.path.exists(outfn):
                    conver_info.set(f'{outfn}已存在，跳过!')
                    continue

                conver_info.set(f'正在进行转换，请稍候...')
                # 构建 FFmpeg 命令
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i', path,  # 输入文件
                    '-codec:a', 'libmp3lame',
                    '-q:a', '2',  # 质量参数（2=高质量，范围0-9）
                    '-y',  # 覆盖已存在文件（可选）
                    outfn  # 输出文件
                ]

                try:
                    # 执行命令（捕获错误输出）
                    subprocess.run(ffmpeg_cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=False)

                except subprocess.CalledProcessError as e:
                    print(f"FFmpeg 转换失败: {e.stderr}")
                except FileNotFoundError:
                    print("错误: 未找到 FFmpeg，请确保已安装并添加到系统路径！")
            conver_info.set(f'已全部转换完毕!')

        self.widgets['tp_texr1'].pack_forget()
        framtop = tkinter.ttk.Frame(self.widgets['tp_rf'])
        framtop.pack(side='top', fill="both", expand=1)

        conver_info = tkinter.StringVar()
        wid_suffix = tkinter.ttk.Label(framtop, textvariable=conver_info)

        conver_mp3 = tkinter.ttk.Button(framtop, text="单文件转换MP3", command=conver_mp3_com)
        conver_allmp3 = tkinter.ttk.Button(framtop, text="批量转换MP3", command=conver_allmp3_com)
        extract_mp3 = tkinter.ttk.Button(framtop, text="从视频提取MP3", command=extract_mp3_com)

        con_var = tkinter.IntVar()
        chb1 = tkinter.ttk.Checkbutton(framtop, text="转换到源目录", variable=con_var, onvalue=0)
        chb2 = tkinter.ttk.Checkbutton(framtop, text="转换到曲库目录", variable=con_var, onvalue=1)
        canel = tkinter.ttk.Button(framtop, text="退出MP3转换", command=canel_btn)

        wid_suffix.grid(row=0, column=0, columnspan=2, pady=2, sticky='nsew')

        chb1.grid(row=1, column=0, columnspan=1, pady=2, sticky='nsew')
        chb2.grid(row=1, column=1, columnspan=1, pady=2, sticky='nsew')

        conver_mp3.grid(row=2, column=0, columnspan=1, pady=2, sticky='nsew')
        extract_mp3.grid(row=2, column=1, columnspan=1, pady=2, sticky='nsew')

        conver_allmp3.grid(row=3, column=0, columnspan=1, pady=2, sticky='nsew')
        canel.grid(row=3, column=1, columnspan=1, pady=2, sticky='nsew')

    def load_lddc(self):
        # 启动lddc项目搜索歌词
        if self.lddc:
            return
        subprocess.Popen('LDDC/LDDC.exe', stderr=subprocess.PIPE, stdout=subprocess.PIPE)  # 执行命令（捕获错误输出）
        self.lddc = True

    def format_mp3name(self):
        # 曲库文件名格式化
        for filename in os.listdir(self.mp3libery):
            if filename.endswith('.mp3'):
                mp3fn = os.path.join(self.mp3libery, filename)  # 构造完整的文件路径
                lrc = mp3fn.replace('.mp3', '.lrc')
                if '-' in mp3fn:
                    newmp3fn = mp3fn.replace('-', '_')
                    newlrc = lrc.replace('-', '_')
                    if not os.path.exists(newmp3fn):
                        os.rename(mp3fn, newmp3fn)
                    if os.path.exists(lrc) and not os.path.exists(newlrc):
                        os.rename(lrc, newlrc)
        print('文件名格式化完毕！')
        self.variables['lrcshow'].set(f'文件名格式化完毕！')

    def playerlist_syn(self):
        # 按播放列表copy mp3
        fn = load_open_path(self.playerlist_syn, 1, 'lst', title='请选择一个音乐播放列表文件')
        # 显式验证路径
        if not isinstance(fn, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not fn:
            return
        mp3folder = load_open_path(self.playerlist_syn, 3, title='请选择U盘存放目录')

        if not isinstance(mp3folder, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not mp3folder:
            return
        try:  # 先尝试以utf-8格式打开文件
            with open(fn, "r", encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:  # 如果utf-8打开失败，则尝试用gbk格式打开
                with open(fn, "r", encoding='gbk', errors='ignore') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:  # 如果第2次仍失败，忽略错误，以utf-8强制打开
                with open(fn, "r", encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

        fns = os.listdir(mp3folder)

        for mp3fn in lines:
            if os.path.basename(mp3fn.strip()) not in fns:
                if os.path.exists(mp3fn.strip()):
                    print(mp3fn.strip(), mp3folder)
                    shutil.copy(mp3fn.strip(), mp3folder)
                    print(f"已将文件{mp3fn.strip()}复制到{mp3folder}")
            else:
                file1 = mp3fn.strip()
                file2 = os.path.join(mp3folder, os.path.basename(mp3fn.strip()))
                if is_updated_by_hash(file1, file2, method='md5'):
                    shutil.copy(file1, mp3folder)
                    print(f'已更新目标文件 {mp3fn.strip()}')
        print('==========>over!')

        for line in lines:
            lrcfn = line.strip().replace('.mp3', '.lrc')
            if os.path.exists(lrcfn):
                if os.path.basename(lrcfn) not in fns:
                    shutil.copy(lrcfn, mp3folder)
                    print(f"已将文件{lrcfn}复制到{mp3folder}")
                else:
                    file2 = os.path.join(mp3folder, os.path.basename(lrcfn))
                    if is_updated_by_hash(lrcfn, file2, method='md5'):
                        shutil.copy(lrcfn, mp3folder)
                        print(f'已更新目标文件 {lrcfn}')

    def googls_cover(self):
        # 在googls搜索封面

        parts = os.path.basename(self.tp_mp3path).split('_')
        album = mp3info_extract(self.tp_mp3path)[0][1]
        if len(parts) != 2:
            return

        artist = parts[0]
        title, extension = parts[1].split('.')
        # if title != album:
        #     title = album

        print(f'开始在Googls搜索{artist}-{title}-的封面...')
        # encoded_text = urllib.parse.quote(f'{artist}+{title}', safe='')  # 要编码的中文文本
        encoded_text = urllib.parse.quote(f'{title}+{artist}', safe='')  # 要编码的中文文本

        # 图片搜索：tbm = isch
        # 视频搜索：tbm = vid
        # 新闻搜索：tbm = nws
        # 购物搜索：tbm = shop
        myurl = 'https://www.google.com/search?tbm=isch&q=' + encoded_text

        try:
            # 获取浏览器会话
            self.get_driver()
            self.driver.get(myurl)

        except WebDriverException as e:
            print(f"出现异常: {e}")
            # 如果出现异常，关闭浏览器会话并设置为None，以便下次重新创建
            if not self.driver:
                self.driver.quit()
            self.driver = None

    def googls_downloadenter(self):
        # 从googls下载封面

        if not self.driver:
            print('请先点击左侧"从googls搜索封面”按钮')
            return

        parts = os.path.basename(self.tp_mp3path).split('_')
        album = mp3info_extract(self.tp_mp3path)[0][1]
        if len(parts) != 2:
            return

        artist = parts[0]
        title, extension = parts[1].split('.')
        if title != album:
            title = album
        path = os.path.join(get_covers_dir(), f'{artist}_{title}.jpg')

        yet = tkinter.messagebox.askyesno("下载图片并替换封面确认", '点击按钮图片将被下载到封面库，同时更新MP3封面！')
        if yet:
            # 获取所选择图片的URL（CSS 选择器依赖 Google 页面结构，失败则优雅退出）
            try:
                first_image = self.driver.find_element(By.CSS_SELECTOR, 'img.sFlh5c')
            except NoSuchElementException:
                print('未能在页面中定位封面图片元素（Google 页面结构可能已变化）')
                self.variables['lrcshow'].set('封面元素定位失败，请稍后重试')
                return
            img_url = first_image.get_attribute('src')
            if img_url.startswith('data:image/jpeg;base64,'):
                base64_data = img_url.split(',', 1)[1]  # 使用split方法去除前缀
                # 解码Base64数据
                decoded_data = base64.b64decode(base64_data)
                with open(path, "wb") as img_file:
                    img_file.write(decoded_data)
                audiofile = eyed3.load(self.tp_mp3path)
                cover_image = open(path, "rb").read()  # 创建封面图片对象
                # 将封面图片添加到MP3文件中（使用标签类型 3）
                audiofile.tag.images.set(3, cover_image, "image/jpeg", "Front cover")

                audiofile.tag.save()  # 保存MP3文件
                print(f'已base64模式给{self.tp_mp3path}填加了专辑封面')
            else:
                response = requests.get(img_url)
                if response.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(response.content)
                    print("%s已下载" % path)

                    audiofile = eyed3.load(self.tp_mp3path)
                    cover_image = open(path, "rb").read()  # 创建封面图片对象
                    # 将封面图片添加到MP3文件中（使用标签类型 3）
                    audiofile.tag.images.set(3, cover_image, "image/jpeg", "Front cover")

                    audiofile.tag.save()  # 保存MP3文件
                    print(f'已url模式给{self.tp_mp3path}填加了专辑封面')
                else:
                    print("下载失败")

            # 更新封面显示
            image = Image.open(path)
            # 调整图像大小
            image = image.resize((500, 280), resample=Image.LANCZOS)
            imageVer = ImageTk.PhotoImage(image)
            self.widgets["tp_labr1"].config(image=imageVer)
            self.widgets["tp_labr1"].image = imageVer
        else:
            return

    def download_cover(self):
        # 从歌词网下载封面
        parts = os.path.basename(self.tp_mp3path).split('_')
        if len(parts) != 2:
            return
        artist = parts[0]
        title, extension = parts[1].split('.')
        print(f'开始在歌词网搜索-{title}-的封面...')
        encoded_text = urllib.parse.quote(title, safe='')

        # 要编码的中文文本
        myurl = 'https://zh.followlyrics.com/search?name=' + encoded_text
        # 使用 urllib.parse.quote 对文本进行 URL 编码
        try:
            # 获取浏览器会话
            self.get_driver()
            self.driver.get(myurl)
        except WebDriverException as e:
            print(f"出现异常: {e}")
            # 如果出现异常，关闭浏览器会话并设置为None，以便下次重新创建
            if self.driver is not None:
                self.driver.quit()
            driver = None

        # 找到包含搜索结果的元素，一个包含搜索结果的div或表格
        try:
            table = self.driver.find_element(By.CLASS_NAME, 'table-striped')
        except NoSuchElementException:
            print('搜索结果为空')
            return

        # 初始化空列表以存储数据
        歌曲列表 = []
        歌手列表 = []
        专辑列表 = []
        歌词链接列表 = []
        table_html = table.get_attribute('innerHTML')
        # 使用BeautifulSoup解析HTML内容
        soup = BeautifulSoup(table_html, 'html.parser')
        lrcname = self.tp_mp3path.replace('.mp3', '.lrc')
        dowloadurl = []
        # 解析表格内容从表格中提取数据
        if soup:
            rows = soup.find_all('tr')
            for row in rows[1:]:  # 跳过表头行
                columns = row.find_all('td')
                if len(columns) >= 4:
                    歌曲 = columns[0].text.strip()
                    歌手 = columns[1].text.strip()
                    专辑 = columns[2].text.strip()
                    歌词链接 = columns[3].find('a')['href']

                    歌曲列表.append(歌曲)
                    歌手列表.append(歌手)
                    专辑列表.append(专辑)
                    歌词链接列表.append(歌词链接)
        else:
            print('BeautifulSoup解析HTML内容没有结果')

        findok = False
        for i in range(len(歌曲列表)):
            if 歌曲列表[i] == title and 歌手列表[i] == artist:
                findok = True
                with open(r'config\mp3info.txt', 'r', encoding='utf-8') as f:
                    content = f.read()
                content = f"{content}{歌手列表[i]}：{歌曲列表[i]}：{专辑列表[i]}\n"
                with open(r'config\mp3info.txt', 'w', encoding='utf-8') as f:
                    f.write(content)

                self.driver.get(歌词链接列表[i])
                coverjpg = self.driver.find_element(By.CLASS_NAME, 'card-img-top')
                image_url = coverjpg.get_attribute('src')
                imagefn = self.tp_mp3path.replace('.mp3', '.jpg')
                # 执行HTTP GET请求以下载文件
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                                         " (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"}
                response = requests.get(image_url, headers=headers)

                # 检查响应状态码
                if response.status_code == 200:
                    # 以二进制模式保存文件
                    with open(imagefn, "wb") as file:
                        file.write(response.content)

                    print(f"文件已成功下载并另存为 '{imagefn}'")
                    return True

                else:
                    print(f"'{lrcname}'文件下载失败")
                    return False
            else:
                print('没找到与歌手与歌名同时匹配的内容')

    def get_driver(self):
        # 初始化 webdrive
        if self.driver is None:
            # 如果浏览器会话不存在，创建一个新的浏览器会话
            chrome_options = webdriver.ChromeOptions()  # 创建ChromeOptions对象
            chrome_options.add_argument('--window-size=1250,1000')  # 设置窗口大小，width和height分别是窗口的宽度和高度
            chrome_options.add_argument('--window-position=2060,560')  # 设置窗口位置，x和y分别是窗口左上角的横纵坐标
            chrome_options.add_argument('--disable-notifications')  # 禁用通知
            self.driver = webdriver.Chrome(options=chrome_options)
            return self.driver

    def help_show(self):
        # 打开帮助文件
        with open('config/readme.md', encoding='utf-8') as f:
            content = f.read()
        self.widgets['tp_texr1'].delete("1.0", tkinter.END)
        self.widgets['tp_texr1'].insert(tkinter.END, content)

    def convert_srt_to_lrc(self):
        # 将srt格式歌词转换成lrc格式
        srt_file_path = load_open_path(self.convert_srt_to_lrc, 1, 'srt')
        # 显式验证路径
        if not isinstance(srt_file_path, (str, os.PathLike)):
            raise ValueError("必须提供有效路径！")
        if not srt_file_path:
            return

        lrc_file_path = srt_file_path.replace('.srt', '.lrc')
        with open(srt_file_path, 'r', encoding='utf-8') as srt_file:
            srt_content = srt_file.read()

        # Regular expression to match SRT time format
        srt_blocks = re.split(r'\n\s*\n', srt_content.strip())
        lrc_lines = []
        for block in srt_blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                time_line = lines[1]
                start_time, end_time = time_line.split(' --> ')
                print(start_time)
                print(end_time)
                start_time_lrc = srt_time_to_lrc_time(start_time)
                text_lines = lines[2:]
                text = ' '.join(text_lines)
                lrc_lines.append(f"[{start_time_lrc}] {text}")

        with open(lrc_file_path, 'w', encoding='utf-8') as lrc_file:
            lrc_file.write('\n'.join(lrc_lines))

    # 自动播放 / 文件关联区 ******************************  自动播放区 ******************************************

    def open_and_play(self, mp3path):
        """供文件关联/双击 mp3 调用：清空列表 → 加入本次曲目 → 播放 → 载入同名 lrc。

        行为符合一般习惯——双击一首歌就只听这首（清空旧列表）。
        但对「在资源管理器里多选 N 首后回车」做了批次感知：这些文件会被单实例
        逐个快速转发过来，只有「批次第一首」清空并播放，1 秒内到达的后续曲目仅入队，
        从而既支持单击替换，也支持多选连播，二者不冲突。

        play() 内部已实现「查找同名 lrc，存在则载入歌词」，本函数无需重复处理歌词。
        """
        if not mp3path or not os.path.exists(mp3path):
            self.variables['lrcshow'].set('文件不存在！')
            return
        mp3path = os.path.normpath(mp3path)
        if not mp3path.lower().endswith('.mp3'):
            self.variables['lrcshow'].set('只支持 mp3 文件！')
            return

        # 将主窗口恢复并提到最前
        try:
            self.deiconify()
            self.state('normal')
            self.lift()
            self.focus_force()
        except tkinter.TclError:
            pass

        # 判断是否为新的一次操作（与上次到达间隔 > 1 秒视为新批次）
        now = time.time()
        is_new_batch = (now - getattr(self, '_last_open_ts', 0.0)) > 1.0
        self._last_open_ts = now

        if is_new_batch:
            # 新双击：停止当前播放并清空旧列表（含开机恢复的列表）
            self.mystop()
            self.list_clear()

        # 追加本次曲目到列表框与播放列表
        self.widgets['lisb1'].insert('end', os.path.basename(mp3path).replace('.mp3', ''))
        self.playlist.append(mp3path)
        target = len(self.playlist) - 1

        if is_new_batch:
            # 批次首曲：切到列表模式（便于多选连播）、选中并立即播放
            self.variables['play_mode'].set(2)
            self.index = target
            self.widgets['lisb1'].selection_clear(0, tkinter.END)
            self.widgets['lisb1'].selection_set(self.index)
            self.widgets['lisb1'].see(self.index)
            self.with_selitem()
            # 播放（play() 会自动查找并载入同名 lrc 歌词）
            self.play()
        # 同批次后续曲目：仅入队，不打断正在播放的第一首

    def start_ipc_server(self):
        """启动本地单实例监听线程。

        当用户再次双击 mp3 时，新进程会把文件路径转发到这里，
        由当前已运行的实例负责播放，避免重复开窗口。
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT))
            sock.listen(5)
        except OSError:
            # 端口被占用（通常意味着已有实例在监听），放弃监听
            self._ipc_sock = None
            return
        self._ipc_sock = sock
        threading.Thread(target=self._ipc_loop, daemon=True).start()

    def _ipc_loop(self):
        """IPC 监听循环：接收转发来的 mp3 路径并在主线程播放。"""
        while True:
            try:
                conn, _ = self._ipc_sock.accept()
            except OSError:
                break  # 套接字已关闭
            try:
                data = conn.recv(4096)
            finally:
                conn.close()
            if data:
                path = data.decode('utf-8', errors='ignore').strip()
                if path:
                    # 跨线程：交回 Tk 主循环执行
                    self.after(0, self.open_and_play, path)


# 主类终止位置 ******************************  主类终止位置 ******************************************************主类终止位置

def lrcfile_to_sec_tex(lrc):
    # 将lrc文件转换成（秒数+文本）的元组列表，
    format_lrc(lrc)  # 先格式化lrc文件，防止意外
    lrc_list = []
    with open(lrc, encoding='utf-8') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        match = re.match(r'\[(\d+:\d+\.\d+)\](.*)', line)
        if match:  # 使用正则表达式提取时间戳和文本
            timestamp = match.group(1)
            text = match.group(2)
            # 将时间戳转换为秒数
            minutes, seconds = map(float, timestamp.split(':'))
            total_seconds = minutes * 60 + seconds
            lrc_list.append((total_seconds, text))
    return lrc_list


def format_lrc(file_path):
    # 格式化lrc文件
    lrc_data = []

    try:  # 先尝试以utf-8格式打开文件
        with open(file_path, "r", encoding='utf-8') as f:
            text_content = f.read()
    except UnicodeDecodeError:
        try:  # 如果utf-8打开失败，则尝试用gbk格式打开
            with open(file_path, "r", encoding='gbk', errors='ignore') as f:
                text_content = f.read()
        except UnicodeDecodeError:  # 如果第2次仍失败，忽略错误，以utf-8强制打开
            with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
                text_content = f.read()

    lines = text_content.strip().split('\n')
    for line in lines:
        # 检查字符串line是否以"["开头，判断是否是一个包含时间戳和歌词内容的行。
        if line.startswith("["):
            # 使用正则表达式提取时间戳和歌词内容
            match = re.match(r'\[(\d+:\d+\.\d+)\](.*)', line)
            if match:
                timestamp_str, lyrics = match.groups()
                timestamp = parse_timestamp(timestamp_str)
                lrc_data.append((timestamp, lyrics))
    # 根据时间戳排序歌词数据
    lrc_data.sort(key=lambda x: x[0])

    lensong = mp3info_extract(file_path.replace('.lrc', '.mp3'))[1]

    # 如果歌曲的实际长度和最后一行歌词的时间不同，则添加一个空的歌词行表示结束
    Tailline = (lensong, '')

    if len(lrc_data) > 0:

        if lrc_data[-1][1] != '':
            lrc_data.append(Tailline)

        if lrc_data[-1][1] == '' and lrc_data[-1][0] != lensong:
            lrc_data[-1] = Tailline

    uplrc = []

    # 兜底：空歌词文件（无任何合法时间戳行）时直接以文件名作为占位行，
    # 否则下面访问 lrc_data[0] 会抛 IndexError。
    if not lrc_data:
        acter = os.path.basename(file_path).split('.')[0].replace('_', ' ')
        lrc_data.append((datetime.timedelta(0), acter))

    if lrc_data[0][0] != datetime.timedelta(0):
        acter = os.path.basename(file_path).split('.')[0].replace('_', ' ')
        lrc_data.insert(0, (datetime.timedelta(0), acter))

    lastime = mp3info_extract(file_path.replace('.lrc', '.mp3'))[1]
    lrc_data.append((datetime.timedelta(seconds=lastime), None))

    for i, (timestamp, lyrics) in enumerate(lrc_data):
        # 特别处理最后一行：即使lyrics为None，也加入只有时间戳的行
        if lyrics or i == len(lrc_data) - 1:
            updata_content = f"[{format_timestamp(timestamp)}]{lyrics.lstrip() if lyrics else ''}"
            uplrc.append(updata_content)

    updated_content = "\n".join(uplrc)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)


def hms_to_milliseconds(hms_str):
    """
    将 分:秒:毫秒格式的字符串转换为毫秒数
    参数:
        hms_str: 格式为"HH:MM:SS"或"H:MM:SS"的字符串
    返回:
        对应的毫秒数
    """
    try:
        # 分割时、分、秒
        minutes, seconds, milliseconds = hms_str.split(':')

        # 转换为整数

        minutes = int(minutes)
        seconds = int(seconds)  # 支持带小数点的秒数
        milliseconds = int(milliseconds)

        # 计算总毫秒数
        total_milliseconds = minutes * 60000 + seconds * 1000 + milliseconds

        return int(total_milliseconds)
    except (ValueError, AttributeError):
        # 处理格式错误的情况
        raise ValueError(f"无效的时间格式: '{hms_str}'，应为 'HH:MM:SS'")


def milliseconds_to_hms(milliseconds):
    # 毫秒转换成时：分：秒的格式字符串
    # 将毫秒转换为秒
    seconds = milliseconds // 1000
    # 计算小时、分钟和秒
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    # 格式化字符串
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def srt_time_to_lrc_time(srt_time):
    # 将srt格式的时间戳转换成lrc格式的
    parts = re.split('[:,]', srt_time)
    if len(parts) == 4:  # 检查是否为4部分，即包含逗号分隔的毫秒数
        hours, minutes, seconds, milliseconds = parts
    else:
        hours, minutes, seconds = parts
        milliseconds = '000'  # 如果没有毫秒数，默认为000

    hours, minutes, seconds = float(hours), float(minutes), float(seconds)
    total_minutes = int(hours * 60 + minutes)
    total_seconds = int(seconds)
    milliseconds = int((float(milliseconds) / 1000) * 1000)  # 确保毫秒数是整数
    return f"{total_minutes:02}:{total_seconds:02}.{milliseconds:03}"


def resize_and_save_image(fn, w, h, outfn):
    # 按宽高裁剪图片
    try:
        # 打开图像文件
        image = Image.open(fn)
        # 调整图像大小
        image = image.resize((w, h), resample=Image.LANCZOS)
        # 保存调整后的图像
        image.save(outfn)
    except Exception as e:
        print(f"Error: {e}")


class ToolTip(object):
    # 提词器
    '''ToolTip类定义了如何创建和显示tooltip。
    create_tooltip函数将tooltip绑定到指定的部件上。
    当鼠标光标进入（<Enter>事件）和离开（<Leave>事件）按钮区域时，tooltip将会显示和隐藏。'''

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tkinter.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tkinter.Label(tw, text=self.text, justify=tkinter.LEFT,
                              background="#ffffe0", relief=tkinter.SOLID, borderwidth=1,
                              font=("tahoma", "10", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


def create_tooltip(widget, text):
    # 在 widget控件鼠标悬停时显示提示词
    tooltip = ToolTip(widget)
    widget.bind('<Enter>', lambda event: tooltip.showtip(text))
    widget.bind('<Leave>', lambda event: tooltip.hidetip())


def get_covers_dir():
    """封面下载目录：优先读取 config/funpath.ini 的 covers_dir，
    否则默认用程序目录下的 covers/，避免硬编码绝对路径。
    """
    covers = None
    try:
        with open('config/funpath.ini', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('covers_dir '):
                    covers = line.split(' ', 1)[1]
                    break
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f'读取 covers_dir 配置出错: {e}')
    if not covers:
        covers = os.path.join(BASE_DIR, 'covers')
    os.makedirs(covers, exist_ok=True)
    return covers


# mp3 元数据缓存：键为 (路径, 修改时间)，编辑元数据后 mtime 变化即自动失效
_mp3info_cache = {}


def mp3info_extract(mp3fn):
    # 提取mp3信息（带缓存：避免选歌/列表循环时对同一文件反复解析磁盘）
    try:
        mtime = os.path.getmtime(mp3fn)
    except OSError:
        mtime = None

    cache_key = (mp3fn, mtime)
    cached = _mp3info_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        audio = MP3(mp3fn)
    except Exception:
        # 文件缺失/损坏/非法：返回安全默认，避免上层 [1] 取时长时崩溃
        return (('标题', '专辑', '演唱者'), 0)
    # 提取歌曲信息
    song_title = audio.get('TIT2', '标题')  # 使用'TIT2'来提取歌曲名称
    album = audio.get('TALB', '专辑')  # 使用'TALB'来提取专辑名称
    artist = audio.get('TPE1', '演唱者')  # 使用'TPE1'来提取演唱者名称
    song_length_seconds = int(audio.info.length)
    gqinfo = (song_title, album, artist)
    result = (gqinfo, song_length_seconds)

    # 清理同一文件的旧 mtime 缓存项，防止字典无限膨胀
    for k in [k for k in _mp3info_cache if k[0] == mp3fn]:
        del _mp3info_cache[k]
    _mp3info_cache[cache_key] = result
    return result


def get_mp3image(mp3_file_path):
    # 提取 MP3的 封面

    audiofile = eyed3.load(mp3_file_path)  # 创建一个eyed3的MP3对象
    if audiofile.tag.images:  # 获取封面图片（如果有的话）
        cover_image_data = audiofile.tag.images[0].image_data
        # 将封面图片保存到文件
        with open("images/extracted_cover.jpg", "wb") as file:
            file.write(cover_image_data)
            return True
    else:
        return False


def updata_dir(dir1, dir2):
    # 先判断文件是否更新过，是则同步文件
    i = 0
    k = 0
    for fn in os.listdir(dir1):
        if fn.endswith(('.py', '.json', '.ini', '.txt', '.lrc', '.png', '.jpg', '.epub', '.pdf')):
            file1 = os.path.join(dir1, fn)
            file2 = os.path.join(dir2, fn)
            if fn in os.listdir(dir2):
                if is_updated_by_hash(file1, file2, method='md5'):
                    shutil.copy(file1, dir2)
                    i += 1
                    print(f'已更新目标文件 {dir2} {fn}')
                else:
                    # print(f'目标文件 {dir2} {fn} 无需更新')
                    pass
            else:
                shutil.copy(file1, dir2)
                k += 1
                print(f'已增加目标文件 {dir2} {fn}')

    print(f"本次更新共新增 {k} 个文件，更新 {i} 个文件")


def file_hash(filename, method='md5'):
    hash_method = getattr(hashlib, method)()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_method.update(chunk)
    return hash_method.hexdigest()


def is_updated_by_hash(file1, file2, method='md5'):
    hash1 = file_hash(file1, method)
    hash2 = file_hash(file2, method)
    return hash1 != hash2


def parse_timestamp(timestamp_str):
    # 解析时间戳（格式：[分:秒.毫秒]） ，返回元组（分，秒，毫秒）
    minutes, seconds, milliseconds = map(int, re.split(r'[:.]', timestamp_str))
    return datetime.timedelta(minutes=minutes, seconds=seconds, milliseconds=milliseconds)


def format_timestamp(timestamp):
    # 格式化为 [分:秒.毫秒]  毫秒3位

    minutes, seconds = divmod(timestamp.seconds, 60)  # divmod（）返回一个包含两个参数相除后获得的商和余数的元组
    milliseconds = timestamp.microseconds // 1000
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def get_ffmpeg_path():
    """返回项目内或系统的 FFmpeg 路径"""
    # 1. 优先检查项目内的 FFmpeg
    project_ffmpeg = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg")
    if os.path.isfile(project_ffmpeg):
        return project_ffmpeg

    # 2. 检查系统路径中的 FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "ffmpeg"  # 返回命令名称
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None  # 未找到


def load_open_path(function, kid, *args, title=None):
    """更新指定函数的路径，用于打开和保存文件或文件夹

    Args:
        function: 调用的函数对象
        kid: 对话框类型 (1-单个文件, 2-多个文件, 3-文件夹, 4-保存文件)
        *args: 文件扩展名列表
        title: 自定义对话框标题
    """

    dic = {}
    try:
        with open('config/funpath.ini', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # 跳过空行
                    key, value = line.split(' ', 1)
                    dic[key] = value
    except FileNotFoundError:
        os.makedirs('config', exist_ok=True)
        open('config/funpath.ini', 'w').close()
    except Exception as e:
        print(f"读取配置文件出错: {e}")
        return None

    # 生成唯一存储键，包含函数名和操作类型
    storage_key = f"{function.__name__}_{kid}"
    # 设置初始目录
    # 设置初始目录
    initial_dir = dic.get(storage_key, dic.get(function.__name__, os.getcwd()))

    # 设置默认标题
    if title is None:
        title = {
            1: '请选择文件(单选)',
            2: '请选择文件(可多选)',
            3: '请选择一个文件夹',
            4: '请选择(输入)要保存的文件名'
        }.get(kid, '请选择')

    # 设置文件类型
    all_types = ';'.join([f"*.{suffix}" for suffix in args])
    filetypes = [('所有支持的类型', all_types)] + [(f"{suffix} 文件", f"*.{suffix}") for suffix in args] if args else []

    # 根据kid值选择对话框类型
    if kid == 1:
        openfn = tkinter.filedialog.askopenfilename(title=title, filetypes=filetypes, initialfile=initial_dir,
                                                    initialdir=os.path.dirname(initial_dir))
        if openfn:
            save_open_path(storage_key, openfn)

    elif kid == 2:
        openfn = tkinter.filedialog.askopenfilenames(title=title, filetypes=filetypes, initialfile=initial_dir,
                                                     initialdir=os.path.dirname(initial_dir))
        if openfn:
            save_open_path(storage_key, os.path.dirname(openfn[0]))

    elif kid == 3:
        openfn = tkinter.filedialog.askdirectory(title=title, initialdir=initial_dir)
        if openfn:
            save_open_path(storage_key, openfn)


    elif kid == 4:
        openfn = tkinter.filedialog.asksaveasfilename(title=title, initialdir=initial_dir)
        if openfn:
            save_open_path(storage_key, os.path.dirname(openfn))

    else:
        return None

    return openfn


def save_open_path(storage_key, new_path):
    """保存函数的工作目录到配置文件"""
    # 读取现有配置
    dic = {}
    try:
        with open('config/funpath.ini', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # 跳过空行
                    key, value = line.split(' ', 1)
                    dic[key] = value
    except FileNotFoundError:
        os.makedirs('config', exist_ok=True)
    except Exception as e:
        print(f"读取配置文件出错: {e}")
        return

    # 更新配置
    dic[storage_key] = new_path

    # 写入配置
    try:
        with open('config/funpath.ini', 'w', encoding='utf-8') as f:
            for key, value in sorted(dic.items()):  # 按key排序便于查看
                f.write(f"{key} {value}\n")
    except Exception as e:
        print(f"保存配置文件出错: {e}")


# ============ 单实例 / 文件关联 模块级配置与工具 ============

# 程序根目录：兼容 PyInstaller 打包（frozen）与脚本两种运行方式
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SINGLE_INSTANCE_HOST = '127.0.0.1'
SINGLE_INSTANCE_PORT = 50573  # 本地单实例通信端口
PROG_ID = 'Muse.mp3'          # 注册表 ProgId


def get_launch_command():
    """返回用于文件关联的可执行命令前缀（不含 "%1" 参数）。"""
    if getattr(sys, 'frozen', False):
        # 打包成 exe：直接用自身可执行文件
        return f'"{sys.executable}"'
    # 脚本模式：优先用 pythonw.exe 启动，避免弹出控制台黑窗
    pyw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    runner = pyw if os.path.exists(pyw) else sys.executable
    script = os.path.join(BASE_DIR, 'muse.py')
    return f'"{runner}" "{script}"'


def register_file_association():
    """把 Muse 注册为 .mp3 的打开方式（写入 HKCU，无需管理员）。

    说明：现代 Windows 因 UserChoice 哈希保护，无法由程序静默「强制」设为唯一
    默认应用；但注册后 Muse 会出现在右键「打开方式」列表中，用户在
    「设置→默认应用」里一键即可设为默认。若 .mp3 当前没有 UserChoice 覆盖，
    则本注册的 ProgId 直接生效。
    """
    if platform.system() != 'Windows':
        print('文件关联仅支持 Windows')
        return False
    import winreg
    import ctypes
    cmd = get_launch_command() + ' "%1"'
    icon = os.path.join(BASE_DIR, 'images', 'v2.ico')
    try:
        # 1) 定义 ProgId 及其打开命令、图标
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              rf'Software\Classes\{PROG_ID}') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, 'Muse 音乐播放器')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              rf'Software\Classes\{PROG_ID}\DefaultIcon') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, icon)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              rf'Software\Classes\{PROG_ID}\shell\open\command') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, cmd)
        # 2) 把 ProgId 关联到 .mp3（OpenWithProgids 使其出现在「打开方式」）
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r'Software\Classes\.mp3\OpenWithProgids') as k:
            winreg.SetValueEx(k, PROG_ID, 0, winreg.REG_NONE, b'')
        # 3) 通知资源管理器刷新文件关联（SHCNE_ASSOCCHANGED）
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
        print('已注册：Muse 现已出现在 mp3 的「打开方式」中。')
        print('如需设为默认：右键任意 mp3 → 打开方式 → 选择其他应用 → 选 Muse → 始终。')
        return True
    except Exception as e:
        print(f'注册文件关联失败: {e}')
        return False


def unregister_file_association():
    """移除文件关联注册项。"""
    if platform.system() != 'Windows':
        return False
    import winreg
    import ctypes
    try:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Classes\.mp3\OpenWithProgids',
                                0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, PROG_ID)
        except FileNotFoundError:
            pass
        # 递归删除 ProgId 子树
        for sub in (rf'Software\Classes\{PROG_ID}\shell\open\command',
                    rf'Software\Classes\{PROG_ID}\shell\open',
                    rf'Software\Classes\{PROG_ID}\shell',
                    rf'Software\Classes\{PROG_ID}\DefaultIcon',
                    rf'Software\Classes\{PROG_ID}'):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except FileNotFoundError:
                pass
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
        print('已移除 Muse 的 mp3 文件关联。')
        return True
    except Exception as e:
        print(f'移除文件关联失败: {e}')
        return False


def try_forward_to_running(path):
    """若已有实例在运行，把文件路径转发给它并返回 True；否则返回 False。"""
    try:
        with socket.create_connection((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT),
                                      timeout=0.6) as s:
            s.sendall(os.path.abspath(path).encode('utf-8'))
        return True
    except OSError:
        return False


if __name__ == "__main__":

    # 关键：双击 mp3 启动时，工作目录会是 mp3 所在目录，导致 images/、config/
    # 等相对路径全部失效。这里统一切回程序根目录。
    os.chdir(BASE_DIR)

    arg_path = sys.argv[1] if len(sys.argv) > 1 else None

    # 注册 / 反注册 文件关联（命令行开关）
    if arg_path in ('--register', '/register'):
        register_file_association()
        sys.exit(0)
    if arg_path in ('--unregister', '/unregister'):
        unregister_file_association()
        sys.exit(0)

    # 单实例：若已有 Muse 在运行，转发待播放文件后直接退出
    if arg_path and os.path.isfile(arg_path):
        if try_forward_to_running(arg_path):
            sys.exit(0)

    app = Application()

    # 本进程即为主实例，若带 mp3 参数则等界面就绪后自动播放
    if arg_path and os.path.isfile(arg_path):
        app.after(800, app.open_and_play, arg_path)

    app.mainloop()
