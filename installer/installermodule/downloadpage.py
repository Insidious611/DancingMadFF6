# Download Page
import shutil
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtMultimedia import QSound
import os, errno
from installermodule.downloader import Downloader
from installermodule import rom
from installermodule.selections import *
from installermodule import song 
from decimal import Decimal
from queue import Queue
import ips
import sys
import glob
import socket
import urllib.request
import urllib.error

mysonglist = song.parseSongXML("songs.xml")

# Should we use the /new directory in the mirrors. Use when testing new song selections, turn off on release.
NEW_PATH = False

# Should we grab mirrors.dat from github to make sure it's up to date?
REMOTE_MIRRORS = True

def _doMirrors(pcmlist, mirrors = None):
    if mirrors == None:
        mirrors = []
    if mirrors == []:
        mirrorfn = "mirrors-new.dat"
        try: 
            with open("mirrors-new.dat", 'wb') as f:
                mrcurl = pycurl.Curl()
                mrcurl.setopt(md5curl.URL, "https://raw.githubusercontent.com/Insidious611/DancingMadFF6/master/installer/mirrors.dat")
                mrcurl.setopt(md5curl.FAILONERROR, True)
                mrcurl.setopt(md5curl.CAINFO, certifi.where())
                mrcurl.setopt(md5curl.TIMEOUT, 5)
                mrcurl.setopt(md5curl.WRITEDATA, f)
                mrcurl.setopt(md5curl.FAILONERROR, True)
                mrcurl.perform()
        except as e:
            print(e)
            mirrorfn = "mirrors.dat"
        try:
            with open(mirrorfn) as f:
                mirrors = f.readlines()
                mirrors = [x.strip() for x in mirrors]
        except IOError:
            return None
        mirrorlist = []
        for m in mirrors:
            errorstr = ""
            try: # Check to make sure mirror is reachable before adding it to our list.
                retcode = urllib.request.urlopen(m,timeout=4).getcode() # 4 seconds may be too fast, but I'm trying to avoid needing to thread this call.
            except urllib.error.URLError as e:
                retcode = -1
                errorstr = e.reason
            if retcode == 200:
                domain = m.split("/")[2]
                try:
                    socket.gethostbyname(domain)
                except:
                    print("Unable to find host " + domain)
                    pass
                else:
                    print("Found host " + domain)
                    mirrorlist.append([m + i for i in pcmlist])
            else:
                if retcode != -1:
                    print("Skipping mirror", m, ", HTTP ERROR ", retcode)
                else:
                    print("Skipping mirror", m, ",", errorstr)
    else:
        mirrorlist = []
        for m in mirrors:
            mirrorlist.append([m + i for i in pcmlist])
    args = tuple(mirrorlist)
    return list(zip(*args))
    
            
def _doSongMap(source, tracknum):
        if NEW_PATH == False:
            sourcestr = ""
        else:
            sourcestr = "new/"
        if mysonglist.sources[source] != "spc":
            if mysonglist.sources[source].startswith("x"):
                sourcestr = sourcestr + "opera/" + mysonglist.sources[source].upper()[1:]
            else:
                sourcestr = sourcestr + mysonglist.sources[source].upper()
        else:
            return ""
        retstr = sourcestr + "/ff3-" + str(tracknum) + ".pcm"
        return retstr


def mapSongs(songSources):
        retlist = []
        for idx,source in enumerate(songSources):
            for pcm in mysonglist.songs[idx].pcms:
                file = _doSongMap(source, pcm)
                if file != "":
                    retlist.append(file)
        return retlist


