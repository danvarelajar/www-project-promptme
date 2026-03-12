#!/usr/bin/env python3
"""Simple HTTP server that serves test.html from the same folder."""

import http.server
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

handler = http.server.SimpleHTTPRequestHandler
httpd = http.server.HTTPServer(("", 8000), handler)
print("Serving test.html at http://localhost:8000/test.html")
httpd.serve_forever()
