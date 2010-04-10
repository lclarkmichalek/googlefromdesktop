#!/usr/bin/env python
# -*- coding: utf-8 -*-
#    Copyright 2010 Laurie Clark-Michalek (Blue Peppers) <bluepeppers@archlinux.us>
#
#    This program (Battleships) is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import urllib2, simplejson, sys, shutil
from tempfile import NamedTemporaryFile
from time import sleep

Key = 'ABQIAAAAfTk2IdQA0Ey_Oe0O0lKpfBTRERdeAiwZ9EeJWta3L_JZVS0bOBSZbJCtMvSfc8Q6xD2JDIz-2ooVzA'

def log(*args):
    for arg in args:
        sys.stderr.write(str(arg))
    sys.stderr.write('\n')

IconPaths = ':/trolltech/styles/commonstyle/images/'
IconNames = map(str, QDir(":/trolltech/styles/commonstyle/images/").entryList())
IconNames = [Name.replace('-16.png', '').replace('-32', '').replace('-128', '')
             .replace('.png', '') for Name in IconNames]

def Icon(Name):
    if Name in IconNames:
        return QIcon(IconPaths + Name + '-32.png')
    
    Con = []
    for IconName in IconNames:
        if Name in IconName:
            Con.append(IconName)
    
    if len(Con) > 0:
        return QIcon(IconPaths + Con[0] + '-32.png')
    
    return QIcon()
     

