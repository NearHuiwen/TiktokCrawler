# -*- coding: utf-8 -*-
# @Author : 李惠文
# @Email : 2689022897@qq.com
# @Time : 2020/7/3 10:58
# 抖音爬虫
import datetime
import os
import sys
import getopt
import urllib.parse
import urllib.request
import copy
import codecs
import requests
import re
from six.moves import queue as Queue
from threading import Thread
import json
import time

# 自定义请求头文件
HEADERS = {
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'zh-CN,zh;q=0.9',
    'pragma': 'no-cache',
    'Accept-Encoding': '',
    'cache-control': 'no-cache',
    'upgrade-insecure-requests': '1',
    'user-agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1",
}

# 下载超时时间
TIMEOUT = 10

# 重试下载次数
RETRY = 5

# 下载失败过多，视为爬虫失败，停止继续爬虫
RESULTS_VARIATION_RETRY = 5000

# 设置十条线程下载
THREADS = 10

# 是否爬取该用户“喜欢”的作品
DOWNLOAD_FAVORITE = False


# 通过content-length头获取远程文件大小
def getRemoteFileSize(url):
    try:
        request = urllib.request.Request(url)
        request.get_method = lambda: 'HEAD'
        response = urllib.request.urlopen(request)
        response.read()
    except urllib.error.HTTPError as e:
        # 远程文件不存在
        print(e.code)
        print(e.read().decode("utf8"))
        return 0
    else:
        fileSize = dict(response.headers).get('Content-Length', 0)
        return int(fileSize)


