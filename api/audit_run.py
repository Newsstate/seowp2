import json, os, re
from http.server import BaseHTTPRequestHandler
import anthropic


def get_redis():
    url   = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    try:
        from upstash_redis import Redis
        return Redis(url=url, token=token)
    except Exception:
        return None


def store_set(job_id, value):
    r = get_redis()
    if r:
        r.set(f"seo:{job_id}", json.dumps(value), ex=3600)


SYSTEM_PROMPT = """You are a world-class SEO auditor. Use the web_search tool MULTIPLE TIMES to research every aspect of the site, then return ONE JSON object only — no markdown, no backticks, no text outside the JSON.

RESEARCH STEPS — do ALL:
1. Fetch the main URL — read title, meta description, H1-H6 tags, keyword frequency, word count, canonical, lang attribute, schema markup, Open Graph tags, Twitter Cards, iframes, favicon
2. Check robots.txt at domain/robots.txt
3. Check sitemap at domain/sitemap.xml and domain/sitemap_index.xml
4. Search "{domain} PageSpeed Insights mobile desktop score"
5. Search "{domain} Core Web Vitals LCP CLS INP"
6. Search "{domain} Facebook Instagram LinkedIn Twitter YouTube" for social profiles
7. Search "{domain} Google Business Profile reviews rating"
8. Search "{domain} DMARC record" and "{domain} SPF record"
9. Search "{domain} technology stack" to identify CMS, CDN, analytics
10. Check domain/llms.txt
11. Search "{domain} organic keyword rankings traffic"
12. Search "{domain} hreflang"

Return ONLY this exact JSON (fill every field with real discovered data):

{
  "domain": "example.com",
  "overall": {"grade": "A", "summary": "One specific sentence about this site's SEO health"},
  "cats": [
    {"k":"op",  "grade":"A+","lbl":"On-Page SEO","c":"#7F77DD"},
    {"k":"geo", "grade":"A", "lbl":"GEO / AI",   "c":"#1e8449"},
    {"k":"us",  "grade":"B-","lbl":"Usability",  "c":"#c0392b"},
    {"k":"pf",  "grade":"A-","lbl":"Performance","c":"#2980b9"}
  ],
  "op": {
    "title":{"t":"Actual title text","len":76,"ok":false},
    "titleAdvice":"Specific advice for this title.",
    "meta":{"t":"Actual meta text","len":160,"ok":true},
    "metaAdvice":"Specific meta advice.",
    "serpUrl":"https://example.com",
    "serpTitle":"Title up to 57 chars",
    "serpDesc":"Meta up to 155 chars...",
    "h1":[{"tag":"H1","v":"Actual H1 text"}],
    "h1Count":1,"h1Status":"good",
    "hfreq":[{"t":"H2","n":12},{"t":"H3","n":24},{"t":"H4","n":7}],
    "kws":[{"p":"keyword","ti":true,"me":true,"hd":true,"f":35},{"p":"phrase","ti":true,"me":false,"hd":true,"f":20}],
    "wc":2118,"wcOk":true,
    "imgAlt":true,"imgAltDesc":"All images have alt attributes.",
    "canon":"https://example.com/","canonOk":true,
    "noindex":false,"noindexOk":true,"noindexHeader":false,
    "httpsRedir":true,
    "robots":"https://example.com/robots.txt","robotsOk":true,"robotsBlocked":false,
    "sitemap":"https://example.com/sitemap_index.xml","sitemapOk":true,
    "analytics":true,"analyticsTools":["Google Analytics","Google Tag Manager"],
    "schema":true,"schemaTypes":["LocalBusiness","WebPage"],
    "lang":"en","langOk":true,
    "hreflang":false,"hreflangDesc":"No hreflang tags found.",
    "amp":false,"ampDesc":"AMP not enabled.","flash":false
  },
  "geo": {
    "renderPct":"18%","renderOk":true,"renderDesc":"Low render % — good for LLM readability.",
    "llmsTxt":true,"llmsTxtUrl":"https://example.com/llms.txt","llmsDesc":"llms.txt found.",
    "traffic":{"org":107,"paid":0,"ai":0},
    "kws":[{"kw":"brand keyword","co":"IN","pos":1,"vol":90,"tr":27},{"kw":"target phrase","co":"IN","pos":45,"vol":210,"tr":0}],
    "positions":[{"r":"Position 1","n":2},{"r":"Position 2-3","n":0},{"r":"Position 4-10","n":0},{"r":"Position 11-20","n":0},{"r":"Position 21-30","n":0},{"r":"Position 31-100","n":3}]
  },
  "us": {
    "cwv":{"lcp":"3.3s","inp":"164ms","cls":"0.00","pass":true},
    "cwvAdvice":"Core Web Vitals pass Google assessment.",
    "mob":{"score":35,"fcp":"9.5s","si":"9.5s","lcp":"16.3s","tti":"17.3s","tbt":"0.46s","cls":"0","opps":[{"n":"Reduce unused JavaScript","s":"4.84s"},{"n":"Avoid page redirects","s":"0.63s"}]},
    "desk":{"score":68,"fcp":"0.8s","si":"1.0s","lcp":"1.1s","tti":"3.9s","tbt":"0.65s","cls":"0.046","opps":[{"n":"Avoid page redirects","s":"0.19s"}]},
    "viewport":true,"iframes":true,"iframesDesc":"iFrames detected.",
    "fontSizes":true,"tapTargets":true,"favicon":true,"emailPrivacy":true,"flash":false
  },
  "pf": {
    "speed":{"srv":"0.0s","cnt":"4.3s","scr":"7.6s","ok":true},
    "size":{"tot":"2.00MB","html":"0.13MB","css":"0.11MB","js":"1.2MB","img":"0.34MB","other":"0.22MB","ok":true},
    "comp":{"rate":"64%","html":"61%","css":"74%","js":"72%","img":"0%","other":"0%","ok":true},
    "http2":true,"imgOpt":true,
    "minify":false,"minifyDesc":"Some JS/CSS files not minified.",
    "jsErrors":true,"jsErrDesc":"TypeError: $ is not a function",
    "inlineStyles":true,"inlineDesc":"Multiple inline styles detected.",
    "depHtml":false,
    "res":{"tot":106,"html":5,"js":32,"css":20,"img":34,"other":15}
  },
  "social":[
    {"name":"Facebook","url":"https://facebook.com/page","ico":"F","bg":"#1877F2","c":"#fff","linked":true,"stat":""},
    {"name":"Instagram","url":"https://instagram.com/page","ico":"Ig","bg":"#E1306C","c":"#fff","linked":true,"stat":""},
    {"name":"LinkedIn","url":"https://linkedin.com/company/x","ico":"in","bg":"#0A66C2","c":"#fff","linked":true,"stat":""},
    {"name":"X/Twitter","url":"https://x.com/handle","ico":"X","bg":"#000","c":"#fff","linked":true,"stat":""},
    {"name":"YouTube","url":"https://youtube.com/channel/x","ico":"▶","bg":"#FF0000","c":"#fff","linked":true,"stat":"195 subscribers"}
  ],
  "fbPixel":"835561506088336","fbPixelOk":true,
  "ogTags":[{"t":"og:title","v":"Title"},{"t":"og:description","v":"Desc"},{"t":"og:image","v":"https://example.com/img.jpg"}],
  "twitterCard":true,
  "twitterTags":[{"t":"twitter:card","v":"summary_large_image"},{"t":"twitter:title","v":"Title"}],
  "local":{
    "hasAddress":true,"phone":"+91 99715 44461","addr":"13 Sussex RD, Clifton NJ 07012",
    "localSchema":true,"schemaType":"LocalBusiness",
    "gbp":{"found":true,"name":"Business Name","addr":"Full address","phone":"+91 99717 44661","site":"https://example.com/"},
    "reviews":{"rating":4.7,"count":52,"dist":[45,4,0,2,1]}
  },
  "tech":{
    "list":[{"name":"WordPress","ver":""},{"name":"Cloudflare","ver":""},{"name":"Google Analytics","ver":""}],
    "dmarc":false,"dmarcDesc":"No DMARC record — add to DNS.",
    "spf":true,"spfRecord":"v=spf1 include:_spf.google.com ~all",
    "server":"cloudflare","serverIp":"162.159.137.54","charset":"UTF-8","http2":true,"http3":false
  },
  "recommendations":[
    {"priority":1,"title":"Issue title","detail":"Specific actionable advice for this site."},
    {"priority":2,"title":"Issue title","detail":"Specific advice."},
    {"priority":3,"title":"Issue title","detail":"Specific advice."},
    {"priority":4,"title":"Issue title","detail":"Specific advice."},
    {"priority":5,"title":"Issue title","detail":"Specific advice."},
    {"priority":6,"title":"Issue title","detail":"Specific advice."}
  ]
}

IMPORTANT: Use REAL values found for this specific site. Return JSON ONLY."""


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        job_id = ""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            job_id = body.get("job_id", "")
            url    = body.get("url", "").strip()

            client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY", "")
            )

            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": (
                    f"Run a full comprehensive SEO audit on: {url}\n\n"
                    "Use web_search multiple times to research on-page tags, "
                    "robots.txt, sitemap, PageSpeed, Core Web Vitals, social profiles, "
                    "Google Business Profile, reviews, technology stack, DMARC/SPF, "
                    "GEO/AI visibility, keyword rankings, llms.txt, hreflang. "
                    "Return ONLY the JSON report."
                )}]
            )

            raw   = "".join(b.text for b in response.content if b.type == "text")
            match = re.search(r'\{[\s\S]*\}', raw)
            if not match:
                raise ValueError("Could not extract JSON from AI response")

            data = json.loads(match.group(0))

            r      = get_redis()
            stored = {}
            if r:
                v = r.get(f"seo:{job_id}")
                if v:
                    stored = json.loads(v)

            store_set(job_id, {
                "status": "done",
                "data":   data,
                "name":   stored.get("name", ""),
                "email":  stored.get("email", "")
            })

        except Exception as e:
            if job_id:
                store_set(job_id, {"status": "error", "message": str(e)})

        body = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass
