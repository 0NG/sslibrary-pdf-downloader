import os, time, io, re
from multiprocessing.pool import ThreadPool

import requests
from PIL import Image
from PyPDF2 import PdfFileMerger

header = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' }

def mkdir(path):
    path = path.strip()
    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path)

def get_session(pool_connections, pool_maxsize, max_retries):
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections = pool_connections, pool_maxsize = pool_maxsize, max_retries = max_retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def search(name, page = 1):
    print('Searching ...')

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
    _tmp_header = header
    _tmp_header['Referer'] = req.url
    req = requests.get(readerUrl, headers = _tmp_header)

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

        return { 'url': url, 'total': int(total), 'isImg': True }

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

    return { 'url': url, 'total': int(total), 'isImg': False }

def downloadPDF(downloadInfo, toPath, threadNum = 8):
    session = get_session(threadNum, threadNum, 3)
    url = downloadInfo['url']
    total = downloadInfo['total']
    outName = toPath + '/page%d.pdf'
    mkdir(toPath)

    def threadDownloadImg(cpage):
        if os.path.exists(outName % cpage):
            return
        try:
            r = session.get(url % cpage, headers = header)

            # sometimes sslibrary asks us to use the same Referer as the url
            _retry_count = 0
            while b'setTimeout' in r.content:
                if _retry_count == 3:
                    _retry_count = -1
                    break
                _tmp_header = header
                _tmp_header['Referer'] = r.url
                r = session.get(url % cpage, headers = _tmp_header)
                _retry_count += 1
            if _retry_count == -1:
                raise Exception('max retry downloading')

            im = Image.open(io.BytesIO(r.content))
            im.save(outName % cpage, 'PDF', dpi=im.info['dpi'])
            time.sleep(1.5)
        except:
            print('page %d failed!' % cpage)
    
    def threadDownloadPDF(cpage):
        if os.path.exists(outName % cpage):
            return
        try:
            r = session.get(url % cpage, headers = header)

            # sometimes sslibrary asks us to use the same Referer as the url
            _retry_count = 0
            while b'setTimeout' in r.content:
                if _retry_count == 3:
                    _retry_count = -1
                    break
                _tmp_header = header
                _tmp_header['Referer'] = r.url
                r = session.get(url % cpage, headers = _tmp_header)
                _retry_count += 1
            if _retry_count == -1:
                raise Exception('max retry downloading')

            with open(outName % cpage, 'wb+') as pice:
                pice.write(r.content)
            time.sleep(0.5)
        except:
            print('page %d failed!' % cpage)

    print('Downloading ...')

    pool = ThreadPool(processes = threadNum)
    if downloadInfo['isImg']:
        pool.map(threadDownloadImg, range(1, total + 1))
    else:
        pool.map(threadDownloadPDF, range(1, total + 1))
    pool.close()
    pool.join()

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

if __name__ == '__main__':
    result = False
    while (result == False):
        keyword = input('Input keyword(s) without any spaces (use "+" between keywords): ')
        result = search(keyword)

        if result == False:
            print('Nothing found!')
        else:
            break

    pages = 1
    choice = input('Input the index of the file you want, press Enter to get the next page of the result of the search, or input -1 to get the last page: \n')
    while (choice == '' or choice == '-1'):
        if choice == '':
            pages = pages + 1
        else:
            pages = pages - 1

        if pages <= 0:
           print('The first page now!')
           pages = 1

        result = search(keyword, pages)
        if result == False:
            print('Hit the last page!')
            pages = pages - 1

        choice = input('Input the index of the file you want, press Enter to get the next page of the result of the search, or input -1 to get the last page: \n')
    
    choice = int(choice)

    downloadInfo = getDownloadInfo(result[choice]['url'])
    downloadPDF(downloadInfo, result[choice]['name'])
    print('Finish!')

