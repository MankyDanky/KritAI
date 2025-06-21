from krita import *

class ArtGit(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass  # Runs when Krita starts

    def createActions(self, window):
        action = window.createAction("artgit_action", "Run ArtGit", "tools/scripts")
        action.triggered.connect(self.run)

    def run(self):
        print("ArtGit plugin is running!")

Krita.instance().addExtension(ArtGit(Krita.instance()))
