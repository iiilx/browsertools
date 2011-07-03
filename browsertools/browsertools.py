import sys, random, re, time
import cookielib
import mechanize

__all__ = ['Browser', 
           'UserAgent', 
           'ProxyManager']

PROXY_LIST = '/usr/local/share/public_proxies.txt'

class ProxyManager:
    '''Decides what proxy to choose. Returns IPs with different class A block each time.
       Also has option of banishing proxies from rotation for limited time.
    '''
    def __init__(self, seed = None):
        self.PROXY_USER = 'aaron.t.cheung:aaron9991002@'
        self.PROXY_LIST = [r for r in open(PROXY_LIST, 'r').read().split('\n') if r != '']
        self.__RECENT_IP_MAX = 5
        self.__RECENT_A_MAX = 2
        self.__random = random.Random(seed)
        self.recent_ips = []
        self.recent_a = []
        self.limbo = []
        self.current = None
        self.proxy_ip = None

    def _get_ip(self):
        if '@' in self.current:
            self.proxy_ip = self.current.split('@')[1].split(':')[0]
        else:
            self.proxy_ip = self.current.split(':')[0]

    def _get_different_proxy(self):
        while True:
            choice = self.__random.choice(self.PROXY_LIST)
            if choice in self.recent_ips:
                continue
            elif self.recent_ips == []:
                self.recent_ips.append(choice)
                self.recent_a.append(choice.split('.')[0])
                break
            else:
                a_class = choice.split('.')[0]
                if a_class in self.recent_a or choice in self.recent_ips:
                    continue
                if len(self.recent_ips) >= self.__RECENT_IP_MAX:
                    self.recent_ips.pop(0)
                if len(self.recent_a) >= self.__RECENT_A_MAX:
                    self.recent_a.pop(0)
                self.recent_ips.append(choice)
                self.recent_a.append(a_class)
                break
        self.current = choice
        self._get_ip()

    def _check_limbo(self):
        for soul in self.limbo:
            if time.time() > soul[1]:
                self.PROXY_LIST.append(soul[0])
                self.limbo = filter(lambda x: soul[0] not in x[0], self.limbo)
                
    def get(self):
        self._check_limbo()
        self._get_different_proxy()
        return self.PROXY_USER + self.current

    def banish(self, proxy, duration = 10):
        '''Temporarily remove a proxy from rotation due to ban or something similar.
           Ban time is in minutes
        '''
        for p in self.PROXY_LIST:
            if proxy == p or proxy in p.split(':')[0]:
                self.PROXY_LIST.remove(p)
                self.limbo.append([p, time.time() + 60 * duration])

class UserAgent:
    '''Returns a random user agent. Supports random number seeding
    '''
    def __init__(self, seed = None):
        self.user_agent = None
        self.headers = None
        self.random = random.Random(seed)
        self._set_user_agent()

    def _set_user_agent(self):
        self.get_firefox_user_agent()
        #if self.random.randint(0,1):
        #    self.get_firefox_user_agent()
        #else:
        #    self.get_ie_user_agent()

    def get_firefox_user_agent(self):
        self.user_agent = 'Mozilla/5.0 (Windows; U; Windows NT ' + \
        self.random.choice(['5.1', '5.2', '6.1']) + '; en-US; ' + \
        self.random.choice([
            'rv:1.9.0.11) Gecko/2009060215 Firefox/3.0.11',
            'rv:1.9.0.14) Gecko/2009082707 Firefox/3.0.14',
            'rv:1.9.1.4) Gecko/20091016 Firefox/3.5.4',
            'rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5',
        ]) + self.random.choice(['', ' (.NET CLR 3.5.30729)'])
        self.headers = [
            ('User-Agent', self.user_agent),
            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            ('Accept-Language', 'en-us,en;q=0.5'),
            ('Accept-Encoding', 'gzip,deflate'),
            ('Accept-Charset',  'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            ('Keep-Alive', '300'),
            ('Connection', 'keep-alive')
        ]

    def get_ie_user_agent(self):
        self.user_agent = 'Mozilla/4.0 (compatible; MSIE ' + \
        self.random.choice([
            '6.0; Windows NT 5.1; SV1)',
            '6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)',
            '6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.1)',
            '7.0; Windows NT 5.1)',
            '7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)',
            '7.0; Windows NT 6.0; Trident/4.0; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)',
            '8.0; Windows NT 6.1)',
            '8.0; Windows NT 5.1; Trident/4.0; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)'
        ])
        self.headers = [
            ('User-Agent', self.user_agent),
            ('Accept', 'application/x-shockwave-flash, image/gif, image/x-xbitmap, ' + \
                       'image/jpeg, image/pjpeg, application/vnd.ms-excel, ' + \
                       'application/vnd.ms-powerpoint, application/msword, */*'),
            ('Accept-Language', 'en-us'),
            ('Accept-Encoding', 'gzip, deflate'),
            ('Connection', 'Keep-Alive')
        ]

class Browser(mechanize.Browser):
    '''A browser configured to spoof user agents, headers, use proxies, etc.
    '''
    def __init__(self, proxy = None, use_proxy = True, seed = None):
        mechanize.Browser.__init__(self)
        self.set_handle_gzip(True)
        self.set_handle_equiv(True)
        self.set_handle_redirect(True)
        self.set_handle_referer(True)
        self.set_handle_robots(False)
        self.set_handle_refresh(True, max_time = 7, honor_time = False)
        self.set_cookiejar(cookielib.LWPCookieJar())
        self.addheaders = UserAgent().headers
        self.use_proxy = use_proxy
        self.proxy_ip = None
        self._init_proxy(proxy)

    def _init_proxy(self, proxy):
        self.p = ProxyManager()
        if self.use_proxy and not proxy:
            self.set_proxy()
        elif proxy:
            self.set_proxy(proxy)
        elif not self.use_proxy:
            self.proxy_ip = None
  
    def refresh(self):
        self.set_cookiejar(cookielib.LWPCookieJar())
        self.set_proxy()
 
    def set_proxy(self, proxy = None):
        '''Pick a random proxy if a particular one is not defined.
        '''
        if not proxy:
            proxy = self.p.get()
        self.set_proxies( {'http': proxy } )
        if '@' in proxy:
            self.proxy_ip = proxy.split('@')[1].split(':')[0]
        else:
            self.proxy_ip = proxy.split(':')[0]

