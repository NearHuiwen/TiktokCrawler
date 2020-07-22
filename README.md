TiktokCrawler抖音爬虫（无/去掉水印）,多线程爬虫+JS逆向
===============

> 项目普及技术：JS逆向（调用JS文件）、抖音的一些接口加密、多线程操作、某些Linux命令操作（可在Win或Linux运行）

请在Python3下运行(版本太低可能会出现不兼容，本人用的是3.7版本)

这是一个[Python](https://www.python.org)的脚本,配置运行后可以下载指定分享视频，指定抖音用户的全部视频(含收藏)，也可以下载指定主题(挑战)或音乐下的全部视频。


## 注意

大家好，首先该项目是某开源项目（来自于https://github.com/loadchange/amemv-crawler）项目的升级迭代（某些功能已过时，本人做了一些更新，还添加了单个视频分享下载，加了一些个人的见解），感谢贵作者的慷慨开源
（截止版本2020年7月22日，即后面可能抖音出现更新，某些功能会过时，请谅解）

秉承原作者[loadchange](https://github.com/loadchange)精神，这是一个**练手项目**，源码仅作为和大家一起**学习Python**使用，你可以免费: 拷贝、分发和派生当前源码（最后最好添加一些自己的见解）。但你不可以用于*商业目的*及其他*恶意用途*。



服务端对抓取的一些限制，如抓取频率、IP等等，如果你遇到了这样的问题，
可能你的下载量已经超出了**学习目的**，对此我也拒绝支持并表示非常抱歉。



## 环境安装

首先，配置好你的Python、node环境

本人用的是pipenv虚拟环境
如果你已有虚拟环境以下可忽略
安装
```bash
$ pip install -i https://pypi.douban.com/simple pipenv
```
创建文件夹“TiktokCrawler”（项目放在这里）
创建虚拟环境
```bash
$ cd TiktokCrawler
$ pipenv install
```

进入虚拟环境
```bash
$ cd TiktokCrawler
$ pipenv shell
```



以上是本人学习习惯用pipenv做虚拟环境，原作者用的是Docker，
后者可能更高级一些用途更广，虚拟的是整个操作系统，有兴趣可以学习一下，这里就不做详解了

导入项目，也可直接下载覆盖TiktokCrawler文件夹
```bash
$ git clone https://github.com/NearHuiwen/TiktokCrawler.git
```
安装项目所需要的包
```bash
$ cd TiktokCrawler
$ pip install -r requirements.txt
```

大功告成,直接跳到下一节配置和运行.

## 配置和运行

有两种方式来指定你要下载的抖音号分享链接,一是编辑`share-url.txt`,二是指定命令行参数.

### 第一种方法:编辑share-url.txt文件

找到一个文字编辑器,然后打开文件`share-url.txt`,把你想要下载的抖音号分享链接编辑进去,以逗号/空格/tab/表格鍵/回车符分隔,可以多行.例如, 这个文件看起来是这样的:


```
有些分享是需要跳转页面才能获取下载地址的，如：分享链接为：#火箭少女101 月亮保安拯救你~ https://v.douyin.com/JY4YN3s/ 复制此链接，打开【抖音短视频】，直接观看视频！
截取“https://v.douyin.com/JY4YN3s/”到“share-url.txt”
实际会跳转到“https://www.iesdouyin.com/share/video/6696500716355292419/?region=CN&mid=6696729684098665227&u_code=i7jmc9j8&titleType=title&utm_source=copy_link&utm_campaign=client_share&utm_medium=android&app=aweme”

“share-url.txt”格式里的如下：

分享单个视频，如：
https://v.douyin.com/JY4YN3s/

分享用户，如：
https://v.douyin.com/JY4mGfR/
或者：https://www.douyin.com/share/user/85860189461?share_type=link&tt_from=weixin&utm_source=weixin&utm_medium=aweme_ios&utm_campaign=client_share&uid=97193379950&did=30337873848,

分享挑战视频，如：
或者：https://www.iesdouyin.com/share/challenge/1593608573838339?utm_campaign=clien,

分享音乐，如：
https://v.douyin.com/JYqGpRJ/
或者：https://www.iesdouyin.com/share/music/6536362398318922509?utm_campaign=client_share&app=aweme&utm_medium=ios&iid=30337873848&utm_source=copy
```

### 获取用户分享链接的方法（挑战、音乐 类似）
<p align="center">
<img src="https://raw.githubusercontent.com/NearHuiwen/TiktokCrawler/master/picture/step1.jpg" width="160">
<img src="https://raw.githubusercontent.com/NearHuiwen/TiktokCrawler/master/picture/step2.png" width="160">
</p>

然后保存文件,双击运行`amemv-video-ripper.py`或者在终端(terminal)里面
运行`python amemv-video-ripper.py`

### 第二种方法:使用命令行参数(仅针对会使用操作系统终端的用户)

如果你对Windows或者Unix系统的命令行很熟悉,你可以通过指定运行时的命令行参数来指定要下载的站点:

某些平台下注意给URL增加引号

```bash
python amemv-video-ripper.py --url URL1,URL2
```

分享链接以逗号分隔,不要有空格.

如果是用户URL默认不下载喜欢列表，需要增加 `--favorite`

```bash
python amemv-video-ripper.py --url URL --favorite
```

### 视频的下载与保存

程序运行后,会默认在download文件夹里面生成一个跟分享ID名字相同的文件夹,如“https://v.douyin.com/JYVGV2y/”,则以“JYVGV2y”命名
视频都会放在这个文件夹下面.

运行这个脚本,不会重复下载已经下载过的视频,所以不用担心重复下载的问题.同时,多次运行可以
帮你找回丢失的或者删除的视频.

下载文件一般以“文件的详情”命名
如果无详情，则以下载文件的ID命名
实在无法命名文件，则以“无名文件+时间”命名

然后重新运行下载命令.
<p align="center"><img src="https://raw.githubusercontent.com/NearHuiwen/TiktokCrawler/master/picture/end-of-run.png" width="800"></p>

## 高级应用

如果你想下载整个挑战主题，请在 share-url.txt 文件中添加 挑战的分享URL

如果你想下载按音乐去下载，请在 share-url.txt 文件中添加 音乐的分享URL

如下: 既为抖音号、挑战主题和音乐的三种爬虫方式，需要注意的是，爬虫只对搜索结果第一的结果进行下载，所以请尽量完整的写出你的 主题或音乐名称。

```
https://www.douyin.com/share/user/85860189461?share_type=link&tt_from=weixin&utm_source=weixin&utm_medium=aweme_ios&utm_campaign=client_share&uid=97193379950&did=30337873848,

https://www.iesdouyin.com/share/challenge/1593608573838339?utm_campaign=clien,

https://www.iesdouyin.com/share/music/6536362398318922509?utm_campaign=client_share&app=aweme&utm_medium=ios&iid=30337873848&utm_source=copy
```

> 短地址的情况

```
https://v.douyin.com/JY4YN3s/
```
