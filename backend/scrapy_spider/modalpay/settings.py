BOT_NAME = "modalpay"
SPIDER_MODULES = ["modalpay.spiders"]
NEWSPIDER_MODULE = "modalpay.spiders"

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1

# Playwright for JS-rendered pages
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000

# Output
FEEDS = {
    "modalpay_data.json": {
        "format": "json",
        "encoding": "utf8",
        "overwrite": True,
        "indent": 2,
    }
}

LOG_LEVEL = "INFO"
USER_AGENT = "TxLogPay-Research-Bot/1.0"
