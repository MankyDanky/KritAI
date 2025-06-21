from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QImage
import json
import ssl
import urllib.request
import base64
import tempfile

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
        
        # API Key input
        layout.addWidget(QLabel("OpenAI API Key:"))
        self.apiKeyEdit = QLineEdit()
        self.apiKeyEdit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.apiKeyEdit)
        
        # Prompt input
        layout.addWidget(QLabel("Prompt:"))
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
    
    def canvasChanged(self, canvas):
        pass
    
    def generateImage(self):
        api_key = self.apiKeyEdit.text().strip()
        prompt = self.promptEdit.toPlainText().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter your OpenAI API key.")
            return
        
        if not prompt:
            QMessageBox.warning(self, "Error", "Please enter a prompt.")
            return
        
        doc = Krita.instance().activeDocument()
        if doc is None:
            QMessageBox.warning(self, "Error", "No active document found.")
            return
        
        self.statusLabel.setText("Generating...")
        self.generateButton.setEnabled(False)
        
        self.worker = DallEWorker(api_key, prompt, doc.width(), doc.height())
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
    
    def __init__(self, api_key, prompt, width, height):
        super().__init__()
        self.api_key = api_key
        self.prompt = prompt
        # Use 1024x1024 for DALL-E
        self.size = "1024x1024"
    
    def run(self):
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
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
