from flask import Flask, request, make_response
import qrcode
import io

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

if __name__ == '__main__':
    app.run(debug=True)

