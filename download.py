import os
import re
import requests
from PyPDF2 import PdfFileMerger

def mkdir(path):
    path = path.strip()
    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path)

def search(name, page = 1):
    print('Searching ...')

    req = requests.post('http://www.sslibrary.com/book/search/do',
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
    buttonurl = 'http://www.sslibrary.com/reader/pdf/pdfreader?ssid='

    if (data['success']):
        list = data['data']['result']
        total = data['data']['total']
        print('%d results in total\n' % total)

        for index, book in enumerate(list):
            print('[%d] %s | %s | %s' % (index, book['bookName'], book['publisher'], book['author']))
            print('-------------------------------------------------------------')

            result.append({'name': book['bookName'], 'buttonurl': buttonurl + book['ssid'] + '&d=' + book['jpathD']})

    if (len(result) == 0):
        return False

    return result

def getDownloadLink(buttonurl):
    req = requests.get(buttonurl)
    page = req.text
    page = page.replace('\r', '').replace('\n', '')

    reg_fileMark = re.compile('(?<=fileMark = ")\d+')
    reg_userMark = re.compile('(?<=userMark = ")\d*')
    reg_url = re.compile("(?<=DEFAULT_BASE_DOWNLOAD_URL = ')[^;]*")

    fileMark = reg_fileMark.search(page).group()
    userMark = reg_userMark.search(page).group()
    url = reg_url.search(page).group()

    url = url.replace("'", "").replace(' ', '')
    return url.replace('+fileMark+', fileMark).replace('+userMark+', userMark)

def downloadPDF(url, toPath):
    print('Downloading ...')

    reg_pages = re.compile('(?<=pages=)\d+')
    pages = int(reg_pages.search(url).group())

    url = url + '&cpage='
    mkdir(toPath)
    for cpage in range(1, pages + 1):
        req = requests.get(url + str(cpage))
        with open(toPath + '/page' + str(cpage) + '.pdf', 'wb+') as pice:
            pice.write(req.content)

    mergePDF(toPath, pages, 'Merged')

def mergePDF(path, num, name):
    merger = PdfFileMerger()
    for cpage in range(1, num + 1):
        merger.append(open(path + '/page' + str(cpage) + '.pdf', 'rb'))
    merger.write(path + '/' + name + '.pdf')
    merger.close()

if __name__ == '__main__':
    result = False
    while (result == False):
        keyword = input('Input a keyword without any spaces: ')
        result = search(keyword)

        if (result == False):
            print('Nothing found!')
        else:
            break

    pages = 1
    choice = input('Input the index of the file you want, press Enter to get the next page of the result of the search, or input -1 to get the last page: \n')
    while (choice == '' or choice == '-1'):
        if (choice == ''):
            pages = pages + 1
        else:
            pages = pages - 1

        if (pages <= 0):
           print('The first page now!')
           pages = 1

        result = search(keyword, pages)
        if (result == False):
            print('Hit the last page!')
            pages = pages - 1

        choice = input('Input the index of the file you want, press Enter to get the next page of the result of the search, or input -1 to get the last page: \n')
    
    choice = int(choice)

    url = getDownloadLink(result[choice]['buttonurl'])
    downloadPDF(url, result[choice]['name'])

