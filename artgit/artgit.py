from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QImage, QPainter, QBrush, QIcon
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

        # Load QSS stylesheet from file
        qss_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "style.qss")
        with open (qss_path, "r") as file:
            mainWidget.setStyleSheet(file.read())
        
        # Title label
        titleLabel = QLabel("Version History")
        titleLabel.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        mainWidget.layout().addWidget(titleLabel)
        
        # Branch management section
        branchGroupBox = QGroupBox("Branch Management")
        branchLayout = QVBoxLayout()
        branchGroupBox.setLayout(branchLayout)
        
        # Current branch dropdown
        branchSelectionLayout = QHBoxLayout()
        branchSelectionLayout.addWidget(QLabel("Current Branch:"))
        self.branchComboBox = QComboBox()
        self.branchComboBox.currentTextChanged.connect(self.onBranchChanged)
        branchSelectionLayout.addWidget(self.branchComboBox)
        branchLayout.addLayout(branchSelectionLayout)
        
        # New branch creation
        newBranchLayout = QHBoxLayout()
        self.newBranchEdit = QLineEdit()
        self.newBranchEdit.setPlaceholderText("Enter new branch name...")
        newBranchLayout.addWidget(self.newBranchEdit)
        
        createBranchButton = QPushButton("Create Branch")
        createBranchButton.clicked.connect(self.createNewBranch)
        newBranchLayout.addWidget(createBranchButton)
        branchLayout.addLayout(newBranchLayout)
        
        mainWidget.layout().addWidget(branchGroupBox)
        
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
        
        restoreButton = QPushButton("Restore Version")
        restoreButton.clicked.connect(self.restoreSelectedVersion)
        buttonLayout.addWidget(restoreButton)
        
        # Refresh button
        refreshButton = QPushButton("Refresh History")
        refreshButton.clicked.connect(self.refreshHistory)
        buttonLayout.addWidget(refreshButton)
        
        historyLayout.addLayout(buttonLayout)
        
        mainWidget.layout().addWidget(historyGroupBox)
        
        # Initialize branch system
        self.currentBranch = "main"  # Default branch
        self.loadBranches()
        
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
        """Load versions data from JSON file with branch support"""
        jsonPath = self.getVersionsJsonPath()
        if jsonPath is None or not os.path.exists(jsonPath):
            # Return default structure with main branch
            return {
                "branches": ["main"],
                "current_branch": "main",
                "commits": {
                    "main": []
                }
            }
        
        try:
            with open(jsonPath, 'r') as f:
                data = json.load(f)
                
            # Convert old format to new format if needed
            if isinstance(data, list):
                # Old format: just a list of commits
                return {
                    "branches": ["main"],
                    "current_branch": "main", 
                    "commits": {
                        "main": data
                    }
                }
            
            # Ensure required keys exist
            if "branches" not in data:
                data["branches"] = ["main"]
            if "current_branch" not in data:
                data["current_branch"] = "main"
            if "commits" not in data:
                data["commits"] = {"main": []}
            
            return data
        except:
            return {
                "branches": ["main"],
                "current_branch": "main",
                "commits": {
                    "main": []
                }
            }
    
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

            # Create preview image without dialog
            previewFileName = f"{versionId}_{docName}.png"
            previewPath = os.path.join(versionsDir, previewFileName)
            
            # Get document thumbnail directly (no dialog)
            self.createPreviewThumbnail(doc, previewPath)
            
            # Copy to versions directory
            shutil.copy2(docPath, versionPath)
            
            # Update versions data
            data = self.loadVersionsData()
            versionInfo = {
                "id": versionId,
                "message": commitMessage,
                "timestamp": timestamp.isoformat(),
                "filename": versionFileName,
                "display_time": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "preview": previewFileName,
                "branch": self.currentBranch
            }
            
            # Add commit to current branch
            if self.currentBranch not in data["commits"]:
                data["commits"][self.currentBranch] = []
            data["commits"][self.currentBranch].append(versionInfo)
            
            # Save versions data
            self.saveVersionsData(data)
            
            # Clear commit message and refresh history
            self.commitMessageEdit.clear()
            self.refreshHistory()
            
            QMessageBox.information(self, "Success", f"Version committed successfully!\nVersion ID: {versionId}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to commit version: {str(e)}")
    
    def refreshHistory(self):
        """Refresh the version history list for current branch"""
        self.historyList.clear()
        
        data = self.loadVersionsData()
        branchCommits = data["commits"].get(self.currentBranch, [])
        
        if not branchCommits:
            item = QListWidgetItem(f"No commits in '{self.currentBranch}' branch. Create your first commit!")
            item.setData(Qt.UserRole, None)
            self.historyList.addItem(item)
            return
        
        # Sort by timestamp (newest first)
        branchCommits.sort(key=lambda x: x["timestamp"], reverse=True)
        
        for version in branchCommits:
            displayText = f"{version['display_time']} - {version['message']}"
            item = QListWidgetItem(displayText)
            item.setData(Qt.UserRole, version)
            # Loads preview icon
            previewPath = os.path.join(self.getVersionsDir(), version.get("preview", ""))
            if os.path.exists(previewPath): 
                icon = QIcon(previewPath)
                item.setIcon(icon)
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
                
                # Load the version document temporarily
                versionDoc = Krita.instance().openDocument(versionPath)
                if not versionDoc:
                    QMessageBox.critical(self, "Error", "Failed to load the version file.")
                    return
                
                # Get all the nodes (layers) from the version document
                versionRootNode = versionDoc.rootNode()
                
                # Clear all nodes from current document
                currentRootNode = currentDoc.rootNode()
                for child in currentRootNode.childNodes():
                    child.remove()
                
                # Copy all nodes from version to current document
                for child in versionRootNode.childNodes():
                    # Clone the node and add it to current document
                    clonedNode = child.clone()
                    currentRootNode.addChildNode(clonedNode, None)
                
                currentDoc.setResolution(int(versionDoc.xRes()))
                
                currentDoc.resizeImage(0, 0, versionDoc.width(), versionDoc.height())
                    
               
                
                currentDoc.setColorSpace(versionDoc.colorModel(), versionDoc.colorDepth(), versionDoc.colorProfile())
                
                # Close the temporary version document
                versionDoc.close()
                
                # Refresh the current document view
                currentDoc.refreshProjection()
                
                # Save the restored document
                currentDoc.save()
                
                QMessageBox.information(self, "Success", 
                                      f"Document restored to version:\n{versionData['message']}\n({versionData['display_time']})")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to restore version: {str(e)}")
    
    def restoreSelectedVersion(self):
        """Restore the selected version to the current document"""
        item = self.historyList.currentItem()
        if item is None:
            QMessageBox.warning(self, "Warning", "Please select a version to restore.")
            return
        
        self.restoreVersion(item)
    
    def loadBranches(self):
        """Load available branches and set current branch"""
        data = self.loadVersionsData()
        self.currentBranch = data.get("current_branch", "main")
        
        # Update branch combo box
        self.branchComboBox.clear()
        self.branchComboBox.addItems(data["branches"])
        
        # Set current branch in combo box
        index = self.branchComboBox.findText(self.currentBranch)
        if index >= 0:
            self.branchComboBox.setCurrentIndex(index)
    
    def onBranchChanged(self, branchName):
        """Handle branch selection change"""
        if branchName and branchName != self.currentBranch:
            self.currentBranch = branchName
            
            # Update current branch in data
            data = self.loadVersionsData()
            data["current_branch"] = branchName
            self.saveVersionsData(data)
            
            # Refresh history for new branch
            self.refreshHistory()
    
    def createNewBranch(self):
        """Create a new branch"""
        branchName = self.newBranchEdit.text().strip()
        if not branchName:
            QMessageBox.warning(self, "Error", "Please enter a branch name.")
            return
        
        # Validate branch name (simple validation)
        if not branchName.replace("_", "").replace("-", "").isalnum():
            QMessageBox.warning(self, "Error", "Branch name can only contain letters, numbers, underscores, and hyphens.")
            return
        
        data = self.loadVersionsData()
        
        # Check if branch already exists
        if branchName in data["branches"]:
            QMessageBox.warning(self, "Error", f"Branch '{branchName}' already exists.")
            return
        
        # Create new branch by copying current branch's commits
        currentBranchCommits = data["commits"].get(self.currentBranch, [])
        
        # Add new branch
        data["branches"].append(branchName)
        data["commits"][branchName] = currentBranchCommits.copy()  # Copy commits from current branch
        data["current_branch"] = branchName
        
        # Save data
        self.saveVersionsData(data)
        
        # Update UI
        self.currentBranch = branchName
        self.loadBranches()
        self.refreshHistory()
        
        # Clear input field
        self.newBranchEdit.clear()
        
        QMessageBox.information(self, "Success", f"Branch '{branchName}' created successfully!")

    def createPreviewThumbnail(self, doc, previewPath):
        """Create a thumbnail preview without showing dialog"""
        try:
            # Use Krita's built-in thumbnail method - no dialog
            thumbnail = doc.thumbnail(256, 256)
            thumbnail.save(previewPath, "PNG")
        except Exception as e:
            # If thumbnail fails, skip preview
            pass

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

# Add the extension and dockers to Krita
Krita.instance().addExtension(ArtGit(Krita.instance()))
Krita.instance().addDockWidgetFactory(DockWidgetFactory("artgitDocker", DockWidgetFactoryBase.DockRight, ArtGitDocker))



# Add the extension and dockers to Krita
Krita.instance().addExtension(ArtGit(Krita.instance()))
Krita.instance().addDockWidgetFactory(DockWidgetFactory("artgitDocker", DockWidgetFactoryBase.DockRight, ArtGitDocker))