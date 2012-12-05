# 简介

宅男抓动漫

# 使用

## commicgetter.py

批量下载动漫，默认抓火影忍者

## nc.py

- 按照指定动漫采集
- 可批量采集多集(sets)
- 采集采用多进程并发，可手工指定并发数(-p)
- 通过urllib3，实现对多个Http Connection的复用
- 页面元素抓取采用lxml，以支持XPath方式抓取
- 对于多次类别抓取进行缓存，以提高抓取速度

# 协议

MIT
