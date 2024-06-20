#call with: python httpserver.py /path/to/your/directory --port 8080

from flask import Flask, request, make_response, send_from_directory, abort
from werkzeug.utils import safe_join
import qrcode
import io
import os
import argparse

app = Flask(__name__)


@app.route('/qrcode', methods=['GET'])
def generate_qr():
    content = request.args.get('content')
    
    if not content:
        return "Content parameter is missing", 400
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    response = make_response(img_io.getvalue())
    response.headers.set('Content-Type', 'image/png')
#    response.headers.set('Content-Disposition', 'attachment', filename='qrcode.png')

    return response

@app.route('/')
def index():
    # Serve the index.html file if it exists
    index_path = safe_join(app.root_path, 'index.html')
    if os.path.isfile(index_path):
        return send_from_directory(app.root_path, 'index.html')
    else:
        return "Index file not found", 404

@app.route('/<path:filename>')
def serve_file(filename):
    # Safely join the path to prevent directory traversal attacks
    file_path = safe_join(app.root_path, filename)
    if os.path.isfile(file_path):
        return send_from_directory(app.root_path, filename)
    else:
        abort(404)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flask server to serve files from a given directory.')
    parser.add_argument('directory', metavar='DIR', type=str, nargs='?', default='.',
                        help='The directory to serve files from (default: current directory)')
    parser.add_argument('--port', type=int, default=8000,
                        help='The port to serve on (default: 8000)')
    args = parser.parse_args()

    # Set the directory to serve files from
    app.root_path = os.path.abspath(args.directory)
    
#    app.run(host='0.0.0.0', port=args.port)

    from waitress import serve
    serve(app, host="0.0.0.0", port=args.port)
