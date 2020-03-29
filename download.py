# -*- coding: UTF-8 -*-
import os, time, io, re, random
from multiprocessing.pool import ThreadPool

import requests
from PIL import Image
from PyPDF2 import PdfFileMerger

UA = [
        'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
        'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
        'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)',
        'Mozilla/5.0 (iPad; U; CPU OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25',
        'Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.114 Mobile Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10240',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
        ]

# default header
header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
        }

# set proxy
proxy = {
        'http': 'http://127.0.0.1:8888',
        'https': 'https://127.0.0.1:8888'
        }
proxy = {}

def mkdir(path):
    path = path.strip()
    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path)

def getRandomUA():
    return UA[random.randint(0, len(UA) - 1)]

def get_session(pool_connections, pool_maxsize, max_retries):
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections = pool_connections, pool_maxsize = pool_maxsize, max_retries = max_retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def check_permission(text):
    reg_title = re.compile('(?<=<title>).+<\/title>')
    _check = reg_title.search(text)
    if _check == None:
        return True

    if _check.group() == '登录</title>':
        print('需要登录')
        reg_ip = re.compile('(?<=zl_ip">).+<\/div>')
        _check = reg_ip.search(text)
        if _check != None:
            print(_check.group()[:-6])
    else:
        print('Unknow error!')
    return False

def search(name, page = 1):
    print('Searching ...')

    # search by options
    req = requests.post('http://www.sslibrary.com/book/search/do',
                        headers = header,
                        data = {'sw': name,
                                'allsw': '',
                                'searchtype': '',
                                'classifyId': '',
                                'isort': '',
                                'field': 1,
                                'jsonp': '',
                                'showcata': '',
                                'expertsw': '',
                                'bCon': '',
                                'page': page,
                                'pagesize': 10,
                                'sign': '',
                                'enc': ''})

    _check = check_permission(req.text)
    if _check == False:
        return []

    data = req.json()

    result = []
    pdfUrl = 'http://www.sslibrary.com/reader/pdf/pdfreader?ssid=%s&d=%s'
    imgUrl = 'http://www.sslibrary.com/reader/jpath/jpathreader?ssid=%s&d=%s'

    if data['success']:
        list = data['data']['result']
        total = data['data']['total']
        print('%d results in total\n' % total)

        for index, book in enumerate(list):
            print('[%d] %s | %s | %s' % (index, book['bookName'], book['publisher'], book['author']))
            print('-------------------------------------------------------------')

            if book['isFromBW']:
                result.append({ 'name': book['bookName'], 'url': pdfUrl % (book['ssid'], book['jpathD']) })
            else:
                result.append({ 'name': book['bookName'], 'url': imgUrl % (book['ssid'], book['jpathD']) })

    if len(result) == 0:
        return False

    return result

def getDownloadInfo(readerUrl):
    req = requests.get(readerUrl, headers = header)

    # need the referer to be req.url to get the content
    while b'setTimeout("location.replace(location.href' in req.content:
        _tmp_header = header
        _tmp_header['Referer'] = req.url
        req = requests.get(readerUrl, headers = _tmp_header)
    cookie_url = req.url

    page = req.text
    page = page.replace('\r', '').replace('\n', '')

    isImg = 'jpath' in readerUrl
    if isImg:
        # jpg pices
        reg_url = re.compile('(?<=jpgPath: ")[^"]*')
        reg_total = re.compile('(?<=put">)\d+')
        total = reg_total.search(page).group()
        url = reg_url.search(page).group()
        url = 'http://img.sslibrary.com' + url + '%06d?zoom=0'

        return { 'url': url, 'total': int(total), 'isImg': True, 'cookie_url': [readerUrl, cookie_url] }

    # pdf pices
    reg_fileMark = re.compile('(?<=fileMark = ")\d+')
    reg_userMark = re.compile('(?<=userMark = ")\d*')
    reg_url = re.compile("(?<=DEFAULT_BASE_DOWNLOAD_URL = ')[^;]*")
    reg_total = re.compile('(?<=pages=)\d+')

    fileMark = reg_fileMark.search(page).group()
    userMark = reg_userMark.search(page).group()
    url = reg_url.search(page).group()

    url = url.replace("'", "").replace(' ', '')
    url = url.replace('+fileMark+', fileMark).replace('+userMark+', userMark) + '&cpage=%d'
    total = int(reg_total.search(url).group())

    return { 'url': url, 'total': int(total), 'isImg': False, 'cookie_url': [readerUrl, cookie_url] }