# 下载文件
def download(medium_type, uri, medium_url, target_folder):
    headers = copy.deepcopy(HEADERS)
    file_name = uri.strip()
    # 如果无名文件，则以“无名文件+时间”命名
    if (not file_name):
        now_time = str(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        file_name = "无名文件" + now_time

    if medium_type == 'video':
        file_name += '.mp4'
        headers['user-agent'] = 'Aweme/63013 CFNetwork/978.0.7 Darwin/18.6.0'
    elif medium_type == 'image':
        file_name += '.jpg'
        file_name = file_name.replace("/", "-")
    else:
        return
    # 文件路径
    file_path = os.path.join(target_folder, file_name)
    # 判断是否存在文件
    if os.path.isfile(file_path):
        # 通过content-length头获取远程文件大小
        remoteSize = getRemoteFileSize(medium_url)
        # 本地已下载的文件大小
        localSize = os.path.getsize(file_path)
        if remoteSize == localSize:
            return
    print("Downloading %s from %s.\n" % (file_name, medium_url))
    retry_times = 0
    #  判断重试下载次数
    while retry_times < RETRY:
        try:
            resp = requests.get(medium_url, headers=headers,
                                stream=True, timeout=TIMEOUT)
            if resp.status_code == 403:
                retry_times = RETRY
                print("Access Denied when retrieve %s.\n" % medium_url)
                raise Exception("Access Denied")
            with open(file_path, 'wb') as fh:
                for chunk in resp.iter_content(chunk_size=1024):
                    fh.write(chunk)
            break
        except:
            pass
        retry_times += 1
    else:
        try:
            os.remove(file_path)
        except OSError:
            pass
        print("Failed to retrieve %s from %s.\n" % (uri, medium_url))
    time.sleep(1)


# 从“分享地址”中，获取跳转页面
def get_real_address(url):
    if url.find('v.douyin.com') < 0:
        return url
    res = requests.get(url, headers=HEADERS, allow_redirects=False)
    if res.status_code == 302:
        long_url = res.headers['Location']
        HEADERS['Referer'] = long_url
        return long_url
    return None


# 获取dytk，用于下个接口使用的字段
def get_dytk(url):
    res = requests.get(url, headers=HEADERS)
    if not res:
        return None
    # dytk = re.findall("dytk: '(.*)'", res.content.decode('utf-8'))
    dytk = re.findall("dytk: '(.*)'", res.text)
    if len(dytk):
        return dytk[0]
    return None


# 多线程下载
class DownloadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # 队列中获取需要下载的
            medium_type, uri, download_url, target_folder = self.queue.get()
            # 下载
            download(medium_type, uri, download_url, target_folder)
            # tase_done()的作用：只有消费者把队列所有的数据处理完毕，queue.join()才会停止阻塞
            self.queue.task_done()


class CrawlerScheduler(object):

    def __init__(self, items):
        # 需下载的文件名:被重定向的地址列表
        self.file_names = {}
        for i in items:
            # 从“分享地址”中，获取跳转页面
            url = get_real_address(i)
            if url:
                self.file_names[re.findall(r'v.douyin.com/(\w+)', i)[-1]] = url
        if len(self.file_names) > 0:
            # 初始化线程队列
            self.queue = Queue.Queue()
            for x in range(THREADS):
                # 线程下载
                worker = DownloadWorker(self.queue)
                # 子线程的daemon属性为False，主线程结束时会检测该子线程是否结束，如果该子线程还在运行，则主线程会等待它完成后再退出
                # 子线程的daemon属性为True，主线程运行结束时不对这个子线程进行检查而直接退出
                worker.daemon = True
                worker.start()  # 属性daemon的值默认为False，如果需要修改，必须在调用start()方法启动线程之前进行设置

            # 下载分析
            self.scheduling()

    # 调用js获取Signature
    @staticmethod
    def generateSignature(value):
        p = os.popen('node fuck-byted-acrawler.js %s' % value)
        return (p.readlines()[0]).strip()

    # 下载分析
    def scheduling(self):
        for key, val in self.file_names.items():
            # 用户全作品
            if re.search('share/user', val):
                self.download_user_videos(key, val)
            # 挑战视频
            elif re.search('share/challenge', val):
                self.download_challenge_videos(key, val)
            # 音乐
            elif re.search('share/music', val):
                self.download_music_videos(key, val)
            # 分享单个视频
            elif re.search('share/video', val):
                self.download_share_videos(key, val)

    # 截取视频id,下载分享视频
    def download_share_videos(self, file_name, url):
        item_ids = re.findall(r'share/video/(\d+)', url)
        if not len(item_ids):
            print("Share video #%s does not exist" % item_ids[0])
            return
        # 筛选视频id
        item_id = item_ids[0]
        video_count = self._download_share_videos_media(item_id, url, file_name)
        # main线程等到其他多个线程执行完毕后再继续执行
        self.queue.join()
        print("\nItem share video #%s, video number %d\n\n" %
              (item_id, video_count))
        print("\nFinish Downloading All the videos from #%s\n\n" % item_id)

    # 下载单个分享视频（添加至队列）
    def _download_share_videos_media(self, item_id, url, file_name):
        # 创建下载文件夹
        current_folder = os.getcwd()
        target_folder = os.path.join(current_folder, 'download/%s' % file_name)
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)
        hostname = urllib.parse.urlparse(url).hostname
        signature = self.generateSignature(str(item_id))
        url = "https://%s/web/api/v2/aweme/iteminfo/?{0}" % hostname
        params = {
            'item_ids': str(item_id),
            'count': '9',
            'cursor': '0',
            'aid': '1128',
            'screen_limit': '3',
            'download_click_limit': '0',
            '_signature': signature
        }
        video_count = 0
        # 获取下载列表
        res = self.requestWebApi(url, params)
        if res:
            item_list = res.get('item_list', [])
            if item_list:
                for aweme in item_list:
                    aweme['hostname'] = hostname
                    video_count += 1
                    # 添加下载地址到队列
                    self._join_download_queue(aweme, target_folder)
        return video_count

    # 下载用户全作品
    def download_user_videos(self, file_name, url):
        # 获取用户id
        number = re.findall(r'share/user/(\d+)', url)
        if not len(number):
            return
        user_id = number[0]
        # 获取dytk，用于下个接口使用的字段
        dytk = get_dytk(f"https://www.amemv.com/share/user/{user_id}")
        # 下载
        video_count = self._download_user_media(user_id, dytk, url, file_name)
        # main线程等到其他多个线程执行完毕后再继续执行
        self.queue.join()
        print("\nAweme number %s, video number %s\n\n" %
              (user_id, str(video_count)))
        print("\nFinish Downloading All the videos from %s\n\n" % user_id)

    # 下载“分享的挑战视频”
    def download_challenge_videos(self, file_name, url):
        challenge = re.findall('share/challenge/(\d+)', url)
        if not len(challenge):
            print("Challenge #%s does not exist" % challenge[0])
            return
        # 获取挑战视频id
        challenges_id = challenge[0]
        video_count = self._download_challenge_media(challenges_id, url, file_name)
        # main线程等到其他多个线程执行完毕后再继续执行
        self.queue.join()
        print("\nAweme challenge #%s, video number %d\n\n" %
              (challenges_id, video_count))
        print("\nFinish Downloading All the videos from #%s\n\n" % challenges_id)

    # 下载“分享的音乐”
    def download_music_videos(self, file_name, url):
        music = re.findall('share/music/(\d+)', url)
        if not len(music):
            return
        # 获取音乐id
        musics_id = music[0]
        video_count = self._download_music_media(musics_id, url, file_name)
        # main线程等到其他多个线程执行完毕后再继续执行
        self.queue.join()
        print("\nAweme music @%s, video number %d\n\n" %
              (musics_id, video_count))
        print("\nFinish Downloading All the videos from @%s\n\n" % musics_id)

    # 添加下载地址到队列
    def _join_download_queue(self,aweme, target_folder):
        try:
            if aweme.get('video', None):
                uri = aweme['video']['play_addr']['uri']
                download_url = "https://aweme.snssdk.com/aweme/v1/play/?{0}"
                download_params = {
                    'video_id': uri,
                    'line': '0',
                    'ratio': '720p',
                    'media_type': '4',
                    'vr_type': '0',
                    'improve_bitrate': '0',
                    'is_play_url': '1',
                    'h265': '1',
                    'adapt720': '1'
                }
                if aweme.get('hostname') == 't.tiktok.com':
                    download_url = 'http://api.tiktokv.com/aweme/v1/play/?{0}'
                    download_params = {
                        'video_id': uri,
                        'line': '0',
                        'ratio': '720p',
                        'media_type': '4',
                        'vr_type': '0',
                        'test_cdn': 'None',
                        'improve_bitrate': '0',
                        'version_code': '1.7.2',
                        'language': 'en',
                        'app_name': 'trill',
                        'vid': 'D7B3981F-DD46-45A1-A97E-428B90096C3E',
                        'app_version': '1.7.2',
                        'device_id': '6619780206485964289',
                        'channel': 'App Store',
                        'mcc_mnc': '',
                        'tz_offset': '28800'
                    }
                url = download_url.format('&'.join([key + '=' + download_params[key] for key in download_params]))
                self.queue.put(('video', aweme.get('desc', uri), url, target_folder))
            else:
                if aweme.get('image_infos', None):
                    image = aweme['image_infos']['label_large']
                    self.queue.put(('image', image['uri'], image['url_list'][0], target_folder))
        except KeyError:
            return
        except UnicodeDecodeError:
            print("Cannot decode response data from DESC %s" % aweme['desc'])
            return

    # 爬取该用户“喜欢”的作品（添加至队列）
    def __download_favorite_media(self, user_id, dytk, hostname, signature, favorite_folder, video_count):
        if not os.path.exists(favorite_folder):
            os.makedirs(favorite_folder)
        url = "https://%s/web/api/v2/aweme/like/" % hostname
        params = {
            'user_id': str(user_id),
            'count': '21',
            'max_cursor': '0',
            'aid': '1128',
            '_signature': signature,
            'dytk': dytk
        }
        max_cursor = None

        while True:
            if max_cursor:
                params['max_cursor'] = str(max_cursor)
            #   获取下载列表
            res = self.requestWebApi(url, params)
            if not res:
                # res = self.requestWebApi(url, params)
                continue
            favorite_list = res.get('aweme_list', [])
            for aweme in favorite_list:
                video_count += 1
                aweme['hostname'] = hostname
                # 添加下载地址到队列
                self._join_download_queue(aweme, favorite_folder)
            if not res.get('has_more'):
                break
            max_cursor = res.get('max_cursor')
        return video_count

    # 下载所有作品（添加至队列）
    def _download_user_media(self, user_id, dytk, url, file_name):
        # 新建文件夹
        current_folder = os.getcwd()
        target_folder = os.path.join(current_folder, 'download/%s' % file_name)
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)

        #  判断之前是否user_id是否获取了
        if not user_id:
            print("Number %s does not exist" % user_id)
            return

        # 首次判断是否无视频，hostname可以理解为该用户的id，下面请求有用
        hostname = urllib.parse.urlparse(url).hostname
        if hostname != 't.tiktok.com' and not dytk:
            print(url, "已无视频可以爬")
            return

        # 获取signature
        signature = self.generateSignature(str(user_id))
        url = "https://%s/web/api/v2/aweme/post/" % hostname

        # 爬取第一页，每页21个视频
        params = {
            'user_id': str(user_id),
            'count': '21',
            'max_cursor': '0',
            'aid': '1128',
            '_signature': signature,
            'dytk': dytk
        }

        # if hostname == 't.tiktok.com':
        #     params.pop('dytk')
        #     params['aid'] = '1180'

        # 分页
        # max_cursor 上一个max_cursor是下一次请求的参数，可以理解为上一个爬取视频的最后一个视频序号吧
        # video_count 爬取视频总数
        max_cursor, video_count = None, 0
        retry_count = 0
        while True:
            if max_cursor:
                params['max_cursor'] = str(max_cursor)
                # 获取下载列表
            res = self.requestWebApi(url, params)
            if not res:
                break
            aweme_list = res.get('aweme_list', [])
            for aweme in aweme_list:
                video_count += 1
                aweme['hostname'] = hostname
                # 添加下载地址到队列
                self._join_download_queue(aweme, target_folder)
            #  has_more：是否没有视频了
            if not res.get('has_more'):
                break
            max_cursor = res.get('max_cursor')
            # TODO: Weird result. What went wrong?
            # 下载过程中爬虫失败判断
            if not max_cursor:
                retry_count += 1
                params['_signature'] = self.generateSignature(str(user_id))
                # 下载失败过多，视为爬虫失败，停止继续爬虫
                if retry_count > RESULTS_VARIATION_RETRY:
                    print('download user media: %s, Too many failures!' %
                          str(user_id))
                    break
                print('download user media: %s, result retry: %d.' %
                      (str(user_id), retry_count,))
        # 是否爬取该用户“喜欢”的作品
        if DOWNLOAD_FAVORITE:
            favorite_folder = target_folder + '/favorite'
            video_count = self.__download_favorite_media(
                user_id, dytk, hostname, signature, favorite_folder, video_count)
        if video_count == 0:
            print("There's no video in number %s." % user_id)
        # 返回总共下载的视频总量
        return video_count

    # 下载挑战视频（添加至队列）
    def _download_challenge_media(self, challenge_id, url, file_name):
        # 创建下载文件夹
        current_folder = os.getcwd()
        target_folder = os.path.join(
            current_folder, 'download/#%s' % file_name)
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)

        hostname = urllib.parse.urlparse(url).hostname
        signature = self.generateSignature(str(challenge_id) + '9' + '0')

        url = "https://%s/aweme/v1/challenge/aweme/" % hostname
        params = {
            'ch_id': str(challenge_id),
            'count': '9',
            'cursor': '0',
            'aid': '1128',
            'screen_limit': '3',
            'download_click_limit': '0',
            '_signature': signature
        }

        cursor, video_count = None, 0
        while True:
            if cursor:
                params['cursor'] = str(cursor)
                params['_signature'] = self.generateSignature(
                    str(challenge_id) + '9' + str(cursor))
            # 获取下载列表
            res = self.requestWebApi(url, params)
            if not res:
                break
            aweme_list = res.get('aweme_list', [])
            if not aweme_list:
                break
            for  aweme in aweme_list:
                aweme['hostname'] = hostname
                video_count += 1
                # 添加下载地址到队列
                self._join_download_queue(aweme, target_folder)
            if res.get('has_more'):
                cursor = res.get('cursor')
            else:
                break
        if video_count == 0:
            print("There's no video in challenge %s." % challenge_id)
        return video_count

    # 下载音乐（添加至队列）
    def _download_music_media(self, music_id, url, file_name):
        if not music_id:
            print("Challenge #%s does not exist" % music_id)
            return
        # 创建下载文件夹，音乐文件夹名字，前头带“@”，用于区别
        current_folder = os.getcwd()
        target_folder = os.path.join(current_folder, 'download/@%s' % file_name)
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)
        hostname = urllib.parse.urlparse(url).hostname
        signature = self.generateSignature(str(music_id))
        url = "https://%s/web/api/v2/music/list/aweme/?{0}" % hostname
        params = {
            'music_id': str(music_id),
            'count': '9',
            'cursor': '0',
            'aid': '1128',
            'screen_limit': '3',
            'download_click_limit': '0',
            '_signature': signature
        }
        if hostname == 't.tiktok.com':
            for key in ['screen_limit', 'download_click_limit', '_signature']:
                params.pop(key)
            params['aid'] = '1180'
        cursor, video_count = None, 0
        while True:
            if cursor:
                params['cursor'] = str(cursor)
                params['_signature'] = self.generateSignature(
                    str(music_id) + '9' + str(cursor))
                # 获取下载列表
            res = self.requestWebApi(url, params)
            if not res:
                break
            aweme_list = res.get('aweme_list', [])
            if not aweme_list:
                break
            for  aweme in aweme_list:
                aweme['hostname'] = hostname
                video_count += 1
                # 添加下载地址到队列
                self._join_download_queue(aweme, target_folder)
            if res.get('has_more'):
                cursor = res.get('cursor')
            else:
                break
        if video_count == 0:
            print("There's no video in music %s." % music_id)
        return video_count

    # 获取下载列表
    def requestWebApi(self, url, params):
        headers = copy.deepcopy(HEADERS)
        headers['cookie'] = '_ga=GA1.2.1280899533.15586873031; _gid=GA1.2.2142818962.1559528881'
        res = requests.get(url, headers=headers, params=params)
        content = res.content.decode('utf-8')
        print(content)
        if not content:
            print('\n\nWeb Api Error: %s'
                  '\n\nhears: %s'
                  '\n\nparams: %s' % (url, str(headers), str(params),))
            return None
        return json.loads(content)


