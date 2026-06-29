"""集中所有可调参数，调效果只动这里。"""
from __future__ import annotations

# ---- 抓取 ----
FETCH_TIMEOUT = 6.0
SEARCH_TIMEOUT = 8.0
MAX_CONCURRENCY = 8
MAX_CONTENT_BYTES = 2_000_000

# deep mode：默认关闭；工具调用可传 deep_mode=True
ENABLE_DEEP_MODE = False
DEEP_FETCH_TIMEOUT = 12.0
DEEP_MAX_PAGES = 5

# ---- 召回 / 输出 ----
SEARCH_FETCH_N = 10
SEARCH_FETCH_MAX = 30
RETURN_TOP_N = 5
RETURN_MAX_N = 10

# ---- 搜索 provider ----
# 可选：bing, duckduckgo
SEARCH_PROVIDERS = ("yandex", "bing", "duckduckgo")

BING_SEARCH_URL = "https://www.bing.com/search"
YANDEX_SEARCH_URL = "https://yandex.com/search"

# ---- 缓存 ----
CACHE_DIR = ".clean_search_cache"
ENABLE_SEARCH_CACHE = True
ENABLE_FETCH_CACHE = True
SEARCH_CACHE_TTL = 6 * 3600
FETCH_CACHE_TTL = 24 * 3600
CACHE_MAX_FILES = 3000
CACHE_CLEANUP_INTERVAL = 300

# ---- 黑名单订阅 ----
BLACKLIST_SUBSCRIPTIONS = [
    # 主要：eallion 14 合 1 黑名单
    "https://raw.githubusercontent.com/eallion/uBlacklist-subscription-compilation/main/uBlacklist.txt",
    "https://gh-proxy.com/raw.githubusercontent.com/eallion/uBlacklist-subscription-compilation/main/uBlacklist.txt",

    # 中文中文黑名单
    "https://raw.githubusercontent.com/cobaltdisco/Google-Chinese-Results-Blocklist/master/uBlacklist_subscription.txt",

    # MisakaMikoto - 中文内容农场 & 低质站
    "https://raw.githubusercontent.com/MisakaMikoto-35c5/ublacklist-rules/main/content-farm.txt",
    "https://raw.githubusercontent.com/MisakaMikoto-35c5/ublacklist-rules/main/bad-content.txt",

    # Scyrte - 屏蔽 CSDN 等
    "https://raw.githubusercontent.com/Scyrte/uBlacklist-Subscription/master/blocklist.txt",

    # NotaInutilis Super SEO Spam Suppressor
    "https://raw.githubusercontent.com/NotaInutilis/Super-SEO-Spam-Suppressor/main/blocklist.txt",

    # popcar2 BadWebsiteBlocklist (AI spam, SEO bait)
    "https://raw.githubusercontent.com/popcar2/BadWebsiteBlocklist/main/uBlacklist.txt",

    # 终结内容农场
    "https://raw.githubusercontent.com/meolalo/end-content-farm/main/uBlacklist.txt",

    # Peter Lowe 广告追踪列表 (40K+)
    "https://pgl.yoyo.org/as/serverlist.php?hostformat=plain&mimetype=plaintext&prepend=*://*.&append=/*&showintro=0",

    # 国际文章/转载拦截
    "https://raw.githubusercontent.com/quenhus/uBlock-Origin-dev-filter/main/dist/other_format/uBlacklist/all.txt",

    # laylavish AI 内容黑名单
    "https://raw.githubusercontent.com/laylavish/uBlockOrigin-HUGE-AI-Blocklist/main/list_uBlockOrigin.txt",

    # wdmpa content-farm-list
    "https://raw.githubusercontent.com/wdmpa/content-farm-list/main/uBlacklist.txt",

    # 镜像: MisakaMikoto
    "https://gh-proxy.com/raw.githubusercontent.com/MisakaMikoto-35c5/ublacklist-rules/main/content-farm.txt",
    "https://gh-proxy.com/raw.githubusercontent.com/MisakaMikoto-35c5/ublacklist-rules/main/bad-content.txt",

    # 镜像: popcar2
    "https://gh-proxy.com/raw.githubusercontent.com/popcar2/BadWebsiteBlocklist/main/uBlacklist.txt",

    # 镜像: wdmpa
    "https://gh-proxy.com/raw.githubusercontent.com/wdmpa/content-farm-list/main/uBlacklist.txt",
]

