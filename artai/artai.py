from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QRect
import json
import ssl
import urllib.request
import base64
import tempfile
import io
import os

class ArtAI(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        pass

class ArtAIDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtAI")
        
        mainWidget = QWidget(self)
        self.setWidget(mainWidget)
        layout = QVBoxLayout()
        mainWidget.setLayout(layout)

        # Load QSS stylesheet from file
        qss_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "style.qss")
        with open (qss_path, "r") as file:
            mainWidget.setStyleSheet(file.read())
        
        # API Key input
        layout.addWidget(QLabel("OpenAI API Key:"))
        self.apiKeyEdit = QLineEdit()
        self.apiKeyEdit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.apiKeyEdit)
        
        # Mode selection
        layout.addWidget(QLabel("Mode:"))
        self.modeCombo = QComboBox()
        self.modeCombo.addItems(["Generate", "Vary"])
        self.modeCombo.currentTextChanged.connect(self.onModeChanged)
        layout.addWidget(self.modeCombo)
        
        # Prompt input
        self.promptLabel = QLabel("Prompt:")
        layout.addWidget(self.promptLabel)
        self.promptEdit = QTextEdit()
        self.promptEdit.setMaximumHeight(100)
        layout.addWidget(self.promptEdit)
        
        # Generate button
        self.generateButton = QPushButton("Generate")
        self.generateButton.clicked.connect(self.generateImage)
        layout.addWidget(self.generateButton)
        
        # Status
        self.statusLabel = QLabel("Ready")
        layout.addWidget(self.statusLabel)
    
    def onModeChanged(self, mode):
        if mode == "Vary":
            self.promptLabel.hide()
            self.promptEdit.hide()
        else:
            self.promptLabel.show()
            self.promptEdit.show()
    
    def canvasChanged(self, canvas):
        pass
    
    def getCurrentLayerImage(self, doc):
        """Export the entire document (all visible layers) as PNG image data"""
        # Create temporary file for export
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file.close()
        
        # Export the document as PNG (includes all visible layers)
        doc.exportImage(temp_file.name, InfoObject())
        
        # Read the PNG data back
        with open(temp_file.name, 'rb') as f:
            png_data = f.read()
        
        # Clean up temp file
        os.unlink(temp_file.name)
        
        return png_data
    
    def generateImage(self):
        api_key = self.apiKeyEdit.text().strip()
        mode = self.modeCombo.currentText()
        
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter your OpenAI API key.")
            return
        
        doc = Krita.instance().activeDocument()
        if doc is None:
            QMessageBox.warning(self, "Error", "No active document found.")
            return
        
        if mode == "Generate":
            prompt = self.promptEdit.toPlainText().strip()
            if not prompt:
                QMessageBox.warning(self, "Error", "Please enter a prompt.")
                return
            image_data = None
        else:  # Vary mode
            image_data = self.getCurrentLayerImage(doc)
            if not image_data:
                QMessageBox.warning(self, "Error", "No document content found to vary.")
                return
            prompt = None
        
        self.statusLabel.setText("Generating...")
        self.generateButton.setEnabled(False)
        
        self.worker = DallEWorker(api_key, prompt, doc.width(), doc.height(), image_data)
        self.worker.finished.connect(self.onComplete)
        self.worker.error.connect(self.onError)
        self.worker.start()
    
    def onComplete(self, image_data):
        try:
            doc = Krita.instance().activeDocument()
            
            # Save generated image to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            temp_file.write(image_data)
            temp_file.close()
            
            # Load and resize image to canvas size
            qimage = QImage(temp_file.name)
            resized = qimage.scaled(doc.width(), doc.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            
            # Create new layer
            new_layer = doc.createNode("AI Generated", "paintlayer")
            
            # Convert to ARGB format
            if resized.format() != QImage.Format_ARGB32:
                resized = resized.convertToFormat(QImage.Format_ARGB32)
            
            # Get pixel data and swap ARGB to BGRA for Krita
            pixel_data = bytearray(resized.bits().asstring(resized.byteCount()))
            for i in range(0, len(pixel_data), 4):
                pixel_data[i], pixel_data[i + 2] = pixel_data[i + 2], pixel_data[i]
            
            # Set pixel data to layer
            new_layer.setPixelData(bytes(pixel_data), 0, 0, doc.width(), doc.height())
            
            # Add layer to document
            doc.rootNode().addChildNode(new_layer, None)
            doc.refreshProjection()
            
            self.statusLabel.setText("Complete!")
            
        except Exception as e:
            self.statusLabel.setText(f"Error: {str(e)}")
        
        self.generateButton.setEnabled(True)
    
    def onError(self, error_message):
        self.statusLabel.setText(f"Error: {error_message}")
        self.generateButton.setEnabled(True)

class DallEWorker(QThread):
    finished = pyqtSignal(bytes)
    error = pyqtSignal(str)
    
    def __init__(self, api_key, prompt, width, height, image_data=None):
        super().__init__()
        self.api_key = api_key
        self.prompt = prompt
        self.width = width
        self.height = height
        self.image_data = image_data
        # Use 1024x1024 for DALL-E
        self.size = "1024x1024"
    
    def run(self):
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            if self.image_data:  # Vary mode
                url = "https://api.openai.com/v1/images/variations"
                
                # Create multipart form data
                boundary = '----formdata-boundary-' + str(id(self))
                body = []
                body.append(f'--{boundary}'.encode())
                body.append(b'Content-Disposition: form-data; name="image"; filename="image.png"')
                body.append(b'Content-Type: image/png')
                body.append(b'')
                body.append(self.image_data)
                body.append(f'--{boundary}'.encode())
                body.append(b'Content-Disposition: form-data; name="n"')
                body.append(b'')
                body.append(b'1')
                body.append(f'--{boundary}'.encode())
                body.append(b'Content-Disposition: form-data; name="size"')
                body.append(b'')
                body.append(self.size.encode())
                body.append(f'--{boundary}'.encode())
                body.append(b'Content-Disposition: form-data; name="response_format"')
                body.append(b'')
                body.append(b'b64_json')
                body.append(f'--{boundary}--'.encode())
                
                form_data = b'\r\n'.join(body)
                
                request = urllib.request.Request(
                    url,
                    data=form_data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": f"multipart/form-data; boundary={boundary}"
                    }
                )
            else:  # Generate mode
                url = "https://api.openai.com/v1/images/generations"
                data = {
                    "model": "dall-e-3",
                    "prompt": self.prompt,
                    "size": self.size,
                    "quality": "standard",
                    "n": 1,
                    "response_format": "b64_json"
                }
                
                json_data = json.dumps(data).encode('utf-8')
                request = urllib.request.Request(
                    url,
                    data=json_data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
            
            response = urllib.request.urlopen(request, timeout=60, context=ssl_context)
            
            if response.getcode() == 200:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                if 'data' in result and len(result['data']) > 0:
                    image_b64 = result['data'][0]['b64_json']
                    image_data = base64.b64decode(image_b64)
                    self.finished.emit(image_data)
                else:
                    self.error.emit("No image data received")
            else:
                self.error.emit(f"API Error {response.getcode()}")
                
        except Exception as e:
            self.error.emit(str(e))

# Register the extension and docker
Krita.instance().addExtension(ArtAI(Krita.instance()))
Krita.instance().addDockWidgetFactory(DockWidgetFactory("artaiDocker", DockWidgetFactoryBase.DockRight, ArtAIDocker))
