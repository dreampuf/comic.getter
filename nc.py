#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
import os
import sys
import time
import argparse
import urllib2
import contextlib
import cPickle as pickle
import atexit

import urllib3
from lxml import etree

try:
    with open(".cache", "rb") as f:
        _cache = pickle.load(f)
except (IOError, EOFError, pickle.UnpicklingError):
    _cache = {}

def dumpcache():
    print "Exit"
    with open(".cache", "wb") as f:
        pickle.dump(_cache, f)
atexit.register(dumpcache)

fetcher = urllib3.PoolManager()
def fetch(url, cache=True):
    ret = None
    if cache and url in _cache:
        ret = _cache.get(url)
    else:
        #with contextlib.closing(urllib2.urlopen(url, timeout=5)) as f:
        resp = fetcher.request('GET', url)
        ret = resp.data
        _cache[url] = ret
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

from billiard import Pool
from billiard import Queue
from billiard import Manager
from urllib import urlretrieve

def save_pic(sets, tpls, pics):
    http = urllib3.PoolManager()
    while not sets.empty():
        try:
            s = sets.get(timeout=5)
            s_url = s["url"]
            s_resp = http.request("GET", s_url)
            s_tree = etree.HTML(s_resp.data)
            pics.put({"url": s_tree.xpath('//*[@id="SS_cur_pic"]')[0].get('value'), "title": s["title"], "set": s["set"], "n": 1})

            href_pre = s_url[:s_url.rfind(".")]
            for n, i in enumerate(s_tree.xpath('//*[@id="comicShow_1"]/option[not(@selected)]'), 2):
                tpls.put({"title": s["title"], "set": s["set"], "n": n, "url": "%s_i%s.html" % (href_pre, i.get("value"))})

        except Queue.Empty:
            continue

    while not tpls.empty():
        try:
            t = tpls.get(timeout=5)
            t_resp = http.request("GET", t["url"])
            t_tree = etree.HTML(t_resp.data)
            pics.put({"title" : t["title"], "set": t["set"], "n": t["n"], "url": t_tree.xpath('//*[@id="SS_cur_pic"]')[0].get('value')})

        except Queue.Empty:
            continue

    while not pics.empty():
        try:
            p = pics.get(timeout=5)
            file_dir = os.path.join(".", "download", p["title"].encode("u8"))
            p_resp = http.request("GET", p["url"])
            file_path = os.path.join(file_dir, "%s_%s%s" % (p["set"], p["n"], os.path.splitext(p["url"])[1]))
            with open(file_path, "wb") as wf:
                wf.write(p_resp.data)
        except (Exception, Queue.Empty) as ex:
            print ex
            continue
    print os.getppid()

def cm(m=None, p=5):
    ct = fetch(m)
    t = etree.HTML(ct)
    title = ''.join(t.xpath('//*[@id="workinfo"]/h1/text()')).strip()
    els = [(i.text, i.get("href")) for i in t.xpath('//*[@id="chapterlist"]/ul/li/a')]
    for n, (e, _) in enumerate(els):
        print "%s." % n, e

    ci = formatipt(raw_input("输入对应集数序号,多集使用逗号分开,连续使用\"-\"分割 eg. 1\n4,6,7\n1-10,14-75\n请选择册:"))
    
    mg = Manager()
    sets, tpls, pics = mg.Queue(), mg.Queue(), mg.Queue()
    for i in ci:
        ci_title, ci_href = els[i]
        print ci_title
        sets.put({"title": title, "set": ci_title, "url": ci_href})

    file_dir = os.path.join(".", "download", ci_title.encode("u8"))
    try:
        os.makedirs(file_dir)
    except OSError:
        pass
    p = Pool(p)
    ret = p.apply_async(save_pic, (sets, tpls, pics))
    out = sys.stdout
    try: 
        while sets.qsize() or tpls.qsize() or pics.qsize():
            #print sets.qsize(), tpls.qsize(), pics.qsize()
            out.write("\r%s,%s,%s" % (sets.qsize(), tpls.qsize(), pics.qsize()))
            out.flush()
            time.sleep(.5)
    except KeyboardInterrupt:
        p.close()
        print "已停止下载"
    else:
        print "下载完成"
    

parser = argparse.ArgumentParser()
parser.add_argument("-m", type=str, default=None, action="store", dest="m", help="采集漫画地址")
parser.add_argument("-p", type=int, default=5, action="store", dest="p", help="采集并发数")

if __name__ == "__main__":
    ret = parser.parse_args()
    cm(**vars(ret))

