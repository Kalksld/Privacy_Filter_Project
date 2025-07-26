from flask import Flask, render_template, request, send_file
import os
import re
import cv2
import numpy as np
import easyocr
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

reader = easyocr.Reader(['en'])

# Regex patterns
patterns = [
    (r'\b\d{10}\b', '**********'),                                      # Phone numbers
    (r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '**********'),  
    (r'\b\d{12}\b', '************'),                                    # Aadhar
    (r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '**********'),                       # PAN
    (r'(http|https)://[^\s]+', '**********'),                           # URL
    (r'\b[A-Z]{2}\d{2}[A-Z]{2}\d{4}\b', '**********'),                  # Vehicle number
    (r'\b\d{6}\b', '******'),                                           # Pincode
    (r'\b(?:\d[ -]*?){13,19}\b', '****************'),                   # Credit/Debit card
    (r'\b(?:\d[ -]*?){8,20}\b', '********************'),                # Bank account numbers
    (r'\d+\s+\w+\s+\w+(?:\s+\w+){0,3}', '***************')              # Simple address pattern
]

@app.route('/')
def home():
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

            img = cv2.imread(image_path)
            results = reader.readtext(image_path)

            for (bbox, text, prob) in results:
                for pattern, _ in patterns:
                    if re.search(pattern, text):
                        (top_left, top_right, bottom_right, bottom_left) = bbox
                        top_left = tuple(map(int, top_left))
                        bottom_right = tuple(map(int, bottom_right))
                        roi = img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
                        if roi.size != 0:
                            blur = cv2.GaussianBlur(roi, (23, 23), 30)
                            img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]] = blur

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

if __name__ == '__main__':
    app.run(debug=True)