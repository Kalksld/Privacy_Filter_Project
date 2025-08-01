from flask import Flask, render_template, request, send_file
import os
import re
import cv2
import numpy as np
import easyocr
from pyzbar.pyzbar import decode
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

reader = easyocr.Reader(['en'], gpu=False)

# ✅ Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'murapalaanusha0@gmail.com'
app.config['MAIL_PASSWORD'] = ''  # 🔐 Use your app-specific password

mail = Mail(app)

# ✅ Sensitive data patterns including DOBs
patterns = [
    (r'\b\d{10}\b', '**********'),                          # Phone numbers
    (r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '**********'),          # Emails
    (r'\b\d{12}\b', '************'),                        # Aadhar
    (r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '**********'),           # PAN
    (r'(http|https)://[^\s]+', '**********'),               # URLs
    (r'\b[A-Z]{2}\d{2}[A-Z]{2}\d{4}\b', '**********'),      # Vehicle number
    (r'\b\d{6}\b', '******'),                               # Pincode
    (r'\b(?:\d[ -]*?){13,19}\b', '****************'),       # Credit/Debit cards
    (r'\b(?:\d[ -]*?){8,20}\b', '********************'),    # Bank account numbers
    (r'\d+\s+\w+\s+\w+(?:\s+\w+){0,3}', '***************'), # Address-like patterns
    (r'\b[A-Z0-9]{8,}\b', '**********'),                    # Alphanumeric codes
    (r'\b\d{2}[-/]\d{2}[-/]\d{4}\b', '**********'),          # DOB: 28/07/2003
    (r'\b\d{4}[-/]\d{2}[-/]\d{2}\b', '**********'),          # DOB: 2003-07-28
    (r'\b\d{1,2} [A-Za-z]+ \d{4}\b', '**********'),          # DOB: 28 July 2003
    (r'\b[A-Za-z]+ \d{1,2}, \d{4}\b', '**********'),         # DOB: July 28, 2003
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/text', methods=['GET', 'POST'])
def text():
    masked_text = ""
    if request.method == 'POST':
        input_text = request.form['input_text']
        masked_text = input_text
        for pattern, repl in patterns:
            masked_text = re.sub(pattern, repl, masked_text)
    return render_template('text.html', masked_text=masked_text)

@app.route('/image', methods=['GET', 'POST'])
def image():
    if request.method == 'POST':
        file = request.files['image']
        if file:
            filename = secure_filename(file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)

            # Step 1: Load the image using OpenCV
            img = cv2.imread(image_path)

            # Step 2: Detect and blur QR codes
            qr_codes = decode(img)
            for qr in qr_codes:
                x, y, w, h = qr.rect
                roi = img[y:y+h, x:x+w]
                if roi.size != 0:
                    blurred = cv2.GaussianBlur(roi, (35, 35), 30)
                    img[y:y+h, x:x+w] = blurred

            # Step 3: Detect sensitive text using OCR and blur
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = reader.readtext(img_rgb)

            for (bbox, text, prob) in results:
                for pattern, _ in patterns:
                    if re.search(pattern, text):
                        top_left, _, bottom_right, _ = bbox
                        x1, y1 = map(int, top_left)
                        x2, y2 = map(int, bottom_right)
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
                        roi = img[y1:y2, x1:x2]
                        if roi.size != 0:
                            blurred = cv2.GaussianBlur(roi, (25, 25), 30)
                            img[y1:y2, x1:x2] = blurred
                        break

            # Step 4: Save final image
            blurred_filename = f"blurred_{filename}"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], blurred_filename)
            cv2.imwrite(output_path, img)

            return render_template(
                'image.html',
                uploaded=True,
                original_filename=filename,
                blurred_filename=blurred_filename
            )

    return render_template('image.html', uploaded=False)

@app.route('/download/<filename>')
def download_file(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(path, as_attachment=True)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        msg = Message(
            subject=f"Message from {name}",
            sender=email,
            recipients=[app.config['MAIL_USERNAME']],
            body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        )
        mail.send(msg)
        return render_template('contact.html', success=True)

    return render_template('contact.html', success=False)

@app.route('/features')
def features():
    return render_template('features.html')

if __name__ == '__main__':
    app.run(debug=True)
