from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import os
import json
import shutil
from datetime import datetime

class ArtGitDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtGit Version History")
        
        # Create main widget and layout
        mainWidget = QWidget(self)
        self.setWidget(mainWidget)
        mainWidget.setLayout(QVBoxLayout())
        
        # Title label
        titleLabel = QLabel("Version History")
        titleLabel.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        mainWidget.layout().addWidget(titleLabel)
        
        # Commit section
        commitGroupBox = QGroupBox("Create New Version")
        commitLayout = QVBoxLayout()
        commitGroupBox.setLayout(commitLayout)
        
        # Commit message input
        self.commitMessageEdit = QLineEdit()
        self.commitMessageEdit.setPlaceholderText("Enter commit message...")
        commitLayout.addWidget(QLabel("Commit Message:"))
        commitLayout.addWidget(self.commitMessageEdit)
        
        # Commit button
        self.commitButton = QPushButton("Commit Current Version")
        self.commitButton.clicked.connect(self.commitCurrentVersion)
        commitLayout.addWidget(self.commitButton)
        
        mainWidget.layout().addWidget(commitGroupBox)
        
        # Version history list
        historyGroupBox = QGroupBox("Version History")
        historyLayout = QVBoxLayout()
        historyGroupBox.setLayout(historyLayout)
        
        self.historyList = QListWidget()
        self.historyList.itemDoubleClicked.connect(self.restoreVersion)
        historyLayout.addWidget(self.historyList)
        
        # Version action buttons
        buttonLayout = QHBoxLayout()
        
        viewButton = QPushButton("View Version")
        viewButton.clicked.connect(self.viewSelectedVersion)
        buttonLayout.addWidget(viewButton)
        
        restoreButton = QPushButton("Restore Version")
        restoreButton.clicked.connect(self.restoreSelectedVersion)
        buttonLayout.addWidget(restoreButton)
        
        # Refresh button
        refreshButton = QPushButton("Refresh History")
        refreshButton.clicked.connect(self.refreshHistory)
        buttonLayout.addWidget(refreshButton)
        
        historyLayout.addLayout(buttonLayout)
        
        mainWidget.layout().addWidget(historyGroupBox)
        
        # Load history on startup
        self.refreshHistory()
    
    def canvasChanged(self, canvas):
        pass
    
    def getVersionsDir(self):
        """Get the directory where versions are stored"""
        doc = Krita.instance().activeDocument()
        if doc is None:
            return None
        
        # Get the document path
        docPath = doc.fileName()
        if not docPath:
            return None
        
        # Create versions directory next to the document
        docDir = os.path.dirname(docPath)
        docName = os.path.splitext(os.path.basename(docPath))[0]
        versionsDir = os.path.join(docDir, f"{docName}_artgit_versions")
        
        # Create directory if it doesn't exist
        os.makedirs(versionsDir, exist_ok=True)
        
        return versionsDir
    
    def getVersionsJsonPath(self):
        """Get the path to the versions.json file"""
        versionsDir = self.getVersionsDir()
        if versionsDir is None:
            return None
        return os.path.join(versionsDir, "versions.json")
    
    def loadVersionsData(self):
        """Load versions data from JSON file"""
        jsonPath = self.getVersionsJsonPath()
        if jsonPath is None or not os.path.exists(jsonPath):
            return []
        
        try:
            with open(jsonPath, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def saveVersionsData(self, data):
        """Save versions data to JSON file"""
        jsonPath = self.getVersionsJsonPath()
        if jsonPath is None:
            return False
        
        try:
            with open(jsonPath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except:
            return False
    
    def commitCurrentVersion(self):
        """Commit the current version of the document"""
        doc = Krita.instance().activeDocument()
        if doc is None:
            QMessageBox.warning(self, "Error", "No active document to commit.")
            return
        
        if not doc.fileName():
            QMessageBox.warning(self, "Error", "Please save the document first before committing.")
            return
        
        commitMessage = self.commitMessageEdit.text().strip()
        if not commitMessage:
            QMessageBox.warning(self, "Error", "Please enter a commit message.")
            return
        
        versionsDir = self.getVersionsDir()
        if versionsDir is None:
            QMessageBox.warning(self, "Error", "Could not create versions directory.")
            return
        
        # Generate version info
        timestamp = datetime.now()
        timestampStr = timestamp.strftime("%Y%m%d_%H%M%S")
        versionId = f"v_{timestampStr}"
        
        # Save the current document to versions directory
        docPath = doc.fileName()
        docName = os.path.splitext(os.path.basename(docPath))[0]
        docExt = os.path.splitext(os.path.basename(docPath))[1]
        versionFileName = f"{versionId}_{docName}{docExt}"
        versionPath = os.path.join(versionsDir, versionFileName)
        
        try:
            # Save current document
            doc.save()
            
            # Copy to versions directory
            shutil.copy2(docPath, versionPath)
            
            # Update versions data
            versionsData = self.loadVersionsData()
            versionInfo = {
                "id": versionId,
                "message": commitMessage,
                "timestamp": timestamp.isoformat(),
                "filename": versionFileName,
                "display_time": timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
            versionsData.append(versionInfo)
            
            # Save versions data
            self.saveVersionsData(versionsData)
            
            # Clear commit message and refresh history
            self.commitMessageEdit.clear()
            self.refreshHistory()
            
            QMessageBox.information(self, "Success", f"Version committed successfully!\nVersion ID: {versionId}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to commit version: {str(e)}")
    
    def refreshHistory(self):
        """Refresh the version history list"""
        self.historyList.clear()
        
        versionsData = self.loadVersionsData()
        if not versionsData:
            item = QListWidgetItem("No versions found. Create your first commit!")
            item.setData(Qt.UserRole, None)
            self.historyList.addItem(item)
            return
        
        # Sort by timestamp (newest first)
        versionsData.sort(key=lambda x: x["timestamp"], reverse=True)
        
        for version in versionsData:
            displayText = f"{version['display_time']} - {version['message']}"
            item = QListWidgetItem(displayText)
            item.setData(Qt.UserRole, version)
            self.historyList.addItem(item)
    
    def openVersion(self, item):
        """Restore the current document to a specific version when double-clicked"""
        self.restoreVersion(item)
    
    def restoreVersion(self, item):
        """Restore the current document to a specific version when double-clicked"""
        versionData = item.data(Qt.UserRole)
        if versionData is None:
            return
        
        currentDoc = Krita.instance().activeDocument()
        if currentDoc is None:
            QMessageBox.warning(self, "Error", "No active document to restore.")
            return
        
        if not currentDoc.fileName():
            QMessageBox.warning(self, "Error", "Please save the current document first.")
            return
        
        versionsDir = self.getVersionsDir()
        if versionsDir is None:
            QMessageBox.warning(self, "Error", "Could not access versions directory.")
            return
        
        versionPath = os.path.join(versionsDir, versionData["filename"])
        if not os.path.exists(versionPath):
            QMessageBox.warning(self, "Error", f"Version file not found: {versionData['filename']}")
            return
        
        # Ask user if they want to restore to this version
        reply = QMessageBox.question(self, "Restore Version", 
                                   f"Do you want to restore the current document to:\n{versionData['message']}\n({versionData['display_time']})\n\nThis will replace the current state with the selected version.",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # Save current state before restoring (optional safety backup)
                currentDoc.save()
                
                # Get current document path
                currentDocPath = currentDoc.fileName()
                
                # Close the current document
                currentDoc.close()
                
                # Copy the version file to replace the current document
                shutil.copy2(versionPath, currentDocPath)
                
                # Reopen the document (now restored to the previous version)
                restoredDoc = Krita.instance().openDocument(currentDocPath)
                
                if restoredDoc:
                    QMessageBox.information(self, "Success", 
                                          f"Document restored to version:\n{versionData['message']}\n({versionData['display_time']})")
                else:
                    QMessageBox.critical(self, "Error", "Failed to reopen the restored document.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to restore version: {str(e)}")
    
    def viewSelectedVersion(self):
        """View the selected version in a new window without affecting current document"""
        item = self.historyList.currentItem()
        if item is None:
            QMessageBox.warning(self, "Warning", "Please select a version to view.")
            return
        
        versionData = item.data(Qt.UserRole)
        if versionData is None:
            return
        
        versionsDir = self.getVersionsDir()
        if versionsDir is None:
            QMessageBox.warning(self, "Error", "Could not access versions directory.")
            return
        
        versionPath = os.path.join(versionsDir, versionData["filename"])
        if not os.path.exists(versionPath):
            QMessageBox.warning(self, "Error", f"Version file not found: {versionData['filename']}")
            return
        
        try:
            # Open the version file in a new window
            Krita.instance().openDocument(versionPath)
            QMessageBox.information(self, "Version Opened", 
                                  f"Opened version for viewing:\n{versionData['message']}\n({versionData['display_time']})\n\nThis is a separate copy - changes won't affect your main document.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open version: {str(e)}")
    
    def restoreSelectedVersion(self):
        """Restore the selected version to the current document"""
        item = self.historyList.currentItem()
        if item is None:
            QMessageBox.warning(self, "Warning", "Please select a version to restore.")
            return
        
        self.restoreVersion(item)

class ArtGit(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        # Create commit action
        commitAction = window.createAction("artgit_commit", "Commit Version", "tools/scripts")
        commitAction.triggered.connect(self.showCommitDialog)
    
    def showCommitDialog(self):
        """Show a simple commit dialog"""
        doc = Krita.instance().activeDocument()
        if doc is None:
            QMessageBox.warning(None, "Error", "No active document to commit.")
            return
        
        if not doc.fileName():
            QMessageBox.warning(None, "Error", "Please save the document first before committing.")
            return
        
        # Simple input dialog for commit message
        message, ok = QInputDialog.getText(None, "Commit Version", "Enter commit message:")
        if ok and message.strip():
            # Find the docker and use its commit function
            for docker in Krita.instance().dockers():
                if isinstance(docker, ArtGitDocker):
                    docker.commitMessageEdit.setText(message.strip())
                    docker.commitCurrentVersion()
                    break

# Add the extension and docker to Krita
Krita.instance().addExtension(ArtGit(Krita.instance()))
Krita.instance().addDockWidgetFactory(DockWidgetFactory("artgitDocker", DockWidgetFactoryBase.DockRight, ArtGitDocker))