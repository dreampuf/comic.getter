#! /usr/bin/env python
# -*- coding: utf-8 -*-
#author: dreampuf (soddyque@gmail.com)

import traceback
import sys, os, random
import urllib, re
from threading import Thread
from threading import Lock

pr = sys.stdout.write
fl = sys.stdout.flush

def baseN(num,b):
    return ((num == 0) and  "0" ) or ( baseN(num // b, b).lstrip("0") + "0123456789abcdefghijklmnopqrstuvwxyz"[num % b])

def unpacked(p, a, c, k, e, d):
    def e(c):
        t = c%a
        return ("" if c < a else e(int(c/a))) + (chr(c+29) if t>35 else baseN(c, 36))
    if True:
      while c:
          d[e(c-1)] = k[c-1] or e(c)
          c = c-1
          c = 1
          r = re.compile('\\b\d\\b')
      return r.sub(lambda x: d[x.group()], p)


def pic_src(src):
    """处理图片地址"""
    pos = 0
    result = []
    for i in range(len(src) / 2):
        result.append(chr(int(src[pos: pos+2], 16)))
        pos += 2
    return "".join(result)
    return "".join(map(lambda x: chr(int(x, 16)), src))#.encode("utf-8")

servers = {
        "智能": "http://mhauto.kkkmh.com:8888",
        "电信1": "http://mhtzj1.kkkmh.com:8888",
        "电信2": "http://mht2.kkkmh.com",
        "网通1": "http://mhc1.kkkmh.com",
        }
choice_server = random.choice(servers.values())

re_pic_ls = re.compile("pic\[\d+\] = '([^']+)';", re.IGNORECASE)
re_packed = re.compile("eval\(function\(p,a,c,k,e,d\)[\w\W]+return p}\((.+)\)\)", re.IGNORECASE)
def GetMain(dict):
    """
    获取某集动漫信息,然后处理
    """
    #dict = {'url': '/manhua/0708/19/49950.html', 'name': u'\xe7\xbf\x94\xe4\xb9\x8b\xe4\xb9\xa6', 'title': u'\xe7\x81\xab\xe5\xbd\xb1\xe5\xbf\x8d\xe8\x80\x85 \xe7\xbf\x94\xe4\xb9\x8b\xe4\xb9\xa6'}
    dict["url"] = "%s%s" % ("http://www.kkkmh.com", dict["url"])
    fs = urllib.urlopen(dict["url"])
    data = fs.read()
    fs.close() 

    #fs = urllib.urlopen("http://www.kkkmh.com/manhua/common/server.js?v1290294109")
    #server = fs.read()
    #fs.close()
    #match = re_packed.match(server) 
    #print eval(match.group(1))
    #print unpacked(*eval(match.group(1)))


    pic_ls = []
    for i in re_pic_ls.finditer(data):
        #print i.group(1)
        pic_ls.append("%s%s" % (choice_server, pic_src(i.group(1))))

    dict.update({"pic_ls":pic_ls})
    return dict

def formatInput(input):
    """
    解析用户输入 eg. 1,5,6  10-14
    返回有序list
    """
    ls = input.split(",")
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

total_size = 0

re_main = re.compile("http://www.kkkmh.com/manhua/.+", re.IGNORECASE)
re_main_title = re.compile('<title>(.+?)漫画-', re.IGNORECASE)
re_main_content = re.compile('<div class="onlinedm">(.+)</div><div class="commentlist box"', re.IGNORECASE)
re_main_li = re.compile('<li><a href="(?P<url>[^"]+)" title="(?P<title>[^"]+)" target="_blank".*?>(?P<name>[^<]+)</a></li>', re.IGNORECASE)
def main(url):
    assert re_main.search(url) != None, "必须为可靠的kkkmh.com漫画刊物页链接"

    fs = urllib.urlopen(url)
    #fs = open("test.html")
    data = fs.read()
    fs.close()
    #print data 
    title = re_main_title.search(data).group(1)

    data = re_main_content.search(data).group()
    ls = re_main_li.finditer(data)
    result = []
    for i in ls:
        dic = i.groupdict()
        result.append(dic)
        #print dir(i.groupdict())

    if len(result) < 40 :
        print "输入对应集数序号,多集使用逗号分开,连续使用\"-\"分割 eg. 1\n4,6,7\n1-10,14-75"
    for n, i in enumerate(result):
        print "%s:%s" % (n, i["name"])
    if len(result) >= 40:
        print "输入对应集数序号,多集使用逗号分开,连续使用\"-\"分割 eg. 1\n4,6,7\n1-10,14-75"
    user_choice = formatInput(raw_input("==================\n"))
    user_choice = map(lambda x: x[1], filter(lambda i: i[0] in user_choice, enumerate(result)))

    sumpic = 0
    for i in user_choice:
        sumpic += len(GetMain(i)["pic_ls"])

    

    print "目标:%s\n总共下载%i集漫画,共%i张图." % (title, len(user_choice), sumpic) 

#下载模块
    from subprocess import Popen

    if sumpic < 10:
        max_process = 1
    elif sumpic < 100:
        max_process = 5
    else:
        max_process = 10

    # 临时解决方案
    alock = Lock()
    def showprocess(strs):
        pr("\r")
        pr(strs)
        fl()

    fails = []
    for i in user_choice:
        print "当前下载:%s-%s" % (title, i["name"])
        tlen = len(i["pic_ls"])
        plen = len(str(tlen))
        dir_path = os.path.join(title, i["name"])
        thread_pool = []
        global total_size
        total_size = 0
        files = {}

        #class Downloader(Thread):
        #    def __init__(self, *args, **kw):
        #        self.data = {}
        #        super(Thread, self).__init__(*args, **kw)
        def cur_printer(filename):
            def _cur_printer(loaded_num, chuck, size):
                global total_size
                if not filename in files:
                    files[filename] = 0
                files[filename] = loaded_num * chuck

                if total_size > 0:
                    showprocess("当前下载进度%.2f%%" % (sum(files.values())/float(total_size), ))

            return _cur_printer

        def downloader(url, path):
            try:
                #fs = urllib.urlopen(url)
                #if not os.path.exists(dir_path):
                #    os.makedirs(dir_path)
                #bs = open(os.path.join(dir_path, "%s%s" % (path, url[url.rindex('.'):])), "w")
                #bs.write(fs.read())
                #bs.close()
                #fs.close()
                global total_size
                full_path = os.path.join(dir_path, "%s%s" % (path, url[url.rindex("."):]))
                if not os.path.exists(dir_path):
                    try:
                        os.makedirs(dir_path)
                    except OSError, ex:
                        pass
                try:
                    filename, headers = urllib.urlretrieve(url, full_path, cur_printer(path))
                    if "Content-Length" in headers:
                        total_size += int(headers["Content-Length"])
                except:
                    pass

            except Exception, ex:
                #fails.append({"name":i["name"], "title":i["title"], "url": url})
                print traceback.format_exc()
                return 
            #pr("\r")
            #fl()
            #pr("当前下载进度%i/%i" % (n+1, tlen))
            #fl()
        
        for n,l in enumerate(i["pic_ls"]):
            t = Thread(target=downloader, kwargs={"url": l, "path": str(n+1).rjust(plen, "0")})
            t.start()
            thread_pool.append(t)

        for i in thread_pool:
            i.join()

   # 临时解决方案结束
    

#下载模块结束

    print "\n下载完成,已下载到脚本执行目录"


    #ts = open("gg.txt", "w")
    #ts.write(str(user_choice))
    #ts.close()



if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://www.kkkmh.com/manhua/0708/huo-ying-ren-zhe.html" 
    main(url)
        #pic_src("2f636f6d696364617461332f6e2f6e617275746f2f3030392f3030332e6a7067")
        #GetMain(1)