class downloadPage(QtWidgets.QWizardPage):
        compChgSgnl = pyqtSignal()
        installstate = 0
        def __init__(self):
              if not (len(sys.argv) >= 2 and sys.argv[1] == "-nosound"):
                try:
                  self.laughFile = QSound("kefkalaugh.wav")
                  self.soundOn = True
                  self.soundPlayed = False
                  print("Kefka laugh enabled")
                except:
                  self.laughFile = None
                  self.soundOn = False
                  self.soundPlayed = False
                  print("Kefka laugh disabled (exception)")
              else:
                self.laughFile = None
                self.soundOn = False
                self.soundPlayed = False
                print("Kefka laugh disabled (commandline)")
              self.installstate = 1
              self.totalDownloads = 0
              super().__init__()
              self.checktimer = QTimer(self)
              self.checktimer.timeout.connect(self.timerEvent)
              self.compChgSgnl.connect(self.completeChanged)
              self.compChgSgnl.emit()
        def custRedrawWidgets(self):
              for i in self.widgetsToRedraw:
                i.repaint()
        def updateCurrentLabel(self, newtext):
              self.currentLabel.setText(newtext)
              self.custRedrawWidgets()
        def initializePage(self):
              self.checktimer.start(100)

        def timerEvent(self):
              sys.stdout.flush() # Periodically flush log to disk.
              if self.installstate == 1:   # Initializing...
                  self.updateCurrentLabel("Initializing downloader...")
                  if self.field("customButton") == True:
                      self.songSources = self.field("songList")
                      if self.field("operaMfButton") == True:
                        self.songSources[31] = mysonglist.sources.index("xmf")
                      elif self.field("operaTbmButton") == True:
                        self.songSources[31] = mysonglist.sources.index("xtbm")
                      elif self.field("operaOstButton") == True:
                        self.songSources[31] = mysonglist.sources.index("xost")
                      elif self.field("operaGmcButton") == True:
                        self.songSources[31] = mysonglist.sources.index("xgmc")
                      elif self.field("operaDwButton") == True:
                        self.songSources[31] = mysonglist.sources.index("xdw")
                      elif self.field("operaSpcButton") == True:
                        self.songSources[31] = mysonglist.sources.index("spc")
                      else:
                        print("DEBUG: Invalid opera selection.")
                        self.songSources[31] = mysonglist.sources.index("xost")
                  elif self.field("sidselectButton") == True:
                      self.songSources = selectionToNumbers("sid")
                  elif self.field("ostButton") == True:
                      self.songSources = selectionToNumbers("ost")
                  elif self.field("fftButton") == True:
                      self.songSources = selectionToNumbers("fft")
                  elif self.field("sschafButton") == True:
                      self.songSources = selectionToNumbers("ssc")
                  elif self.field("ocrButton") == True:
                      self.songSources = selectionToNumbers("ocr")
                  elif self.field("ocraltButton") == True:
                      self.songSources = selectionToNumbers("ocr2")
                  elif self.field("ffarButton") == True:
                      self.songSources = selectionToNumbers("ffar")
                  elif self.field("crcButton") == True:
                      self.songSources = selectionToNumbers("crc")
                  else:
                      self.songSources = selectionToNumbers("ost") # Shouldn't get here, but ost as default anyway.

                  # if self.songSources[31] == 0: # OST opera is now available. Commented this bit out. 
                      # self.songSources[31] = 6
                  if self.songSources[59] == mysonglist.sources.index("ost"): # No OST versions of sound effects.
                      self.songSources[59] = mysonglist.sources.index("spc")
                  
                  templist = mapSongs(self.songSources)
                  # TODO: Make this bit for the optional addons less hard coded.
                  if self.field("twueCheck") == True:
                    templist.append("contrib/twue.ips")
                  if self.field("mplayerCheck") == True:
                    if self.field("cutsongCheck") == True:
                      templist.append("contrib/mplayer-csr-main-nh.ips")
                    else:
                      templist.append("contrib/mplayer-main-nh.ips")
                  if self.field("cutsongCheck") == True:
                    templist.append("contrib/CSR/ff3-90.pcm")
                    templist.append("contrib/CSR/ff3-91.pcm")
                    templist.append("contrib/CSR/ff3-92.pcm")
                    templist.append("contrib/CSR/ff3-93.pcm")
                    templist.append("contrib/CSR/csr.ips")
                  self.updateCurrentLabel("Checking status of mirrors, installer may appear frozen (please be patient!)...")
                  self.custRedrawWidgets()
                  comblist = _doMirrors(templist, self.validmirrors)
                  destination = self.field("destPath")
                  # Rename higanified tracks back to normal name so that they can be checked for already existing
                  for filename in glob.glob(destination + "/track-*.pcm"):
                    new_name = filename.replace("track","ff3")
                    os.rename(filename, new_name)
                  self.totalDownloads = len(comblist)
                  urlqueue = Queue(maxsize=self.totalDownloads)
                  for urlpair in comblist:
                      urlqueue.put(urlpair)  
                  self.downloader = Downloader(urlqueue, destination)
                  if self.totalDownloads != 0:
                    self.installstate = 2
                  else:
                    self.installstate = 3
              elif self.installstate == 2:   # Downloading PCMs
                  if self.totalDownloads-self.downloader.count() > 0:
                    totalPercentage = ((self.totalDownloads-self.downloader.count()-1) / (self.totalDownloads+2)) * 100
                  else:
                    totalPercentage = 0
                  self.totalBar.setValue(totalPercentage)
                  if self.downloader.status == self.downloader.Downloading:
                      progress = Decimal(self.downloader.progress)
                      size = Decimal(self.downloader.size)
                      if size == 0:
                          percentage = 0
                          labelStr = "Downloading ({0}/{1}) 0% ...".format(self.totalDownloads-self.downloader.count(),self.totalDownloads)
                      else:
                          percentage = (progress / size) * 100
                          labelStr = "Downloading ({0}/{1}) ({2}/{3} kB) {4}% ...".format(self.totalDownloads-self.downloader.count(),self.totalDownloads,round(progress/1024,2),round(size/1024,2),round(percentage,2))
                      self.updateCurrentLabel(labelStr)
                      self.currentBar.setValue(percentage)
                  elif self.downloader.status == self.downloader.Waiting:
                      self.updateCurrentLabel("Connecting...")
                      self.currentBar.setValue(0)
                      self.downloader.start()
                  elif self.downloader.status == self.downloader.Initializing:
                      self.updateCurrentLabel("Connecting...")
                      self.currentBar.setValue(0)
                      self.downloader.start()
                  elif self.downloader.status == self.downloader.Error:
                      self.updateCurrentLabel("Error: " + self.downloader.errormessage)
                      self.currentBar.setValue(0)
                      self.installstate = 254
                  elif self.downloader.status == self.downloader.Complete:
                      self.updateCurrentLabel("Download Complete!")
                      self.currentBar.setValue(0)
                      self.installstate = 3
                  elif self.downloader.status == self.downloader.Skipping:
                      self.updateCurrentLabel("Matched existing file, skipping...")
                      self.currentBar.setValue(0)
                  elif self.downloader.status == self.downloader.Summing:
                      self.updateCurrentLabel("Downloading ({0}/{1}) Checksumming existing file (will skip download if match)...".format(self.totalDownloads-self.downloader.count(),self.totalDownloads))
                      self.currentBar.setValue(0)
                  else:
                      pass
              elif self.installstate == 3:   # Patching ROM
                  self.updateCurrentLabel("Download finished. Patching ROM...")
                  self.currentBar.setValue(0)
                  totalPercentage = (self.totalDownloads / (self.totalDownloads + 2)) * 100
                  self.totalBar.setValue(totalPercentage)
                  try:
                    os.remove(os.path.join(self.field("destPath").replace("/","\\"), "ff3msu.sfc")) # Avoid a crash later on by removing any sfcs already present in the destination directory.              
                  except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
                  try:
                    os.remove(os.path.join(self.field("destPath").replace("/","\\"), "ff3.sfc")) # Ditto to above.
                  except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
                  patchPath = os.path.join(self.field("destPath"), "ff3msu.ips")
                  destromPath = os.path.join(self.field("destPath"), "ff3msu.sfc")
                  try:
                    self.updateCurrentLabel("Patching: Copying ROM to destination path...")
                    shutil.copy2(self.field("romPath"), destromPath)
                    self.currentBar.setValue(25)
                    self.updateCurrentLabel("Patching: Copying Patch to destination path...")
                    shutil.copy2("ff3msu.ips", self.field("destPath"))
                    self.currentBar.setValue(50)
                    self.updateCurrentLabel("Patching: Checking for SMC header...")
                    myrom = rom.SNESRom(self.field("romPath"))
                    myrom.parse()
                    if myrom.has_smc_header:
                        unheaderedPath = os.path.join(self.field("destPath"), "temp.sfc")
                        self.updateCurrentLabel("Patching: Found SMC header, removing...")
                        newfile = open(unheaderedPath, "wb")
                        romfile = open(destromPath, "rb")
                        _ = romfile.read(512) # Skip the header
                        newfile.write(romfile.read()) # Write everything else to the new file
                        newfile.close()
                        romfile.close()
                        os.remove(destromPath)
                        os.rename(unheaderedPath, destromPath)
                        self.updateCurrentLabel("Patching: Header removed.")
                    else:
                        self.updateCurrentLabel("Patching: No SMC header found.")
                    self.currentBar.setValue(75)
                    self.updateCurrentLabel("Patching: Applying patch...")
                    ips.apply(patchPath, destromPath)
                    os.remove(patchPath)
                    if self.field("twueCheck") == True:
                        self.updateCurrentLabel("Patching: Applying TWUE v1.98...")
                        twuePath = os.path.join(self.field("destPath"), "twue.ips")
                        ips.apply(twuePath, destromPath)
                        os.remove(twuePath)
                    if self.field("mplayerCheck") == True:
                        self.updateCurrentLabel("Patching: Applying Music Player DM Edition...")
                        tmp = "mplayer-csr-main-nh.ips" if self.field("cutsongCheck") == True else "mplayer-main-nh.ips"
                        mplayerPath = os.path.join(self.field("destPath"), tmp)
                        ips.apply(mplayerPath, destromPath)
                        os.remove(mplayerPath)
                    if self.field("cutsongCheck") == True:
                        self.updateCurrentLabel("Patching: Applying Cut Songs Restoration...")
                        csrPath = os.path.join(self.field("destPath"), "csr.ips")
                        ips.apply(csrPath, destromPath)
                        os.remove(csrPath)
                    self.updateCurrentLabel("Patching: Patch successful!")
                    self.currentBar.setValue(100)
                    totalPercentage = (self.totalDownloads+1 / (self.totalDownloads + 2)) * 100
                    self.totalBar.setValue(totalPercentage)
                    self.installstate = 4
                  except Exception as e:
                    self.updateCurrentLabel("Patching: ROM Patching Failed! Error:" + repr(e))
                    print("EXCEPTION DURING PATCHING:",repr(e))
                    self.installstate = 254
              elif self.installstate == 4:   # Final copying/renaming/etc.
                  self.updateCurrentLabel("Finalizing: Copying Manifests and MSU file...")
                  self.currentBar.setValue(0)
                  if self.field("higanButton") == True:
                      shutil.copy2("ff3msu.msu", self.field("destPath"))
                      tmpRomSrc = os.path.join(self.field("destPath"), "ff3msu.sfc")
                      tmpRomDst = os.path.join(self.field("destPath"), "program.rom")
                      tmpMsuSrc = os.path.join(self.field("destPath"), "ff3msu.msu")
                      tmpMsuDst = os.path.join(self.field("destPath"), "msu1.rom")
                      shutil.move(tmpRomSrc, tmpRomDst)
                      shutil.move(tmpMsuSrc, tmpMsuDst)
                      self.currentBar.setValue(50)
                      self.updateCurrentLabel("Finalizing: Higanifying track names...")
                      tmpOldCwd = os.getcwd()
                      os.chdir(self.field("destPath"))
                      pcmsList = glob.glob('ff3-*.pcm')
                      for thisfile in pcmsList:
                          newfilename = thisfile.replace("ff3", "track")
                          os.rename(thisfile, newfilename)
                      os.chdir(tmpOldCwd)
                  elif self.field("SD2SNESButton") == True:
                      shutil.copy2("ff3msu.msu", os.path.join(self.field("destPath"), "ff3.msu"))
                      if os.path.exists(os.path.join(self.field("destPath"), "ff3.sfc")):
                        os.remove(os.path.join(self.field("destPath"), "ff3.sfc"))
                      os.rename(os.path.join(self.field("destPath"), "ff3msu.sfc"), os.path.join(self.field("destPath"), "ff3.sfc"))
                  elif self.field("BSNESButton") == True:
                      shutil.copy2("ff3msu.msu", os.path.join(self.field("destPath"), "ff3.msu"))
                      shutil.copy2("ff3msu.xml", os.path.join(self.field("destPath"), "ff3.xml"))
                      if os.path.exists(os.path.join(self.field("destPath"), "ff3.sfc")):
                        os.remove(os.path.join(self.field("destPath"), "ff3.sfc"))
                      os.rename(os.path.join(self.field("destPath"), "ff3msu.sfc"), os.path.join(self.field("destPath"), "ff3.sfc"))
                  else:
                      pass
                  self.currentBar.setValue(100)
                  self.updateCurrentLabel("Done!")
                  self.totalBar.setValue(100)
                  self.installstate = 255
              elif self.installstate == 254: # Error
                  pass
              elif self.installstate == 255: # Complete
                  if self.soundOn:
                    if self.soundPlayed == False:
                        try:
                            self.laughFile.play()
                        except:
                            print("Failed to play kefka laugh")
                        else:
                            print("Played kefka laugh")
                        self.soundPlayed = True
                  self.compChgSgnl.emit()
              else:
                  pass

        def isComplete(self):
              if self.installstate == 255:
                  return True
              else:
                  return False