BLACKLIST_CACHE_FILE = ".blacklist_cache.txt"
BLACKLIST_TTL = 7 * 24 * 3600
BLACKLIST_CACHE_GRACE = 90 * 24 * 3600

USER_BLACKLIST_FILE = ".user_blacklist.txt"
BAD_RESULT_FILE = ".bad_results.txt"

STATIC_BLACKLIST = {
    # 中文内容农场 / 低质聚合
    "csdn.net", "blog.csdn.net",
    "baijiahao.baidu.com", "zhidao.baidu.com",
    "360doc.com", "sohu.com", "toutiao.com",
    "jianshu.com", "ithome.com", "163.com", "qq.com",
    "51cto.com", "oschina.net", "cnblogs.com",
    "segmentfault.com", "tuicool.com", "aibase.com",

    # 国际低质 / SEO / 转载聚合，保持克制，避免误伤
    "answers.microsoft.com",
    "quora.com",
    "medium.com",
    "dev.to",
    "geeksforgeeks.org",
    "tutorialspoint.com",
    "w3schools.com",
    "javatpoint.com",
    "programiz.com",
    "stackshare.io",
}

# ---- 内容规则 ----
MIN_SNIPPET_LEN = 40
MIN_CONTENT_LEN = 200
MAX_SPAM_HITS = 3

SPAM_KEYWORDS = (
    # zh
    "点击", "广告", "推广", "加微信", "扫码加", "原标题",
    "转载请", "版权声明", "免责声明", "立即下载", "VIP",
    "充值", "开通会员", "限时优惠", "联系客服", "带货",

    # en
    "click here", "sponsored", "advertisement", "affiliate",
    "promo code", "coupon", "buy now", "limited time",
    "sign up now", "subscribe now", "download now",
    "this post may contain affiliate links",
    "as an amazon associate",
)

# ---- 权威域名评分 ----
TRUSTED_DOMAINS = {
    "github.com": 0.35,
    "gitlab.com": 0.28,
    "stackoverflow.com": 0.32,
    "serverfault.com": 0.28,
    "superuser.com": 0.26,
    "developer.mozilla.org": 0.38,
    "docs.python.org": 0.38,
    "docs.microsoft.com": 0.34,
    "learn.microsoft.com": 0.36,
    "pkg.go.dev": 0.34,
    "go.dev": 0.36,
    "nodejs.org": 0.34,
    "react.dev": 0.34,
    "nextjs.org": 0.34,
    "typescriptlang.org": 0.34,
    "wikipedia.org": 0.22,
    "arxiv.org": 0.30,
    "acm.org": 0.32,
    "ieee.org": 0.32,
}

LOW_QUALITY_DOMAINS = {
    "csdn.net": -0.25,
    "blog.csdn.net": -0.28,
    "baijiahao.baidu.com": -0.35,
    "zhidao.baidu.com": -0.25,
    "360doc.com": -0.30,
    "jianshu.com": -0.20,
    "medium.com": -0.08,
    "dev.to": -0.05,
    "geeksforgeeks.org": -0.16,
    "tutorialspoint.com": -0.18,
    "w3schools.com": -0.10,
    "javatpoint.com": -0.20,
    "programiz.com": -0.08,
}

# ---- 反爬 ----
USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
)

CHALLENGE_MARKERS = (
    "just a moment",
    "cf-browser-verification",
    "challenge-platform",
    "_cf_chl_opt",
    "captcha",
    "verifying you are human",
    "checking your browser",
    "请完成安全验证",
    "人机验证",
)

# 例："http://127.0.0.1:7890"
PROXY = None