def usage():
    print("1. Please create file share-url.txt under this same directory.\n"
          "2. In share-url.txt, you can specify amemv share page url separated by "
          "comma/space/tab/CR. Accept multiple lines of text\n"
          "3. Save the file and retry.\n\n"
          "Sample File Content:\nurl1,url2\n\n"
          "Or use command line options:\n\n"
          "Sample:\npython amemv-video-ripper.py --urls url1,url2\n\n\n")
    print(u"未找到share-url.txt文件，请创建.\n"
          u"请在文件中指定抖音分享页面URL，并以 逗号/空格/tab/表格鍵/回车符 分割，支持多行.\n"
          u"保存文件并重试.\n\n"
          u"例子: url1,url12\n\n"
          u"或者直接使用命令行参数指定链接\n"
          u"例子: python amemv-video-ripper.py --urls url1,url2")


# 获取“分享地址”
# 找到一个文字编辑器,然后打开文件share-url.txt
# 把你想要下载的抖音号分享链接编辑进去,以逗号/空格/tab/表格鍵/回车符分隔,可以多行.例如, 这个文件看起来是这样的:
def parse_sites(fileName):
    with open(fileName, "rb") as f:
        txt = f.read().rstrip().lstrip()
        txt = codecs.decode(txt, 'utf-8')
        txt = txt.replace("\t", ",").replace(
            "\r", ",").replace("\n", ",").replace(" ", ",")
        txt = txt.split(",")
    numbers = list()
    for raw_site in txt:
        site = raw_site.lstrip().rstrip()
        if site:
            numbers.append(site)
    return numbers


