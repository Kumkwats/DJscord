# adapted from : https://gitea.arpa.li/JustAnotherArchivist/little-things/src/branch/master/youtube-extract

import re
import itertools

def extract_id_from_urls(yt_url: str):
    # Only one slash before so it still matches inside URLs when slashes were collapsed.
    domainPattern = re.compile(r'/(www\.|m\.)?(youtube\.(com|de|fr|co\.uk|it|es|at|pt|gr|hu|ro|pl|dk|no|se|fi|ee|lt|lv|ru|by|cz|sk|si|rs|hr|ca)|(music|gaming)\.youtube\.com|(es|uk|pl|ru|it|jp|br)\.youtube\.com|youtube-nocookie\.com)(:\d+)?/', re.IGNORECASE)

    noisePattern = '|'.join([
        r'//www\.youtube\.com/s/(desktop|player)/[0-9a-f]+/',
        r'//www\.youtube\.com/s/gaming/emoji/',
        r'//www\.youtube\.com/redirect\?event=channel_banner&',
        r'//www\.youtube\.com/redirect\?(?=(\S*&)?event=video_description(&|$))(?!(\S*&)?v=)',
        r'//www\.youtube\.com/yts/',
        r'//www\.youtube\.com/img/',
        r'//www\.youtube\.com/youtubei/',
        r'//www\.youtube\.com/ads(/|$)',
        r'//www\.youtube\.com/creators(/|$)',
        r'//www\.youtube\.com/(player|iframe)_api(\?|$)',
        r'//www\.youtube\.com/error(_204)?/?\?',
        r'//www\.youtube\.com/(about|t|howyoutubeworks)([/?]|$)',
        r'//www\.youtube\.com/results/?(\?|$)',
        r'//www\.youtube\.com/premium/?\?',
        r'//www\.youtube\.com/new([/?]|$)',
        r'//www\.youtube\.com/?(\?(?!(\S*&)?v=)|$)',
        r'//www\.youtube\.com/embed/("|%22|' r"'|%27" r')(%20)?(\+|%3B)', # JS extraction stuff
        r'//www\.youtube\.com/service_ajax$',
        r'//www\.youtube\.com/watch(\?v=)?$',
        r'//consent\.(youtube|google)\.com/',
        r'//www\.youtube\.com/(c|user|channel|watch(_popup)?(\.php)?|embed|e|v|redirect|(my_videos_)?upload)(%[23]F|/)?$', # Miscellaneous crap
    ])

    channelPattern = '|'.join([
        r'''/www\.youtube\.com/c/[^/?&=."'>\\\s]+''',
        r'/www\.youtube\.com/user/[A-Za-z0-9]{1,20}',
        r'/www\.youtube\.com/channel/UC[0-9A-Za-z_-]{22}',
        r'''/www\.youtube\.com/[^/?&=."'>\\\s]+(?=/?(\s|\\?["'>]|$))''',
    ])

    # Make sure that the last 11 chars of the match are always the video ID (because Python's re doesn't support \K).
    # If necessary, use lookahead assertions to match further stuff after the video ID.
    videoPattern = '|'.join([
        # Normal watch URL
        r'/www\.youtube\.com/watch(_popup)?(\.php)?/?\?(\S*&)?v=[0-9A-Za-z_-]{11}',
        r'/www\.youtube\.com/watch/[0-9A-Za-z_-]{11}',
        # Embeds
        r'/www\.youtube\.com/e(mbed)?/(?!videoseries\?)[0-9A-Za-z_-]{11}',
        r'/www\.youtube\.com/embed/?\?(\S*&)?v=[0-9A-Za-z_-]{11}',
        # Shortener
        r'/(?i:youtu\.be)(:\d+)?/[0-9A-Za-z_-]{11}',
        # Shorts
        r'/www\.youtube\.com/shorts/[0-9A-Za-z_-]{11}',
        # Old (Flash) embeds
        r'/www\.youtube\.com/v/[0-9A-Za-z_-]{11}',
        # Redirects from links in video descriptions
        r'/www\.youtube\.com/redirect\?(\S*&)?v=[0-9A-Za-z_-]{11}(?=&|$)',
        # Tracking and other crap
        r'/www\.youtube\.com/(ptracking|set_awesome)\?(\S*&)?video_id=[0-9A-Za-z_-]{11}',
        r'/www\.youtube\.com/api/timedtext\?(\S*&)?v=[0-9A-Za-z_-]{11}',
        r'/www\.youtube\.com/(my_videos_)?edit\?(\S*&)?video_id=[0-9A-Za-z_-]{11}',
        r'/www\.youtube\.com/(all_comments|attribution|cthru|get_endscreen|livestreaming/dashboard)\?(\S*&)?v=[0-9A-Za-z_-]{11}',
        # Generic v parameter on watch URLs including with percent encoding; this covers e.g. google.com/url?... or the oEmbed
        r'/watch/?\?(\S*&)?v=[0-9A-Za-z_-]{11}',
        # Generic v parameter on anything
        r'[?&]v=[0-9A-Za-z_-]{11}(?=&|\s|$)',
    ])

    def _percentdecode(s):
        return s.replace('%2F', '/').replace('%3A', ':').replace('%3F', '?').replace('%3D', '=').replace('%26', '&')


    matchers = [
        # (pattern, paramSearch, function(match: list[str]) -> output str or None); returning None stops further processing of a line
        # If paramSearch is True, a corresponding pattern with [/:?=&] replaced by their percent encodings is generated; the reverse replacement is done again automatically before calling the function.
        [noisePattern, False, lambda m: None],
        [channelPattern, True, lambda m: 'https://www.youtube.com/' + m[0].split('/', 2)[-1].rstrip('/')],
        [videoPattern, True, lambda m: f'https://www.youtube.com/watch?v={m[0][-11:]}'],
        [r'/www\.youtube\.com/(?:playlist|watch|embed(?:/videoseries|/\+lastest|/playlist)?/?)\?(?:\S*&)?list=UU([0-9A-Za-z_-]+)', True, lambda m: f'https://www.youtube.com/channel/UC{m[1]}'],
        [r'/www\.youtube\.com/(?:playlist|watch|embed(?:/videoseries|/\+lastest|/playlist)?/?)\?(?:\S*&)?list=((PL|FL|RD|OL)[0-9A-Za-z_-]+)', True, lambda m: f'https://www.youtube.com/playlist?list={m[1]}'],
        [r'/www\.youtube\.com/embed/?\?(?=(?:\S*&)?listType=user_uploads(?:&|$))(?:\S*&)?list=([A-Za-z0-9]{1,20})', True, lambda m: f'https://www.youtube.com/user/{m[1]}'],
        [r'/www\.youtube\.com/rss/user/([A-Za-z0-9]{1,20})', True, lambda m: f'https://www.youtube.com/user/{m[1]}'],
        [r'/www\.youtube\.com/(?:subscription_center\?(?:\S*&)?add_user=|subscribe_widget\?(?:\S*&)?p=|profile\?(?:\S*&)?user=)([A-Za-z0-9]{1,20})', True, lambda m: f'https://www.youtube.com/user/{m[1]}'],
        [r'/www\.youtube\.com/feeds/videos\.xml\?(?:\S*&)?channel_id=(UC[0-9A-Za-z_-]+)', True, lambda m: f'https://www.youtube.com/channel/{m[1]}'],
        [r'/www\.youtube\.com(?:/view_play_list\?(?:\S*&)?p=|/playlist\?(?:.*&)?list=)([0-9A-F]{16})(?=(&|\s|$))', True, lambda m: f'https://www.youtube.com/playlist?list=PL{m[1]}'],
        [r'/(?i:i\.ytimg\.com|img\.youtube\.com)(?::\d+)?/vi/([0-9A-Za-z_-]{11})/', True, lambda m: f'https://www.youtube.com/watch?v={m[1]}'],
    ]

    # Compile pattern and generate one for parameters if desired
    for e in matchers:
        e[0] = re.compile(e[0])

    url = re.sub(r'https?://', '//', raw_url.strip())
    url = domainPattern.sub('/www.youtube.com/', url)
    decodedLine = _percentdecode(url)
    hadMatches = False
    for pattern, paramSearch, func in matchers:
        results = set()
        for m in itertools.chain((x for x in pattern.finditer(url)), (x for x in pattern.finditer(decodedLine)) if paramSearch else ()):
            hadMatches = True
            r = func(m)
            if r in results:
                continue
            results.add(r)
            if r is None:
                break
            # sys.stdout.buffer.write(r.encode('utf-8', 'surrogateescape'))
            # sys.stdout.buffer.write(b'\n')
        if None in results:
            break
    if not hadMatches:
        # sys.stderr.buffer.write(raw_url)
        return None
