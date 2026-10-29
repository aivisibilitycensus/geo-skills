#!/usr/bin/env python3
"""Local test server for geo-migration-guard. Simulates one fictional site
(Larkspur Ridge Cycles) before and after a replatform on the same host.

  python3 migration_server.py --mode before --port 8766
  python3 migration_server.py --mode after  --port 8766
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SIZING = ("Choosing the right frame size matters more than any upgrade. Measure your inseam standing "
          "against a wall in socks, then multiply by 0.67 for a road frame in centimeters or by 0.226 for a "
          "mountain frame in inches. Reach matters too: if you sit between sizes, riders with longer arms "
          "usually take the larger frame and riders who want quick handling take the smaller one. ") * 6
TUBELESS = ("Tubeless tires run at lower pressure without pinch flats. Start with tubeless-ready rims and "
            "tires, fit a valve, add sealant through the valve core, and seat the bead with a burst of air. "
            "Shake the wheel so the sealant coats the casing, then top up every three months. ") * 6
FITTING = ("Our bike fitting session takes ninety minutes. We measure flexibility, saddle height, setback "
           "and reach, then adjust your bike on a trainer while you ride. You leave with a written report. ") * 4
GRAVEL = ("Gravel bikes for mixed surfaces, from steel all-rounders to carbon race frames. Every bike is built "
          "and checked in our workshop before collection. ") * 5
WINTER = ("Riding through winter is easier with fenders, a rear light that runs all day, and wider tires at "
          "lower pressure. Clean the chain weekly, because road salt wears drivetrains fast. ") * 5
ABOUT = "Larkspur Ridge Cycles is a fictional bike shop used for testing. We fix, fit and sell bikes. " * 3


def page(title, h1, body, jsonld=None, head_extra="", js_only=False):
    ld = ""
    if jsonld:
        ld = '<script type="application/ld+json">' + json.dumps(jsonld) + "</script>"
    main = f"<main><h1>{h1}</h1><p>{body}</p></main>"
    if js_only:
        main = ('<div id="root"></div><script>document.getElementById("root").innerHTML = '
                + json.dumps(f"<main><h1>{h1}</h1><p>{body}</p></main>") + ";</script>")
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>{title}</title>{head_extra}{ld}</head>"
            f"<body><!-- SYNTHETIC TEST PAGE: fictional business --><nav><a href=\"/\">Home</a> <a href=\"/guides\">Guides</a></nav>"
            f"{main}<footer>Larkspur Ridge Cycles (fictional)</footer></body></html>")


ART = lambda h: {"@context": "https://schema.org", "@type": "Article", "headline": h}  # noqa: E731
FAQ = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}
SHOP = {"@context": "https://schema.org", "@type": "BikeStore", "name": "Larkspur Ridge Cycles"}

BEFORE = {
    "/": page("Larkspur Ridge Cycles | Bike Shop", "Larkspur Ridge Cycles", ABOUT, SHOP),
    "/guides/bike-sizing": page("Bike Size Guide: How to Choose a Frame Size | Larkspur Ridge Cycles",
                                "How to choose a bike frame size", SIZING, [ART("How to choose a bike frame size"), FAQ]),
    "/guides/tubeless-setup": page("How to Set Up Tubeless Tires | Larkspur Ridge Cycles",
                                   "How to set up tubeless tires", TUBELESS, ART("How to set up tubeless tires")),
    "/services/bike-fitting": page("Professional Bike Fitting | Larkspur Ridge Cycles", "Bike fitting", FITTING,
                                   {"@context": "https://schema.org", "@type": "Service", "name": "Bike fitting"}),
    "/shop/gravel-bikes": page("Gravel Bikes | Larkspur Ridge Cycles", "Gravel bikes", GRAVEL),
    "/blog/winter-riding-tips": page("Winter Riding Tips | Larkspur Ridge Cycles", "Winter riding tips", WINTER,
                                     ART("Winter riding tips")),
    "/about": page("About Us | Larkspur Ridge Cycles", "About Larkspur Ridge Cycles", ABOUT),
    "/old-promo": page("Spring Service Offer | Larkspur Ridge Cycles", "Spring service offer", "Book a service. " * 20),
}
ROBOTS_BEFORE = "User-agent: *\nDisallow: /cart\n"

AFTER = {
    "/": page("Larkspur Ridge Cycles | Bike Shop", "Larkspur Ridge Cycles", ABOUT, SHOP),
    "/learn/bike-sizing": page("Bike Size Guide: How to Choose a Frame Size | Larkspur Ridge Cycles",
                               "How to choose a bike frame size", SIZING, [ART("How to choose a bike frame size"), FAQ]),
    "/learn/tubeless-setup": page("How to Set Up Tubeless Tires | Larkspur Ridge Cycles",
                                  "How to set up tubeless tires", TUBELESS, ART("How to set up tubeless tires"), js_only=True),
    "/bikes/gravel": page("Gravel Bikes | Larkspur Ridge Cycles", "Gravel bikes", GRAVEL,
                          head_extra='<meta name="robots" content="noindex, follow">'),
    "/journal/winter-riding": page("Winter Riding Tips | Larkspur Ridge Cycles", "Winter riding tips", WINTER[: len(WINTER) // 2],
                                   head_extra='<link rel="canonical" href="/journal/">'),
    "/journal/": page("Journal | Larkspur Ridge Cycles", "Journal", "Stories from the workshop."),
    "/about-us": page("About Us | Larkspur Ridge Cycles", "About Larkspur Ridge Cycles", ABOUT),
}
REDIRECTS_AFTER = {
    "/guides/bike-sizing": (301, "/learn/bike-sizing"),
    "/guides/tubeless-setup": (302, "/learn/tubeless"),
    "/learn/tubeless": (301, "/learn/tubeless-setup"),
    "/services/bike-fitting": (301, "/"),
    "/shop/gravel-bikes": (301, "/bikes/gravel"),
    "/blog/winter-riding-tips": (301, "/journal/winter-riding"),
    "/about": (301, "/about-us"),
}
ROBOTS_AFTER = ("User-agent: *\nDisallow: /cart\n\nUser-agent: GPTBot\nDisallow: /\n\n"
                "User-agent: PerplexityBot\nDisallow: /\n\nUser-agent: Claude-SearchBot\nDisallow: /learn/\n")


class H(BaseHTTPRequestHandler):
    mode = "before"

    def log_message(self, *a):
        pass

    def _send(self, code, body=b"", ctype="text/html; charset=utf-8", headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/robots.txt":
            return self._send(200, (ROBOTS_BEFORE if self.mode == "before" else ROBOTS_AFTER).encode(), "text/plain")
        pages = BEFORE if self.mode == "before" else AFTER
        if self.mode == "after" and path in REDIRECTS_AFTER:
            code, loc = REDIRECTS_AFTER[path]
            return self._send(code, b"", headers={"Location": loc})
        if path in pages:
            return self._send(200, pages[path].encode())
        return self._send(404, b"<html><head><title>Not found</title></head><body><h1>Not found</h1></body></html>")

    do_HEAD = do_GET


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["before", "after"], required=True)
    ap.add_argument("--port", type=int, default=8766)
    a = ap.parse_args()
    H.mode = a.mode
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
