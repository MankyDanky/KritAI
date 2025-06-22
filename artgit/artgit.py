from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QImage, QPainter, QBrush, QIcon
import os
import json
import shutil
import uuid
from datetime import datetime
from .graph_view import CommitGraphView, GraphDialog

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
        
        """
        self.historyList = QListWidget()
        self.historyList.itemDoubleClicked.connect(self.restoreVersion)
        historyLayout.addWidget(self.historyList)
        """

        # remove self.historyList definition …

        self.historyTree = QTreeWidget()
        self.historyTree.setHeaderLabels(["Commit", "Time", "Msg"])
        self.historyTree.itemDoubleClicked.connect(self.restoreTreeVersion)
        historyLayout.addWidget(self.historyTree)

        # Version action buttons
        buttonLayout = QHBoxLayout()
        
        restoreButton = QPushButton("Restore Version")
        restoreButton.clicked.connect(self.restoreSelectedVersion)
        buttonLayout.addWidget(restoreButton)

        parentBtn = QPushButton("Go to Parent")
        parentBtn.clicked.connect(self.gotoParent)
        buttonLayout.addWidget(parentBtn)

        
        # Refresh button
        refreshButton = QPushButton("Refresh History")
        refreshButton.clicked.connect(self.refreshHistory)
        buttonLayout.addWidget(refreshButton)

        graphBtn = QPushButton("Show Graph")
        graphBtn.clicked.connect(self.showGraphWindow)
        buttonLayout.addWidget(graphBtn)
        
        historyLayout.addLayout(buttonLayout)
        
        mainWidget.layout().addWidget(historyGroupBox)
        
        self.currentHead = self.loadVersionsData()["current_head"]
        
        # Load history on startup
        self.refreshHistory()
    
    def gotoParent(self):
        item = self.historyTree.currentItem()
        if not item:                    # nothing selected
            return
        cur = item.data(0, Qt.UserRole)
        parent_id = cur.get("parent")
        if not parent_id:
            return

        for i in range(self.historyTree.topLevelItemCount()):
            leaf = self.historyTree.topLevelItem(i)
            if leaf.data(0, Qt.UserRole)["id"] == parent_id:
                self.historyTree.setCurrentItem(leaf)
                self.historyTree.scrollToItem(leaf)
                break

    # helper: drop malformed records that break refreshHistory()
    def _sanitizeCommits(self, data):
        """Drop malformed or duplicate commit entries."""
        seen = set()
        bad  = []
        for k, v in data["commits"].items():
            if not isinstance(v, dict) or "timestamp" not in v or k in seen:
                bad.append(k)
            seen.add(k)
        for k in bad:
            del data["commits"][k]
        return data

    def canvasChanged(self, canvas):
        pass

    def restoreTreeVersion(self, item, _col):
        version = item.data(0, Qt.UserRole)
        if version:
            self.restoreVersionFromDict(version)
    
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
        path = self.getVersionsJsonPath()
        if not path or not os.path.exists(path):
            return {"commits": {}, "current_head": None}
        try:
            data = json.load(open(path, "r"))
        except Exception:
            return {"commits": {}, "current_head": None}

        # legacy list → dict migration  (keep if you still have old files)
        if isinstance(data.get("commits"), list):
            data = {
                "commits": {c["id"]: c for c in data["commits"]},
                "current_head": None
            }
        elif isinstance(next(iter(data["commits"].values()), {}), list):
            flat = {}
            for lst in data["commits"].values():
                for c in lst:
                    flat[c["id"]] = c
            data = {"commits": flat, "current_head": data.get("current_head")}

        return self._sanitizeCommits(data)   # ← now it’s defined


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

            parent_id   = data.get("current_head")
            commit_id =  str(uuid.uuid4())

            versionInfo = {
                "id":        commit_id,
                "parent":    parent_id,
                "message":   commitMessage,
                "timestamp": timestamp.isoformat(),
                "display_time": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "filename":  versionFileName,
                "preview":   previewFileName
            }
            

            data["commits"][commit_id]  = versionInfo
            data["current_head"]        = commit_id
            self.currentHead            = commit_id

            # Save versions data
            self.saveVersionsData(data)
            
            # Clear commit message and refresh history
            self.commitMessageEdit.clear()
            self.refreshHistory()
            
            QMessageBox.information(
                self, "Success",
                f"Committed {commit_id[:8]}…")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to commit version: {str(e)}")
    
    def refreshHistory(self):
        self.historyTree.setUpdatesEnabled(False)
        self.historyTree.clear()

        data = self.loadVersionsData()
        commits = sorted(data["commits"].values(),
                        key=lambda c: c["timestamp"], reverse=True)

        for c in commits:
            leaf = QTreeWidgetItem([
                f"{c['id'][:8]}…",
                c["display_time"],
                c["message"]
            ])
            leaf.setData(0, Qt.UserRole, c)
            iconPath = os.path.join(self.getVersionsDir(), c.get("preview", ""))
            if os.path.exists(iconPath):
                leaf.setIcon(0, QIcon(iconPath))
            self.historyTree.addTopLevelItem(leaf)

        self.historyTree.setUpdatesEnabled(True)

    
    def restoreVersionFromDict(self, versionData):
        """Restore the current document to a specific version when double-clicked"""
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

                data = self.loadVersionsData()
                data["current_head"] = versionData["id"]
                self.currentHead     = versionData["id"]
                self.saveVersionsData(data)

                
                QMessageBox.information(self, "Success", 
                                      f"Document restored to version:\n{versionData['message']}\n({versionData['display_time']})")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to restore version: {str(e)}")

    def restoreSelectedVersion(self):
        sel = self.historyTree.currentItem()
        if not sel:
            QMessageBox.warning(self, "Warning", "Select a commit first.")
            return

        self.restoreTreeVersion(sel, 0)
    
    def createPreviewThumbnail(self, doc, previewPath):
        """Create a thumbnail preview without showing dialog"""
        try:
            # Use Krita's built-in thumbnail method - no dialog
            thumbnail = doc.thumbnail(256, 256)
            thumbnail.save(previewPath, "PNG")
        except Exception as e:
            # If thumbnail fails, skip preview
            pass

    def showGraphWindow(self):
        data    = self.loadVersionsData()
        versions_dir = self.getVersionsDir() 
        commits = sorted(data["commits"].values(),
                        key=lambda c: c["timestamp"], reverse=True)
        commits_by_id = {c["id"]: c for c in commits}

        for c in commits:
            c["preview_abs"] = os.path.join(versions_dir, c["preview"])

        dlg = GraphDialog(commits, self)                # ← create FIRST
        graph = dlg.findChild(CommitGraphView)
        graph.commitClicked.connect(
            lambda cid: self.restoreVersionFromDict(commits_by_id[cid])
        )

        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.show()


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