# 获取“分享地址”的文件路径
def get_content(filename):
    if os.path.exists(filename):
        return parse_sites(filename)
    else:
        # 无法调出地址
        usage()
        sys.exit(1)


if __name__ == "__main__":
    content, opts, args = None, None, []

    try:
        # getopt.getopt()为了从外部输入不同的命令行选项时，对应执行不同的功能
        opts, args = getopt.getopt(sys.argv[1:], "hi:o:", ["favorite", "urls=", "filename="])
    except getopt.GetoptError:
        # 无法调出地址
        usage()
        # sys.exit([args])的参数解析
        # 意思就是参数为数字的时候，和 shell 退出码意义是一样的，sys.exit(2)和sys.exit(1)只是为了区分结束原因
        # 0 ：成功结束
        # 1 ：通用错误　　
        # 2 ：误用Shell命令
        sys.exit(2)

    # 命令行中提取地址到content
    for opt, arg in opts:
        if opt == "--favorite":
            DOWNLOAD_FAVORITE = True
        elif opt == "--urls":
            content = arg.split(",")
        elif opt == "--filename":
            content = get_content(arg)

    # 从文件中提取下载地址到content
    if content == None:
        # 找到一个文字编辑器,然后打开文件share-url.txt
        content = get_content("share-url.txt")

    # 没有需要下载就关闭
    if len(content) == 0 or content[0] == "":
        # 无法调出地址
        usage()
        sys.exit(1)

    # 执行下载程序
    CrawlerScheduler(content)