def downloadPDF(downloadInfo, toPath, threadNum = 8):
#    session = get_session(threadNum, threadNum, 3)
    url = downloadInfo['url']
    total = downloadInfo['total']
    outName = toPath + '/page%d.pdf'
    mkdir(toPath)

    def _getCookie(ua):
        _tmp_header = header
        _tmp_header['User-Agent'] = ua
        r = requests.get(downloadInfo['cookie_url'][0], headers = _tmp_header, proxies = {}, allow_redirects = False)
        c = r.cookies.get_dict()
        _tmp_header['Referer'] = downloadInfo['cookie_url'][1]
        r = requests.get(downloadInfo['cookie_url'][1], headers = _tmp_header, proxies = {}, cookies = c)
        _tmp_c = r.cookies.get_dict()
        for key in _tmp_c:
            c[key] = _tmp_c[key]
        return c

    def _getContent(url, cpage, ua, cookie = {}):
        _tmp_header = header
        _tmp_header['User-Agent'] = ua
        try:
            r = requests.get(url, headers = _tmp_header, cookies = cookie, proxies = proxy)
            if r.status_code == 404:
                time.sleep(10)
                ua = getRandomUA()
                cookie = _getCookie(ua)

            _retry_count = 0
            while b'setTimeout("location.replace(location.href' in r.content or r.status_code == 404 or 'Content-Length' in r.headers and int(r.headers['Content-Length']) != len(r.content):
                time.sleep(1)
                if _retry_count == 3:
                    _retry_count = -1
                    break
                # sometimes sslibrary asks us to use the same Referer as the url
                _tmp_header['Referer'] = r.url
                r = requests.get(url, headers = _tmp_header, cookies = cookie, proxies = proxy)
                _retry_count += 1
            if _retry_count == -1:
                raise Exception('max retry downloading')
        except:
            print('page %d failed!' % cpage)
            return ''
        return r.content

    def threadDownloadImg(cpage):
        if os.path.exists(outName % cpage):
            return
        ua = getRandomUA()
        cookie = _getCookie(ua)
        content = _getContent(url % cpage, cpage, ua, cookie)
        if content == '':
            return
        im = Image.open(io.BytesIO(content))
        im.save(outName % cpage, 'PDF', dpi=im.info['dpi'])
        time.sleep(0.5)
   
    def threadDownloadPDF(cpage):
        if os.path.exists(outName % cpage):
            return
        ua = getRandomUA()
        content = _getContent(url % cpage, cpage, ua)
        if content == '':
            return
        with open(outName % cpage, 'wb+') as pice:
            pice.write(content)
        time.sleep(0.5)

    print('Downloading ...')

    with ThreadPool(processes = threadNum) as pool:
        if downloadInfo['isImg']:
            pool.map(threadDownloadImg, range(1, total + 1))
        else:
            pool.map(threadDownloadPDF, range(1, total + 1))

    mergePDF(toPath, total, 'Merged')

def mergePDF(path, num, name):
    merger = PdfFileMerger()
    for cpage in range(1, num + 1):
        try:
            merger.append(open(path + '/page%d.pdf' % cpage, 'rb'))
        except:
            print(cpage)
    merger.write(path + '/' + name + '.pdf')
    merger.close()

def main():
    result = False
    while (result == False):
        keyword = input('输入关键词，不要有空格，需要空格的话就用+代替: ')
        result = search(keyword)
        if result == []:
            print('Error!')
            return

        if result == False:
            print('Nothing found!')
        else:
            break

    pages = 1
    choice = input('输入你想下载的文件的编号，按回车看下一页，输入-1看上一页: \n')
    while (choice == '' or choice == '-1'):
        if choice == '':
            pages = pages + 1
        else:
            pages = pages - 1

        if pages <= 0:
           print('已经是第一页了!')
           pages = 1

        result = search(keyword, pages)
        if result == False:
            print('已经是最后一页了!')
            pages = pages - 1

        choice = input('输入你想下载的文件的编号，按回车看下一页，输入-1看上一页: \n')
    
    choice = int(choice)

    downloadInfo = getDownloadInfo(result[choice]['url'])
    downloadPDF(downloadInfo, result[choice]['name'])
    print('Finish!')

if __name__ == '__main__':
    main()