class Window(QMainWindow):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        
        self._Image = QPixmap()
        self.Image = QLabel()
        self.Image.setAlignment(Qt.AlignCenter)
        
        self.NextButton = QPushButton()
        self.NextButton.setIcon(Icon('right'))
        self.PrevButton = QPushButton()
        self.PrevButton.setIcon(Icon('left'))
        
        self.Name = QLabel()
        self.Save = QPushButton()
        self.Save.setIcon(Icon('save'))
        BottomInfoLayout = QVBoxLayout()
        BottomInfoLayout.addWidget(self.Name)
        BottomInfoLayout.addWidget(self.Save)
        
        BottomLayout = QHBoxLayout()
        BottomLayout.addWidget(self.PrevButton)
        BottomLayout.addLayout(BottomInfoLayout)
        BottomLayout.addWidget(self.NextButton)
        
        
        self.Term = QLineEdit()
        self.ResultWidget = QListWidget()
        SideLayout = QVBoxLayout()
        SideLayout.addWidget(self.Term)
        SideLayout.addWidget(self.ResultWidget)
        
        FullLayout = QGridLayout()
        FullLayout.addWidget(self.Image, 0, 0)
        FullLayout.setColumnStretch(0, 5)
        FullLayout.setRowStretch(0, 5)
        FullLayout.addLayout(SideLayout, 0, 1)
        FullLayout.addLayout(BottomLayout, 1, 0, 1, 2)
        
        CentralWidget = QWidget()
        CentralWidget.setLayout(FullLayout)
        self.setCentralWidget(CentralWidget)
        
        self.connect(self.Term, SIGNAL('editingFinished ()'),
                     self.termeditSearch)
        
        self.connect(self.Save, SIGNAL('pressed()'),
                     self.SaveCurrent)
        
        self.connect(self.NextButton, SIGNAL('pressed()'),
                     self.Next)
        
        self.connect(self.PrevButton, SIGNAL('pressed()'),
                     self.Prev)
        
        menuBar = self.menuBar()
        fileBar = menuBar.addMenu('&File')
        
        fileBar.addAction(self.createAction('&Save', self.SaveCurrent, 'Ctrl-S',
                        'save', 'This saves the current image'
                            ' to your hard drive'))
        
        fileBar.addAction(self.createAction('&Next', self.Next, 'Space',
                        'right', 'This displays the next picture from the results'))
        fileBar.addAction(self.createAction('&Prev', self.Prev, 'Ctrl-Z',
                        'left', 'This displays the previous picture from the results'))
        fileBar.addAction(self.createAction('Sear&ch', self.actionSearch, 'Ctrl-C',
                        tip='This does a new search'))
        fileBar.addAction(self.createAction('C&lose', self.close, 'Ctrl-Q', 'close',
                        'Exits the program'))
        
        self.Results = {}
        self._CurrentTerm = ''
        self._Index = 0
        
        self.DldThread = DownloadThread(self, [])
        
        Settings = QSettings()
        
        Size = Settings.value("Window/Size", QVariant(QSize(600,500))).toSize()
        self.resize(Size)
        
        Position = Settings.value("Window/Position", QVariant(QPoint(0,0))).toPoint()
        self.move(Position)
        
    
    def close(self):
        self.DldThread.interupt()
        app.quit()
        sys.exit()
    
    def termeditSearch(self):
        Term = self.Term.text()
        
        self.Search(Term)
    
    def actionSearch(self):
        dialog = Search()
        
        if dialog.exec_():
            self.Search(dialog.Term.text())
    
    def SaveCurrent(self):
        File = QFileDialog.getSaveFileName(self, "Save File", filter='Images (*.png *.xpm *.jpg)')
        
        shutil.copyfile(self.Results[self._Index]['File'], File)
    
    def Next(self):
        if self._Index + 1 < len(self.Results):
            self._Index += 1
        else:
            self._Index = 0
        self.ResultWidget.setCurrentRow(self._Index)
        self.DldThread.Next()
    
    def Prev(self):
        if self._Index - 1 >= 0:
            self._Index -= 1
        else:
            self._Index = len(self.Results) - 1
        self.ResultWidget.setCurrentRow(self._Index)
        self.DldThread.Prev()
    
    def createAction(self, text, slot=None, shortcut=None, icon=None,
                     tip=None, checkable=False, signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(Icon(icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action
    
    def Search(self, Term):
        Term = Term.replace(' ','%20')
        if Term == '' or Term == self._CurrentTerm:
            return
        
        self._CurrentTerm = Term
        self._Index = 0
        
        if self.DldThread.isRunning():
            self.DldThread.interupt()
        
         
        
        self.statusBar().showMessage('Polling Google')
        
        url = ('http://ajax.googleapis.com/ajax/services/search/images'
       '?v=1.0&q=%s&key=%s&userip=127.0.0.1&rsz=%s' % (Term,
                                                       Key, 'large'))
        
        request = urllib2.Request(url, None, {'Referer': 'http://www.google.com'})
        response = urllib2.urlopen(request)
        results = simplejson.load(response)
        
        for index, result in enumerate(results['responseData']['results']):
            self.Results[index] = result
        
        self.DldThread = DownloadThread(self, [result['unescapedUrl'] for result in self.Results.values()])
        self.DldThread.start()
        
        self.ResultWidget.clear()
        self.ResultWidgetList = []
        for result in self.Results.values():
            self.ResultWidgetList.append(QListWidgetItem(result['titleNoFormatting'], self.ResultWidget))
        self.ResultWidget.setCurrentRow(0)
        
    
    def DownloadFinished(self):
        if self._Index not in self.DldThread.Files.keys() or self._Index not in self.Results.keys():
            return 
        self.Results[self._Index]['File'] = self.DldThread.Files[self._Index]
        self.statusBar().showMessage('Image Downloaded', 2000)
        self.SyncImage()
    
    def SyncImage(self):
        if self._Image.isNull():            
            self._Image = QPixmap(self.Results[self._Index]['File']).scaled(
                                self.ImageSize.width(), self.ImageSize.height())
            self.Image.setPixmap(self._Image)
        else:
            self._Image = QPixmap(self.Results[self._Index]['File'])
            PicSize = self._Image.size()
            PicSize.scale(self.ImageSize, Qt.KeepAspectRatio)
            self._Image = self._Image.scaled(PicSize.width(), PicSize.height())
            self.Image.setPixmap(self._Image)
        
        self.Name.setText(self.Results[self._Index]['titleNoFormatting'])
    
    def DownloadStarted(self):
        self.statusBar().showMessage('Downloading Image')
    
    def resizeEvent(self, Event):
        self.ImageSize = self.Image.size()
        return
        self.Image.setPixmap(QPixmap())
    
    def closeEvent(self, Event):
        Settings = QSettings()
        Settings.setValue("Window/Size", QVariant(self.size()))
        Settings.setValue("Window/Positon", QVariant(self.pos()))
        
        
        

class DownloadThread(QThread):
    def __init__(self, parent, Uris):
        QThread.__init__(self, parent)
        self.Uris = Uris
        self.Files = {}
        
        self._Interupted = False
        
        self.connect(self, SIGNAL('finished()'),
                     self.parent().DownloadFinished)
        self.connect(self, SIGNAL('started()'),
                     self.parent().DownloadStarted)
    
    def interupt(self):
        self._Interupted = True
    
    def start(self):
        QThread.start(self)
        self._Interupted = False
    
    def restart(self):
        self.interupt()
        sleep(0.05)
        self.start()
    
    def Next(self):
        if self.parent()._Index in self.Files.keys():
            return
        self.restart()
    
    def Prev(self):
        if self.parent()._Index in self.Files.keys():
            return
        self.restart()
    
    def Move(self, Index):
        if self.parent()._Index in self.Files.keys():
            return
        self.parent()._Index = Index
        self.restart()
    
    def run(self):
        if self.parent()._Index in self.Files.keys():
            return
        block_size = 512
        i = 0
        counter = 0
        temp = urllib2.urlopen(self.Uris[self.parent()._Index])
        headers = temp.info()
        size = int(headers['Content-Length'])
        File = NamedTemporaryFile('w',delete=False)
        
        while i < size:
            if not self._Interupted:
                File.write(temp.read(block_size))
                i += block_size
                counter += 1
            else:
                log('QThread: Interupted')
                File.close()
                return
        
        File.close()
        
        self.Files[self.parent()._Index] = File.name

class Search(QDialog):
    def __init__(self, parent=None):
        super(Search, self).__init__(parent)
        
        Label = QLabel('&Search Term')
        self.Term = QLineEdit()
        Label.setBuddy(self.Term)
        
        ButtonBox = QDialogButtonBox(QDialogButtonBox.Ok| QDialogButtonBox.Cancel)
        
        Layout = QGridLayout()
        Layout.addWidget(Label, 0, 0)
        Layout.addWidget(self.Term, 0, 1)
        Layout.addWidget(ButtonBox, 1, 0, 1, 2)
        
        self.connect(ButtonBox, SIGNAL('accepted ()'),
                     self.accept)
        self.connect(ButtonBox, SIGNAL('rejected ()'),
                     self.reject)
        
        self.setLayout(Layout)





app = QApplication(sys.argv)
Main = Window()
Main.show()
app.exec_()