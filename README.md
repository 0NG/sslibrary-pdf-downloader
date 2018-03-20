# sslibrary的pdf资料下载器
从http://www.sslibrary.com上下载pdf资料，这大概只有国人用吧。。。so no english version

sslibrary的pdf格式文件只提供在线阅读，很麻烦，通过本项目的程序即可下载下来。这样就不需要sslibrary的特制阅读器了，直接用普通的pdf阅读器打开。

## 前提

1. 你的IP有权限下载sslibrary的文件，比如校园网用户并且学校买了sslibrary
2. python 3.x
3. 通过pip安装requests和PyPDF2模块

## 使用方法

```bash
python3 download.py
```

正确运行后会是这样：

![](./readme/1.png)

输入关键词进行搜索，比如搜索“光学”：

![](./readme/2.png)

此时输入列表中的序号，即可下载对应的资料。我限制了每次显示10个结果，什么都不输入直接按回车，即可显示下一页，如果要返回上一页，就输入-1。

下载的资料位置在当前目录下的对应资料名的文件夹内，文件名为Merged.pdf。

## 适用范围

有部分sslibrary上的资料是以图片形式存在的，本程序暂时还未支持这种资料的下载，如果遇到，可以试试[另一个人的项目](https://github.com/zamlty/sslibrary-downloader)，或者在issue说一下也行。

## TODO

1. 支持多线程下载
2. 提供更多的资料搜索选项
3. 支持下载图片格式的资料
4. 支持登录
4. 其他