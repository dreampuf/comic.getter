#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
有妖气动漫采集脚本
  Feature:
    - 按照指定动漫采集
    - 可批量采集多集(sets)
    - 采集采用多进程并发，可手工指定并发数(-p)
    - 通过urllib3，实现对多个Http Connection的复用
    - 页面元素抓取采用lxml，以支持XPath方式抓取
    - 对于多次类别抓取进行缓存，以提高抓取速度

  TODO:
    - 目录规整，使得抓取过来的目录有序

"""

from __future__ import with_statement

__author__ = "dreampuf<soddyque@gmail.com>"
__website__ = "https://github.com/dreampuf/comic.getter"

import os
import sys
import time
import argparse
import cPickle as pickle
import atexit

import urllib3
from lxml import etree
from billiard import Pool
from billiard import Queue
from billiard import Manager
from billiard import log_to_stderr
from billiard import cpu_count
logger = log_to_stderr()

try:
    with open(".cache", "rb") as f:
        _cache = pickle.load(f)
except (IOError, EOFError, pickle.UnpicklingError):
    _cache = {}

def dumpcache():
    with open(".cache", "wb") as f:
        pickle.dump(_cache, f)
atexit.register(dumpcache)

fetcher = urllib3.PoolManager()
def fetch(url, cache=True):
    ret = None
    if cache and url in _cache:
        rtime, ret = _cache.get(url)
        if time.time() - rtime < 3600: return ret #只缓存一个小时内的操作

    resp = fetcher.request('GET', url)
    ret = resp.data
    _cache[url] = (time.time(), ret)
    return ret

def formatipt(ipt):
    """
    解析用户输入 eg. 1,5,6  10-14
    返回有序list
    """
    ls = ipt.split(",")
    result = {}
    for i in ls:
        if i.count("-") == 1 and i[-1] != "-":
            start = i[:i.find("-")]
            end = i[i.find("-")+1:]
            if not start.isdigit() and not end.isdigit():
                continue
            for k in xrange(int(start), int(end) + 1):
                result[k] = True

        if i.isdigit():
            result[int(i)] = True

    return result.keys()

def formatipt(ipt):
    for i in ipt.split(","):
        if "-" in i:
            for n in xrange(*map(int, i.split("-"))):
                yield n
        else:
            yield int(i) - 1

def save_pic(task, timeout=1):
    http = urllib3.PoolManager()
    print " Worker:" , os.getpid()#, task
    result = []
    if task["type"] == "sets":
        s = task
        s_url = s["url"]
        s_resp = http.request("GET", s_url)
        s_tree = etree.HTML(s_resp.data)
        result.append({"type": "pics", "url": s_tree.xpath('//*[@id="SS_cur_pic"]')[0].get('value'), "title": s["title"], "set": s["set"], "n": 1})
        href_pre = s_url[:s_url.rfind(".")]
        for n, i in enumerate(s_tree.xpath('//*[@id="comicShow_1"]/option[not(@selected)]'), 2):
            result.append({"type": "tpls", "title": s["title"], "set": s["set"], "n": n, "url": "%s_i%s.html" % (href_pre, i.get("value"))})
    
    elif task["type"] == "tpls":
        t = task
        t_resp = http.request("GET", t["url"])
        t_tree = etree.HTML(t_resp.data)
        result.append({"type": "pics", "title" : t["title"], "set": t["set"], "n": t["n"], "url": t_tree.xpath('//*[@id="SS_cur_pic"]')[0].get('value')})

    elif task["type"] == "pics": 
        try:
            p = task
            file_dir = os.path.join(".", "download", p["title"])
            p_resp = http.request("GET", p["url"])
            file_path = os.path.join(file_dir, "%s_%s%s" % (p["set"], p["n"], os.path.splitext(p["url"])[1])).encode("u8")
            with open(file_path, "wb") as wf:
                wf.write(p_resp.data)
        except (Exception, ) as ex:
            print ex

    return result


def cm(m =None, p=5, u="", **kw):
    ct = fetch(m)
    t = etree.HTML(ct)
    title = ''.join(t.xpath('//*[@id="workinfo"]/h1/text()')).strip()
    els = [(i.get("title")[:-11], i.get("href")) for i in t.xpath('//*[@id="chapterlist"]/ul/li/a')]
    for n, (e, _) in enumerate(els):
        print "%s." % n, e
    ci_pure = raw_input("输入对应集数序号,多集使用逗号分开,连续使用\"-\"分割 eg. 1\n4,6,7\n1-10,14-75\n请选择册:")
    ci = formatipt(ci_pure)
    
    #mg = Manager()
    tasks = []
    for i in ci:
        ci_title, ci_href = els[i]
        tasks.append({"type": "sets", "title": title, "set": "%s.%s" % (i+1, ci_title), "url": ci_href})

    file_dir = os.path.join(".", "download", title).encode("u8")
    try:
        if not os.path.exists(file_dir): os.makedirs(file_dir)
    except OSError:
        pass
    #use manual processes
    #ps = [Process(target=save_pic, args=(sets, tpls, pics)) for i in xrange(min(p, len(ci)))]
    #for i in ps:
    #    i.start()
    pool = Pool(processes=p)
    result = pool.map_async(save_pic, tasks) #for i in xrange(realy_p)] #if p.map_async don't forget p.close()
    out = sys.stdout
    try: 
        while True:
            if result.ready():
                tasks = []
                for ret in result.get():
                    tasks.extend(ret)
                if not tasks: break
                result = pool.map_async(save_pic, tasks) #for i in xrange(realy_p)] #if p.map_async don't forget p.close()
            out.write("\r%d" % (len(tasks)))
            out.flush()
            time.sleep(.5)
    except KeyboardInterrupt:
        print "已停止下载"
        #return
    finally:
        pool.close()

    print "下载完成"

    if not u: return
    #压缩并上传
    zip_name = file_dir[2:].replace(os.path.sep, "_") + "_" + ci_pure
    username, password = u.split(":")
    ci_str = map(str, ci)
    tfiles = ["%s/%s"%(dirpath, filename) for dirpath, dirs, files in os.walk(file_dir)
                                          for filename in files if filename[:filename.find(".")] in ci_str]
    zip_files(tfiles, zip_name)
    upfile(username, password, zip_name)

def zip_files(files, zip_name=None):
    "将指定文件压缩成为Zip"
    if zip_name is None : zip_name = "upload"
    zip_name = zip_name + ".zip"
    print "正在打包 %s ..." % zip_name
    import zipfile
    zpf = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
    for i in files[:10]:
        zpf.write(i)
    zpf.close()
    print "打包完毕 %s" % zip_name

def upfile(username, password, zip_name=None):
    "上传"

    print "正在登录115.com"
    import re
    from hashlib import md5
    from requests import sessions, api
    HEADERS = {
        "user_agent": "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
    }
    s = sessions.session(headers=HEADERS)
    resp = s.request("POST",
            "https://passport.115.com/?ac=login",
            data={
                "login[account]": username,
                "login[passwd]": password,
                "login[time]": "true"
            })
    resp = s.request("GET", "http://115.com")
    try:
        user_cookie = re.search("var USER_COOKIE = [\"']([^'\"]+)[\"'];", resp.text).group(1)
        user_rsa1 = re.search("Core.CONFIG.FUpRsa1 = [\"']([^\"']+)[\"'];", resp.text).group(1)
        user_rsa2 = re.search("Core.CONFIG.FUpRsa2 = [\"']([^\"']+)[\"'];", resp.text).group(1)
    except AttributeError:
        print "Error Account.."

    token_time = str(int(time.time()*1000))
    file_size = os.path.getsize(zip_name)
    token = md5(user_rsa1 + user_rsa2 + str(file_size) + token_time + user_rsa2 + user_rsa1).hexdigest()
    print "正在上传: %s 文件大小: %s 请稍后..." % (zip_name, file_size)
    resp = api.post("http://vipup.u.115.com/upload",
            data={
                "FileName": zip_name,
                "cid": "2156432", #U115 directory
                "cookie": user_cookie,
                "aid": "1",
                "token": token,
                "time": token_time,
                "Upload": "Submit Query",
            }, files={
                "Filedata": (zip_name.decode("u8"), open(zip_name)),
            }, headers={
                "user-agent": "Adobe Flash Player 11",
                "x-flash-version": "11,3,300,265",
            })
    
    print "上传成功"
    print resp.json
    

parser = argparse.ArgumentParser()
parser.add_argument("-m", type=str, default=None, action="store", dest="m", help="采集漫画地址")
parser.add_argument("-p", type=int, default=5, action="store", dest="p", help="采集并发数")
parser.add_argument("-u", type=str, default="", action="store", dest="u", help="指定空间账户，压缩并上传到指定分享空间（USERNAME:PASSWORD）")
parser.add_argument("-z", type=str, default=None, action="store", dest="z", help="只上传指定zip文件，不进行下载和压缩动作")

if __name__ == "__main__":
    ret = parser.parse_args()
    if ret.z:
        username, password = ret.u.split(":")
        upfile(username, password, ret.z)
    else:
        cm(**vars(ret))
    #upfile(["%s/%s" % (dirpath, filename) for dirpath, dirs, files in os.walk("download/") for filename in files if filename[-3:] == "jpg"][:10], "ss")


