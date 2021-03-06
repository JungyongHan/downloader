# -*- coding: utf-8 -*-
#########################################################
# python
import os
from datetime import datetime
import traceback
import logging
import subprocess
import time
import re
import json
import requests
import urllib
import urllib2
import lxml.html
from enum import Enum
import threading

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_
from telepot import Bot, glance
from telepot.loop import MessageLoop
from time import sleep
import telepot
from flask_socketio import SocketIO, emit, send

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, path_app_root
from framework.job import Job
from framework.util import Util
from system.logic import SystemLogic

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelDownloaderItem
from .logic_transmission import LogicTransmission
from .logic_downloadstation import LogicDownloadStation
from .logic_qbittorrent import LogicQbittorrent
from .logic_aria2 import LogicAria2

import plugin


#########################################################

class LogicNormal(object):
    
   
    pre_telegram_title = None
    @staticmethod
    def send_telegram(where, title):
        try:
            if LogicNormal.pre_telegram_title == title:
                return
            else:
                LogicNormal.pre_telegram_title = title
            if where == '0':
                msg = '트랜스미션'
            elif where == '1':
                msg = '다운로드스테이션'
            elif where == '2':
                msg = '큐빗토렌트'
            elif where == '3':
                msg = 'aria2'
            msg += '\n%s 다운로드 완료' % title 
            import framework.common.notify as Notify
            Notify.send_message(msg, message_id='downloader_completed_remove')
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())



    @staticmethod
    def add_download_by_request(request):
        try:
            download_url = request.form['download_url'] if 'download_url' in request.form else None

            if download_url is None:
                return {'ret':'fail'}
            default_torrent_program = request.form['default_torrent_program'] if 'default_torrent_program' in request.form else None
            download_path = request.form['download_path'] if 'download_path'  in request.form else None

            return LogicNormal.add_download2(download_url, default_torrent_program, download_path)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret = {'ret':'error'}

    
    @staticmethod
    def add_download2(download_url, default_torrent_program, download_path, request_type='web', request_sub_type=''):
        try:
            setting_list = db.session.query(ModelSetting).all()
            arg = Util.db_list_to_dict(setting_list)
            if default_torrent_program is None:
                default_torrent_program = arg['default_torrent_program']
           
            if download_path is not None and download_path.strip() == '':
                download_path = None
            if default_torrent_program == '0':
                if download_path is None:
                    download_path = arg['transmission_default_path']
                ret = LogicTransmission.add_download(download_url, download_path)
            elif default_torrent_program == '1':
                if download_path is None:
                    download_path = arg['downloadstation_default_path']
                ret = LogicDownloadStation.add_download(download_url, download_path)
            elif default_torrent_program == '2':
                if download_path is None:
                    download_path = arg['qbittorrnet_default_path']
                ret = LogicQbittorrent.add_download(download_url, download_path)
            elif default_torrent_program == '3':
                ret = LogicAria2.add_download(download_url, download_path if download_path is not None else arg['aria2_default_path'])

            ret['default_torrent_program'] = default_torrent_program
            ret['downloader_item_id'] = ModelDownloaderItem.save(ret, request_type, request_sub_type)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret = {'ret':'error'}
        finally:
            return ret


    @staticmethod
    def program_init():
        try:
            LogicTransmission.program_init()
            LogicDownloadStation.program_init()
            LogicQbittorrent.program_init()
            LogicAria2.program_init()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return 'fail'
    


    @staticmethod
    def scheduler_function():
        try:
            logger.debug('scheduler_function')
            
            LogicTransmission.scheduler_function()
            LogicDownloadStation.scheduler_function()
            LogicQbittorrent.scheduler_function()
            LogicAria2.scheduler_function()
            
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())




    

    
    
    @staticmethod
    def add_download_api(request):
        try:
            setting_list = db.session.query(ModelSetting).all()
            arg = Util.db_list_to_dict(setting_list)
            download_url = request.args.get('download_url')

            if download_url is None:
                return {'ret':'fail'}
            
            default_torrent_program = request.args.get('default_torrent_program')
            
            download_path = request.args.get('download_path')
            return LogicNormal.add_download2(download_url, default_torrent_program, download_path)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return 'fail'
    
    

    
  

    @staticmethod
    def is_available_normal_download():
        try:
            ret = False
            default_torrent_program = db.session.query(ModelSetting).filter_by(key='default_torrent_program').first().value
            if default_torrent_program == '1':
                ret = True
            else:
                transmission_normal_file_download = (db.session.query(ModelSetting).filter_by(key='transmission_normal_file_download').first().value == 'True')
                ret = transmission_normal_file_download
            return ret
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    




    
   



    @staticmethod
    def filelist(req):
        try:
            ret = {}
            page = 1
            page_size = int(db.session.query(ModelSetting).filter_by(key='web_page_size').first().value)
            job_id = ''
            search = ''
            if 'page' in req.form:
                page = int(req.form['page'])
            if 'search_word' in req.form:
                search = req.form['search_word']
            
            query = db.session.query(ModelDownloaderItem)
            if search != '':
                query = query.filter(ModelDownloaderItem.title.like('%'+search+'%'))
            request_type = req.form['request_type']
            if request_type != 'all':
                query = query.filter(ModelDownloaderItem.request_type == request_type)
            count = query.count()
            query = (query.order_by(desc(ModelDownloaderItem.id))
                        .limit(page_size)
                        .offset((page-1)*page_size)
                )
            logger.debug('ModelDownloaderItem count:%s', count)
            lists = query.all()
            ret['list'] = [item.as_dict() for item in lists]
            ret['paging'] = Util.get_paging_info(count, page, page_size)
            return ret
        except Exception, e:
            logger.debug('Exception:%s', e)
            logger.debug(traceback.format_exc())

