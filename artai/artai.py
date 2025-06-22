from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QImage, QColor
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
        self.modeCombo.addItems(["Generate", "Vary", "Edit"])
        self.modeCombo.currentTextChanged.connect(self.onModeChanged)
        layout.addWidget(self.modeCombo)
        
        # Prompt input
        self.promptLabel = QLabel("Prompt:")
        layout.addWidget(self.promptLabel)
        self.promptEdit = QTextEdit()
        self.promptEdit.setMaximumHeight(100)
        layout.addWidget(self.promptEdit)
        
        # Mask painting controls (for Edit mode)
        self.maskFrame = QFrame()
        maskLayout = QHBoxLayout(self.maskFrame)
        maskLayout.setContentsMargins(0, 0, 0, 0)
        
        self.maskToggle = QPushButton("Enable Mask Painting")
        self.maskToggle.setCheckable(True)
        self.maskToggle.clicked.connect(self.onMaskToggle)
        maskLayout.addWidget(self.maskToggle)
        
        maskLayout.addWidget(QLabel("Size:"))
        self.maskSizeSlider = QSlider(Qt.Horizontal)
        self.maskSizeSlider.setMinimum(5)
        self.maskSizeSlider.setMaximum(100)
        self.maskSizeSlider.setValue(20)
        maskLayout.addWidget(self.maskSizeSlider)
        
        self.maskSizeLabel = QLabel("20")
        self.maskSizeSlider.valueChanged.connect(lambda v: self.maskSizeLabel.setText(str(v)))
        maskLayout.addWidget(self.maskSizeLabel)
        
        layout.addWidget(self.maskFrame)
        self.maskFrame.hide()  # Hidden by default
        
        # Generate button
        self.generateButton = QPushButton("Generate")
        self.generateButton.clicked.connect(self.generateImage)
        layout.addWidget(self.generateButton)
        
        # Status
        self.statusLabel = QLabel("Ready")
        layout.addWidget(self.statusLabel)
        
        # Mask painting state
        self.maskPaintingActive = False
        self.maskLayer = None
        self.originalTool = None
    
    def onModeChanged(self, mode):
        if mode == "Vary":
            self.promptLabel.hide()
            self.promptEdit.hide()
            self.maskFrame.hide()
        elif mode == "Edit":
            self.promptLabel.show()
            self.promptEdit.show()
            self.maskFrame.show()
        else:  # Generate
            self.promptLabel.show()
            self.promptEdit.show()
            self.maskFrame.hide()
        
        # Disable mask painting when switching away from Edit mode
        if mode != "Edit" and self.maskPaintingActive:
            self.disableMaskPainting()
    
    def onMaskToggle(self):
        if self.maskToggle.isChecked():
            self.enableMaskPainting()
        else:
            self.disableMaskPainting()
    
    def enableMaskPainting(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            self.maskToggle.setChecked(False)
            return
        
        self.maskPaintingActive = True
        self.maskToggle.setText("Disable Mask Painting")
        
        # Create or find mask layer
        self.maskLayer = doc.createNode("AI_Edit_Mask", "paintlayer")
        doc.rootNode().addChildNode(self.maskLayer, None)
        doc.setActiveNode(self.maskLayer)
        
        self.statusLabel.setText("Mask painting enabled - Paint red areas to edit, then generate")
    
    def disableMaskPainting(self):
        self.maskPaintingActive = False
        self.maskToggle.setChecked(False)
        self.maskToggle.setText("Enable Mask Painting")
        self.statusLabel.setText("Ready")
    
    def canvasChanged(self, canvas):
        pass
    
    def getMaskImage(self, doc):
        """Create a proper mask: transparent where user painted, opaque everywhere else"""
        if not self.maskLayer:
            return None
        
        # Get document dimensions
        w, h = doc.width(), doc.height()
        
        # Get mask layer pixel data
        pixel_data = self.maskLayer.pixelData(0, 0, w, h)
        
        # Create mask array - start with all opaque white (preserve everything)
        mask_array = bytearray(w * h * 4)
        for i in range(0, len(mask_array), 4):
            mask_array[i:i+4] = [255, 255, 255, 255]  # White opaque
        
        # Convert BGRA pixel data and mark painted areas as transparent
        pixel_array = bytearray(pixel_data)
        
        for i in range(0, len(pixel_array), 4):
            # Get BGRA values from mask layer
            b, g, r, a = pixel_array[i:i+4]
            
            # If there's any visible paint (any color with opacity), make it transparent in mask
            if a > 10:  # Any visible paint on mask layer
                # Make this area transparent (DALL-E will edit here)
                mask_array[i:i+4] = [0, 0, 0, 0]
        
        # Create temporary file and save mask
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file.close()
        
        # Create QImage from mask data and save
        qimage = QImage(bytes(mask_array), w, h, QImage.Format_ARGB32)
        qimage.save(temp_file.name, "PNG")
        
        # Read the PNG data back
        with open(temp_file.name, 'rb') as f:
            png_data = f.read()
        
        # Clean up temp file
        os.unlink(temp_file.name)
        
        return png_data

    def getCurrentLayerImage(self, doc):
        """Export the entire document (all visible layers except mask) as PNG image data"""
        # Create temporary file for export
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file.close()
        
        # Hide mask layer if it exists before export
        mask_was_visible = False
        if self.maskLayer:
            mask_was_visible = self.maskLayer.visible()
            self.maskLayer.setVisible(False)
        
        # Export the document as PNG (without mask layer)
        doc.exportImage(temp_file.name, InfoObject())
        
        # Restore mask layer visibility
        if self.maskLayer:
            self.maskLayer.setVisible(mask_was_visible)
        
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
            mask_data = None
        elif mode == "Vary":
            image_data = self.getCurrentLayerImage(doc)
            if not image_data:
                QMessageBox.warning(self, "Error", "No document content found to vary.")
                return
            prompt = None
            mask_data = None
        else:  # Edit mode
            prompt = self.promptEdit.toPlainText().strip()
            if not prompt:
                QMessageBox.warning(self, "Error", "Please enter a prompt for editing.")
                return
            image_data = self.getCurrentLayerImage(doc)
            if not image_data:
                QMessageBox.warning(self, "Error", "No document content found to edit.")
                return
            mask_data = self.getMaskImage(doc)
            if not mask_data:
                QMessageBox.warning(self, "Error", "No mask found. Please paint mask areas first.")
                return
        
        self.statusLabel.setText("Generating...")
        self.generateButton.setEnabled(False)
        
        self.worker = DallEWorker(api_key, prompt, doc.width(), doc.height(), image_data, mask_data)
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
            mode = self.modeCombo.currentText()
            layer_name = f"AI {mode}"
            new_layer = doc.createNode(layer_name, "paintlayer")
            
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
            
            # Clean up mask layer if this was an edit operation
            if mode == "Edit" and self.maskLayer:
                doc.rootNode().removeChildNode(self.maskLayer)
                self.maskLayer = None
                if self.maskPaintingActive:
                    self.disableMaskPainting()
            
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
    
    def __init__(self, api_key, prompt, width, height, image_data=None, mask_data=None):
        super().__init__()
        self.api_key = api_key
        self.prompt = prompt
        self.width = width
        self.height = height
        self.image_data = image_data
        self.mask_data = mask_data
        # Use 1024x1024 for DALL-E
        self.size = "1024x1024"
    
    def run(self):
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            if self.mask_data:  # Edit mode
                url = "https://api.openai.com/v1/images/edits"
                
                # Create multipart form data for editing
                boundary = '----WebKitFormBoundary' + str(id(self))
                body = []
                
                # Add image
                body.append(f'--{boundary}')
                body.append('Content-Disposition: form-data; name="image"; filename="image.png"')
                body.append('Content-Type: image/png')
                body.append('')
                body.append(self.image_data.decode('latin1'))
                
                # Add mask
                body.append(f'--{boundary}')
                body.append('Content-Disposition: form-data; name="mask"; filename="mask.png"')
                body.append('Content-Type: image/png')
                body.append('')
                body.append(self.mask_data.decode('latin1'))
                
                # Add prompt
                body.append(f'--{boundary}')
                body.append('Content-Disposition: form-data; name="prompt"')
                body.append('')
                body.append(self.prompt)
                
                # Add other parameters
                body.append(f'--{boundary}')
                body.append('Content-Disposition: form-data; name="n"')
                body.append('')
                body.append('1')
                
                body.append(f'--{boundary}')
                body.append('Content-Disposition: form-data; name="size"')
                body.append('')
                body.append(self.size)
                
                body.append(f'--{boundary}')
                body.append('Content-Disposition: form-data; name="response_format"')
                body.append('')
                body.append('b64_json')
                
                body.append(f'--{boundary}--')
                
                form_data = '\r\n'.join(body).encode('latin1')
                
                request = urllib.request.Request(
                    url,
                    data=form_data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": f"multipart/form-data; boundary={boundary}"
                    }
                )
                
            elif self.image_data:  # Vary mode
                url = "https://api.openai.com/v1/images/variations"
                
                # Create multipart form data for variations
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
                # Try to get error details from response
                try:
                    error_data = response.read().decode('utf-8')
                    self.error.emit(f"API Error {response.getcode()}: {error_data}")
                except:
                    self.error.emit(f"API Error {response.getcode()}")
                
        except urllib.error.HTTPError as e:
            # Get detailed error message for HTTP errors
            try:
                error_data = e.read().decode('utf-8')
                error_json = json.loads(error_data)
                if 'error' in error_json and 'message' in error_json['error']:
                    self.error.emit(f"HTTP {e.code}: {error_json['error']['message']}")
                else:
                    self.error.emit(f"HTTP {e.code}: {error_data}")
            except:
                self.error.emit(f"HTTP {e.code}: {str(e)}")
        except Exception as e:
            self.error.emit(str(e))

# Register the extension and docker
Krita.instance().addExtension(ArtAI(Krita.instance()))
Krita.instance().addDockWidgetFactory(DockWidgetFactory("artaiDocker", DockWidgetFactoryBase.DockRight, ArtAIDocker))
