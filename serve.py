import http.server
import socketserver
import webbrowser
import os

PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

print(f"Serving OcuGuard AI Enterprise Suite at http://localhost:{PORT}")
# Open the browser automatically to index.html
webbrowser.open(f"http://localhost:{PORT}/index.html")

try:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("Press Ctrl+C to stop the server.")
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\nServer stopped.")
