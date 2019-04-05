import os, time, io, re, threading
import requests
from PIL import Image
from PyPDF2 import PdfFileMerger

header = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' }

def mkdir(path):
    path = path.strip()
    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path)

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
    top = 1
    url = downloadInfo['url']
    total = downloadInfo['total']
    outName = toPath + '/page%d.pdf'
    mkdir(toPath)

    qLock = threading.Lock()
    def threadDownloadImg():
        nonlocal top
        cur = 0
        while True:
            # get a new page
            with qLock:
                if top > total:
                    # all the pages are downloaded
                    break

                cur = top
                top += 1
                count = 0

            try:
                r = requests.get(url % cur, headers = header)
                im = Image.open(io.BytesIO(r.content))
                im.save(outName % cur, 'PDF', dpi=im.info['dpi'])
                time.sleep(1)
            except:
                # Retry 3 times, as sometimes download may fail for raw pdf
                if count == 3:
                    print('page %d failed!' % cur)
                count += 1
    
    def threadDownloadPDF():
        nonlocal top
        cur = 0
        while True:
            # get a new page
            with qLock:
                if top > total:
                    # all the pages are downloaded
                    break

                cur = top
                top += 1
                count = 0

            try:
                r = requests.get(url % cur, headers = header)
                with open(outName % cur, 'wb+') as pice:
                    pice.write(r.content)
            except:
                # Retry 3 times, as sometimes download may fail for raw pdf
                if count == 3:
                    print('page %d failed!' % cur)
                count += 1

    print('Downloading ...')

    threadList = []
    if downloadInfo['isImg']:
        for _ in range(threadNum):
            t = threading.Thread(target = threadDownloadImg)
            t.start()
            threadList.append(t)

    else:
        for _ in range(threadNum):
            t = threading.Thread(target = threadDownloadPDF)
            t.start()
            threadList.append(t)

    for i in range(threadNum):
        threadList[i].join()

    mergePDF(toPath, total, 'Merged')

def mergePDF(path, num, name):
    merger = PdfFileMerger()
    for cpage in range(1, num + 1):
        merger.append(open(path + '/page%d.pdf' % cpage, 'rb'))
    merger.write(path + '/' + name + '.pdf')
    merger.close()

if __name__ == '__main__':
    result = False
    while (result == False):
        keyword = input('Input a keyword without any spaces(use "+" between keywords): ')
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
