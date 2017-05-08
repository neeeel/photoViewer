import tkinter
from PIL import Image,ImageDraw,ImageTk
import GPXManager
import threading
import mapmanager
from tkinter import font,filedialog,messagebox
from tkinter import ttk
import datetime
from tkinter import messagebox
import time


class MainWindow(tkinter.Tk):

    def __init__(self):
        self.tracsisBlue = "#%02x%02x%02x" % (20, 27, 77)
        self.tracsisGrey = "#%02x%02x%02x" % (99, 102, 106)
        super(MainWindow, self).__init__()
        self.state("zoomed")
        self.playEnabled = False
        self.killThreadFlag = False
        self.maxBufferSize = 100
        self.bufferStartIndex = 0 ### this is the index in the dataFrame that the first entry in the buffer refers to.
        ### so we have photos from bufferStartIndex to bufferStartIndex + len(self.imageList) pre-loaded at any time
        self.infrastructureList = ["UNASSESSED","VISIBLE","NOT VISIBLE","UNSURE"]
        self.deleteStatus = "NO POINT SELECTED"
        self.deleteList =[]
        self.statusChanged = False
        self.playSpeed = 1 ### number of seconds between displaying each photo
        self.data = None ### a list holding the photo file name, lats and lons for each point
        self.pixelCoords = [] ### a list holding the x,y coords on the map for each point on the track
        self.currentPhotoPosition=0
        self.imageList = []
        self.imageListLoadingThread = None
        self.lastPhotoUpdateTime = None
        self.currentAfterID = None
        self.infrastructureStatus = 0 ## 0 = no changes, 1 = change to visible, 2 = change to not visible, 3 change to unsure
        self.statusColours = ["black","green","red","purple"]
        self.mapScale = 1
        self.baseMapImage = None
        self.viewPortTopLeft = [0,0]
        self.topLeftOfImage = [0,0]
        ###
        ### set up the controls
        ###

        controlsFont = font.Font(family='Helvetica', size=14)

        controlsFrame = tkinter.Frame(self)

        topFrame = tkinter.Frame(controlsFrame)
        self.photoButton = tkinter.Button(topFrame,text = "Import Photos",font=controlsFont,command=self.load_photos)
        print("colour is",self.photoButton.config("bg")[-1])
        self.photoButton.grid(row=0,column=0,pady=(10,0))
        self.trackButton = tkinter.Button(topFrame, text="Import Tracks",font=controlsFont,command=self.load_tracks,state=tkinter.DISABLED)
        self.trackButton.grid(row=0, column=1,pady=(10,0))
        #tkinter.Button(topFrame, text="Delete Photo",font=controlsFont).grid(row=1, column=0,sticky="ew")
        tkinter.Label(topFrame,text = "Time Difference(hh:mm:ss)\n This value is added to the Track data").grid(row = 1,column = 0,sticky = "ew")
        self.timeEntry = tkinter.Entry(topFrame,width = 9)
        self.timeEntry.grid(row=1,column=1)
        self.timeEntry.insert(0,"0")
        ttk.Separator(topFrame).grid(row=2,column=0,columnspan=2,sticky="ew",pady = 20)
        topFrame.grid(row=0,column=0)

        secondFrame  = tkinter.Frame(controlsFrame)
        self.playButton = tkinter.Button(secondFrame, text="Play\nPhotos", font=controlsFont,command=self.start_playback,bg="red")
        self.playButton.grid(row=3, column=0, pady=(10, 0), sticky="n")
        tkinter.Button(secondFrame, text="Stop\nPhotos", font=controlsFont,command=self.stop).grid(row=3, column=1, pady=(10, 0), sticky="n")
        tkinter.Button(secondFrame, text="<<<", font=controlsFont,command=self.decrement_playback_speed).grid(row=3, column=2, sticky="new", pady=(10, 0))
        tkinter.Button(secondFrame, text=">>>", font=controlsFont,command=self.increment_playback_speed).grid(row=3, column=3, sticky="new", pady=(10, 0))
        self.skipBackwardButton = tkinter.Button(secondFrame, text="Skip Backward", font=controlsFont,command=self.display_previous_photo)
        self.skipBackwardButton.grid(row=4, column=0,columnspan=2, sticky="ew")
        self.skipForwardButton = tkinter.Button(secondFrame, text="Skip Forward", font=controlsFont,command=self.display_next_photo)
        self.skipForwardButton.grid(row=4, column=2,columnspan=2, sticky="ew")
        self.speedLabel = tkinter.Label(secondFrame,text = "Current Speed 1x", font=controlsFont)
        self.speedLabel.grid(row=5,column=1,columnspan=2,sticky="ew",pady = (10,0))
        ttk.Separator(secondFrame).grid(row=6, column=0, columnspan=4, sticky="ew", pady=20)
        secondFrame.grid(row=1,column=0)

        thirdFrame = tkinter.Frame(controlsFrame)
        tkinter.Label(thirdFrame, text="Cycling Infrastructure", font=controlsFont).grid(row=0,column=0,columnspan = 2)
        self.visibleButton = tkinter.Button(thirdFrame, text="VISIBLE", font=controlsFont, width = 11,command=self.visible_clicked)
        self.visibleButton.grid(row=1, column=0, pady=(10, 0), sticky="n")
        self.notVisibleButton = tkinter.Button(thirdFrame, text="NOT VISIBLE", font=controlsFont,command=self.not_visible_clicked)
        self.notVisibleButton.grid(row=1, column=1, pady=(10, 0), sticky="n")
        self.unsureButton = tkinter.Button(thirdFrame, text="UNSURE", font=controlsFont,command=self.unsure_clicked)
        self.unsureButton.grid(row=2, column=0, sticky="n",columnspan = 2)
        self.commentBox = tkinter.Text(thirdFrame,width = 30,height = 10, wrap="none")

        self.commentBox.grid(row=3,column = 0,columnspan = 2)
        tkinter.Button(thirdFrame, text="Save\nComment",command=self.save_comment).grid(row=4, column=0, columnspan=2,pady = (5,0))
        ttk.Separator(thirdFrame).grid(row=5, column=0, columnspan=4, sticky="ew", pady=20)
        thirdFrame.grid(row=2,column=0)

        fourthFrame = tkinter.Frame(controlsFrame)
        tkinter.Button(fourthFrame, text="Import\nCSV", font=controlsFont,command=self.import_from_csv).grid(row=0, column=0, pady=(10, 0), sticky="n")
        tkinter.Button(fourthFrame, text="Export\nCSV", font=controlsFont,command=self.export_to_csv).grid(row=0, column=1, pady=(10, 0), sticky="n")
        tkinter.Button(fourthFrame, text="Geotag\nPhotos", font=controlsFont,state=tkinter.DISABLED).grid(row=0, column=2, pady=(10, 0), sticky="n")
        #ttk.Separator(fourthFrame).grid(row=4, column=0, columnspan=4, sticky="ew", pady=20)
        fourthFrame.grid(row=3,column=0)

        controlsFrame.grid(row=0, column=0, sticky="n")

        self.mapPanelSize = 800  ### TODO change this to deal with different screen res
        self.photoPanelSize = 800
        self.mapPanel = tkinter.Canvas(self, relief=tkinter.RAISED, borderwidth=1,width = self.mapPanelSize,height = self.mapPanelSize)
        self.photoPanel = tkinter.Canvas(self, relief=tkinter.RAISED, borderwidth=1,width = self.photoPanelSize,height = self.photoPanelSize)
        self.mapPanel.bind("<Button-1>",self.map_clicked)
        self.mapPanel.bind("<Button-3>", self.map_right_clicked)
        self.mapPanel.bind("<MouseWheel>",self.on_mousewheel)
        self.bind("<Delete>",self.delete_pressed)
        self.bind("<Escape>", self.escape_pressed)
        self.mapPanel.grid(row=0, column=2, rowspan=3)
        self.photoPanel.grid(row=0, column=1, rowspan=3)

        return
        ###
        ### delete this

        file = "C:/Users/NWatson/Desktop/Walking Photos/Photo Geotagger & Viewer/Example Garmin Tracks/Garmin Tracks.gpx"

        directory = "C:/Users/NWatson/Desktop/Walking Photos/Photo Geotagger & Viewer/Example Garmin Photo Output/"
        GPXManager.load_photos(directory)
        GPXManager.load_tracks([file])
        self.data=GPXManager.get_data()
        print("length ofdata is", len(self.data))
        #print(self.data.head())
        if self.imageListLoadingThread is None:
            self.imageListLoadingThread = threading.Thread(target=self.buffer)
            self.imageListLoadingThread.start()

        coords = [(item[1], item[2]) for item in self.data[["file", "Lat", "Lon"]].values.tolist()]
        centre = mapmanager.get_centre_of_points_alternate(coords, 14)
        zoom = mapmanager.calculateZoomValueAlternate(coords)
        self.pixelCoords = [mapmanager.get_coords(centre, c, zoom) for c in coords]
        self.mapImage = mapmanager.load_map_with_labels(centre[0],centre[1],zoom)

        for index, p in enumerate(self.pixelCoords):
            #print("in load tracks, index is ", index, p)
            self.draw_leg(p, index)

        self.trackButton.configure(state=tkinter.DISABLED)
        self.photoButton.configure(state=tkinter.ACTIVE)

    def on_mousewheel(self,event):
        print("wheel value",event.delta,event.delta/120)
        if self.baseMapImage is None:
            return
        print("redrawing")
        self.mapScale+= event.delta*0.5/120
        if self.mapScale < 1:
            self.mapScale = 1
        print("map scale is now",self.mapScale)
        self.draw_all_gps_points()


    def export_to_csv(self):
        self.escape_pressed(None)
        savefile = filedialog.asksaveasfilename()
        if savefile == "":
            messagebox.showinfo(message="You must select a location and name")
            return
        exportDf = self.data.copy()
        exportDf.reset_index(inplace=True)
        #exportDf["file"] = exportDf["file"].apply(func=lambda x: x.split("\\")[-1])
        exportDf["Date"] = exportDf["Time"].apply(func=lambda x:datetime.datetime.strftime(x,"%d/%m/%Y"))
        exportDf["Time"] = exportDf["Time"].apply(func=lambda x: datetime.datetime.strftime(x,"%H:%M:%S"))
        exportDf = exportDf[["file","Date","Time","Lat","Lon","Infrastructure","Comments"]]
        try:
            exportDf.to_csv(savefile + ".csv",index=False,header=["Photo Name","Date","Time","Lat","Lon","Infrastructure","Comments"])
        except PermissionError as e:
            messagebox.showinfo(message="File is already open, please close file and re-export")

    def import_from_csv(self):
        self.escape_pressed(None)
        file = filedialog.askopenfilename()
        if file == "" or not ".csv" in file:
            messagebox.showinfo(message="You need to select a .csv file")
            return
        if not self.imageListLoadingThread is None:
            ### kill the image loading thread, if it exists
            print("sending signal to kill the thread")
            self.killThreadFlag = True
            self.imageListLoadingThread = None
            print("thread dead")
        self.data = None
        self.stop()
        self.currentPhotoPosition = 0
        self.mapPanel.delete(tkinter.ALL)
        self.imageList = []
        self.data = GPXManager.load_dataframe_from_csv(file)
        if self.imageListLoadingThread is None:
            self.killThreadFlag = False
            self.imageListLoadingThread = threading.Thread(target=self.buffer)
            self.imageListLoadingThread.daemon = True
            self.imageListLoadingThread.start()

        coords = [(item[1],item[2]) for item in self.data[["file","Lat","Lon"]].values.tolist()]
        self.mapCentre = mapmanager.get_centre_of_points_alternate(coords, 14)
        self.mapZoom = mapmanager.calculateZoomValueAlternate(coords)
        self.pixelCoords = [mapmanager.get_coords(self.mapCentre, c, self.mapZoom) for c in coords]
        self.baseMapImage = mapmanager.load_high_def_map_with_labels(self.mapCentre[0], self.mapCentre[1], self.mapZoom)
        self.draw_all_gps_points()
        self.display_photo()
        self.trackButton.configure(state=tkinter.DISABLED)
        self.photoButton.configure(state=tkinter.ACTIVE)

    def save_comment(self):
        text = self.commentBox.get("1.0",tkinter.END)
        #print(text)
        if not self.data is None:
            self.data.ix[self.currentPhotoPosition, "Comments"] = text.rstrip('\r\n')
            #self.commentBox.delete("1.0", tkinter.END)

    def load_photos(self):
        self.escape_pressed(None)
        if not self.imageListLoadingThread is None:
            ### kill the image loading thread, if it exists
            print("sending signal to kill the thread")
            self.killThreadFlag = True
            self.imageListLoadingThread = None
            print("thread dead")
        self.data = None
        self.stop()
        self.currentPhotoPosition = 0
        self.mapPanel.delete(tkinter.ALL)
        self.imageList = []
        directory = filedialog.askdirectory()
        if directory == "":
            messagebox.showinfo(message="No directory Selected")
            return
        numPhotos = GPXManager.load_photos(directory)
        messagebox.showinfo(message=str(numPhotos) + " photos loaded")
        self.photoButton.configure(state=tkinter.DISABLED)
        self.trackButton.configure(state=tkinter.ACTIVE)

    def load_tracks(self):
        self.escape_pressed(None)
        self.mapPanel.delete(tkinter.ALL)
        fileList = list(filedialog.askopenfilenames(initialdir=dir))
        self.trackButton.configure(state=tkinter.DISABLED)
        self.photoButton.configure(state=tkinter.ACTIVE)
        if fileList == []:
            messagebox.showinfo(message="No GPX files Selected")
            return
        timeValue = self.timeEntry.get()
        if timeValue == "":
            timeValue = "0"
        GPXManager.load_tracks(fileList,timeValue)
        self.data = GPXManager.get_data()
        print("length ofdata is",len(self.data))
        if len(self.data) ==0:
            messagebox.showinfo(message="Couldnt match any photos with track data")
            return
        messagebox.showinfo(message="Matched " + str(len(self.data)) + " photos and GPS points")
        #print(self.data.head())
        if self.imageListLoadingThread is None:
            self.killThreadFlag = False
            self.imageListLoadingThread = threading.Thread(target=self.buffer)
            self.imageListLoadingThread.daemon = True
            self.imageListLoadingThread.start()
        coords = [(item[1], item[2]) for item in self.data[["file", "Lat", "Lon"]].values.tolist()]
        self.mapCentre = mapmanager.get_centre_of_points_alternate(coords, 14)
        self.mapZoom = mapmanager.calculateZoomValueAlternate(coords)
        self.pixelCoords = [mapmanager.get_coords(self.mapCentre, c, self.mapZoom) for c in coords]
        self.baseMapImage = mapmanager.load_high_def_map_with_labels(self.mapCentre[0], self.mapCentre[1], self.mapZoom)
        #self.mapPanel.create_image(0, 0, image=self.baseMapImage, anchor=tkinter.NW, tags=("map",))
        self.draw_all_gps_points()
        self.display_photo()

    def draw_all_gps_points(self,x=0,y=0):
        start = time.time() * 1000
        self.mapPanel.delete(tkinter.ALL)
        iw, ih = self.baseMapImage.size
        # calculate crop rect
        cw, ch = iw / self.mapScale, ih / self.mapScale
        print("crop rect is",cw,ch)
        if cw > iw or ch > ih:
            cw = iw
            ch = ih
        # crop it
        ###
        ### self.viewPortTopLeft is where the user has dragged or adjusted the image
        if self.viewPortTopLeft[0] < -int(iw / 2 - cw / 2):
            self.viewPortTopLeft[0] = -int(iw / 2 - cw / 2)
        if self.viewPortTopLeft[1] < -int(ih / 2 - ch / 2):
            self.viewPortTopLeft[1] = -int(ih / 2 - ch / 2)
        print("viewporttopleft is", self.viewPortTopLeft, "cw is", cw)
        ###
        ### self.topLeftOfImage is the absolute coords of the displayed part of the map
        ### eg [100,100] would mean that (0,0) on the map panel would be showing [100,100] of the base map image
        ###

        self.topLeftOfImage[0] = int(iw / 2 - cw / 2) + self.viewPortTopLeft[0]
        self.topLeftOfImage[1] = int(ih / 2 - ch / 2) + self.viewPortTopLeft[1]

        print("_x,_y are",self.topLeftOfImage)
        print("view port top left is",self.viewPortTopLeft)
        tmp = self.baseMapImage.crop((self.topLeftOfImage[0], self.topLeftOfImage[1], self.topLeftOfImage[0] + int(cw), self.topLeftOfImage[1] + int(ch)))
        size = int(cw * self.mapScale), int(ch * self.mapScale)
        # draw
        self.img = ImageTk.PhotoImage(tmp.resize((800,800)))
        self.img_id = self.mapPanel.create_image(x, y, image=self.img, anchor=tkinter.NW, tags=("map",))
        for index, p in enumerate(self.pixelCoords):
            self.draw_leg(p, index)
        print("drawing complete map took",(time.time() * 1000) - start)

    def buffer(self):
        while not self.killThreadFlag:
            if self.playSpeed > 0:
                ### load the photo to the end of the buffer
                nextIndexToLoad = self.bufferStartIndex + len(self.imageList)
                ### is buffer full?
                if len(self.imageList) >= self.maxBufferSize:
                    ### yes it is
                    if self.currentPhotoPosition >= self.bufferStartIndex + len(self.imageList) or self.currentPhotoPosition < self.bufferStartIndex:  ### is the current photo to display not conta9ined in the imageList?
                        ### no, its not currently stored in the image list
                        ### so we need to rebuffer entirely
                        #print("image list is full, and the selected photo is not contained in the image list, rebuffering with empty list")
                        self.imageList = []
                        self.bufferStartIndex = self.currentPhotoPosition
                        nextIndexToLoad = self.currentPhotoPosition
                        if nextIndexToLoad < len(self.data):
                            img = ImageTk.PhotoImage(Image.open(self.data.iloc[nextIndexToLoad]["file"]).resize((self.photoPanelSize,self.photoPanelSize), Image.ANTIALIAS))
                            self.imageList.append(img)
                    elif self.currentPhotoPosition > self.bufferStartIndex + len(self.imageList) - 5:  ### are we close to the end?
                        ### yes we are
                        ### so re buffer from current position

                        self.bufferStartIndex = self.bufferStartIndex + len(self.imageList) - 5
                        self.imageList = self.imageList[-5:]
                        print("rebuffering from current position,bufferstartindex is now", self.bufferStartIndex)




                    elif self.currentPhotoPosition - self.bufferStartIndex >= len(self.imageList) / 2:### are we past halfway?
                        ### yes we are, so we need to drop some and load some
                        #print("image list is full, and we are past half way, so we are removing a photo from begninngin, and adding one to the end")
                        self.imageList = self.imageList[1:]
                        self.bufferStartIndex += 1
                        if nextIndexToLoad < len(self.data):
                            img = ImageTk.PhotoImage(Image.open(self.data.iloc[nextIndexToLoad]["file"]).resize((self.photoPanelSize,self.photoPanelSize), Image.ANTIALIAS))
                            self.imageList.append(img)
                        #print("buffer start index is", self.bufferStartIndex)
                    else:
                        ### no, we arent past half way, so we dont need to do anything
                        #print("doing nothing")
                        pass
                else:
                    ### no buffer isnt full, so we can load some more photos in
                    if self.currentPhotoPosition >= self.bufferStartIndex + len(self.imageList) or self.currentPhotoPosition < self.bufferStartIndex:  ### is the current photo to display not conta9ined in the imageList?
                        ### no, its not currently stored in the image list
                        ### so we need to rebuffer entirely
                        #print("image list is not full, but selected photo,",self.currentPhotoPosition," is outside of image list, buffer start is ",self.bufferStartIndex,"no of entries in list",len(self.imageList))
                        self.imageList = []
                        self.bufferStartIndex = self.currentPhotoPosition
                        nextIndexToLoad = self.currentPhotoPosition
                        if nextIndexToLoad < len(self.data):
                            img = ImageTk.PhotoImage(Image.open(self.data.iloc[nextIndexToLoad]["file"]).resize((self.photoPanelSize,self.photoPanelSize), Image.ANTIALIAS))
                            self.imageList.append(img)

                    else:
                        #print("image list is not full, adding next photo to end of list")
                        #print("next index to load is", nextIndexToLoad)
                        if nextIndexToLoad < len(self.data):
                            img = ImageTk.PhotoImage(Image.open(self.data.iloc[nextIndexToLoad]["file"]).resize((self.photoPanelSize,self.photoPanelSize), Image.ANTIALIAS))
                            self.imageList.append(img)
                time.sleep(0.05)
        else:
            print("ending thread")
            self.imageListLoadingThread = None
            self.killThreadFlag = False

    def draw_leg(self,coords,index):
        #print("in draw leg, index is",index,type(index))
        x, y = coords

        ### translate point relative to viewport
        x -= self.topLeftOfImage[0]
        y -= self.topLeftOfImage[1]
        ### adjust point to fit the 800x800 display panel
        x = x * 800 / (1280 / self.mapScale)
        y = y * 800 / (1280 / self.mapScale)
        #print("after scaling, point is", x, y)
        try:
            widgets = self.mapPanel.find_withtag("point_" + str(index))
            #print("widgets are",widgets)
            self.mapPanel.delete("point_" + str(index))
            #print("deleting widget", widgets, "from map")
        except Exception as e:
            ### point doesnt exist
            pass
        status =  self.infrastructureList.index( self.data.iloc[index]["Infrastructure"])
        #print("redrawing leg", index,"infrastruture is",status,"colour is",self.statusColours[status])
        if index == self.currentPhotoPosition:
            try:
                self.mapPanel.delete("highlight")
            except Exception as e:
                ### the highlight cirle may not exist
                pass
            #print("HERERERE")
            self.mapPanel.create_oval(x - 10, y - 10, x + 10, y + 10, fill="yellow", width=0,tags=("highlight", "curr_" + str(self.currentPhotoPosition),))
        obj = self.mapPanel.create_oval([x - 5, y - 5, x + 5, y + 5], fill=self.statusColours[status],width=0,tags=("point_" + str(index),))
        #print("created new point with tag",self.mapPanel.gettags(obj),obj)

    def display_photo(self):
        #print("trying to display photo no",self.currentPhotoPosition,"buffer start index is",self.bufferStartIndex)
        self.lastPhotoUpdateTime = int(round(time.time() * 1000))
        self.photoPanel.delete(tkinter.ALL)
        try:
            photoToDisplay = self.currentPhotoPosition - self.bufferStartIndex
            ###
            ### if photoToDisplay is negative, it means user has selected a photo that occurs before the first photo
            ### that is loaded into imagelist.We want to throw an error if this is the case
            if photoToDisplay < 0:
                print("photo to display is",photoToDisplay,self.imageList[self.maxBufferSize + 1])

            #print("index in imageList of photo to display is",photoToDisplay)
            ###
            ### check to see if there are at least 5 entries in the list, by trying to access index 6, so it
            ### will throw an error if theres less than 5 photos loaded
            ###
            print(self.imageList[5]) ### this line throws the error, keep it
            self.mapPanel.delete("text")
            text = self.data.iloc[self.currentPhotoPosition].name
            self.mapPanel.create_text(100, 10, text=text, tags=("text",))
            self.photoPanel.create_image(0, 0, image=self.imageList[photoToDisplay], anchor=tkinter.NW)
            if self.playEnabled:
                if self.infrastructureStatus != 0:
                    self.data.ix[self.currentPhotoPosition,"Infrastructure"] = self.infrastructureList[self.infrastructureStatus]
                    print("set status of",self.currentPhotoPosition,"to",self.data.iloc[self.currentPhotoPosition]["Infrastructure"])
            self.draw_leg(self.pixelCoords[self.currentPhotoPosition],self.currentPhotoPosition) ## redraw the selected point with highlight
            self.photoPanel.delete("text")
            self.commentBox.configure(state=tkinter.NORMAL)
            self.commentBox.delete("1.0", tkinter.END)
            print("comments for photo",self.currentPhotoPosition," are " ,self.data.iloc[self.currentPhotoPosition]["Comments"])
            self.commentBox.insert("1.0",self.data.iloc[self.currentPhotoPosition]["Comments"])
            if self.playEnabled: ### only disable text box if we are in play mode
                self.commentBox.configure(state=tkinter.DISABLED)
            return True
        except IndexError as e:
            self.photoPanel.create_text(370,350,text="BUFFERING",font=("Purisa", 28),tags=("text",),fill="red")
            self.after(50,self.display_photo)

    def display_next_photo(self):
        self.currentPhotoPosition += 1
        if self.currentPhotoPosition >= len(self.data):
            self.currentPhotoPosition -= 1
            self.playEnabled = False
            self.stop()
        self.display_photo()

    def display_previous_photo(self):
        self.currentPhotoPosition -= 1
        if self.currentPhotoPosition <= 0:
            self.currentPhotoPosition = 0
            self.playEnabled = False
            self.stop()
        print("trying to dsiplay photo", self.currentPhotoPosition)
        self.display_photo()

    def on_press_to_move(self,event):
        winX = event.x - self.mapPanel.canvasx(0)
        winY = event.y - self.mapPanel.canvasy(0)
        print("clicked at", winX, winY)
        self.dragInfo["Widget"] = self.mapPanel.find_closest(event.x, event.y, halo=10)[0]
        self.dragInfo["xCoord"] = winX
        self.dragInfo["yCoord"] = winY
        tags = self.mapPanel.gettags(self.dragInfo["Widget"])
        print("in press to move, tags are",tags)

    def map_clicked(self,event):
        if self.playEnabled:
            return
        x = self.mapPanel.canvasx(event.x)
        y = self.mapPanel.canvasy(event.y)
        widgets  = self.mapPanel.find_overlapping(x-1, y-1,x+1, y+1)
        tags = self.mapPanel.gettags(widgets[0])
        print("in map clicked, tags are", tags)
        print(widgets)
        if len(widgets)>1:
            point = self.mapPanel.gettags(widgets[1])[0]
            print("point is",point)
            if "point" in point:
                point = int(point.replace("point_",""))
                print("point is now",point)
                self.currentPhotoPosition = point
                print("self.currentphotopos is",self.currentPhotoPosition)
                self.display_photo()
        else:
            ### user has clicked map only
            winX = event.x - self.mapPanel.canvasx(0)
            winY = event.y - self.mapPanel.canvasy(0)
            print("clicked at", winX, winY)
            self.dragInfo = {}
            self.dragInfo["Widget"] = widgets[0]
            self.dragInfo["xCoord"] = winX
            self.dragInfo["yCoord"] = winY
            self.dragInfo["tag"] = "map"
            self.mapClickedCoords = (winX, winY)
            self.mapPanel.bind("<B1-Motion>", self.on_movement)
            self.mapPanel.bind("<ButtonRelease-1>", self.on_release_to_move_map)

    def on_release_to_move_map(self,event):
        winX = event.x - self.mapPanel.canvasx(0)
        winY = event.y - self.mapPanel.canvasy(0)
        print("map was moved", winX - self.mapClickedCoords[0], winY - self.mapClickedCoords[1])
        self.mapPanel.unbind("<B1-Motion>")
        self.mapPanel.unbind("<ButtonRelease-1>")
        print("before adjustment, viewporttopleft is",self.viewPortTopLeft)
        if winX - self.mapClickedCoords[0] == 0 and winY - self.mapClickedCoords[1] == 0:
            return
        if self.mapScale == 1:
            self.viewPortTopLeft = [0,0]
        else:
            self.viewPortTopLeft[0] -= (winX - self.mapClickedCoords[0]) *(1280 / self.mapScale)/800
            self.viewPortTopLeft[1] -= (winY - self.mapClickedCoords[1])* (1280 / self.mapScale)/800
        print("in release to move, viewporttopleft is",self.viewPortTopLeft)
        self.draw_all_gps_points()

    def on_movement(self,event):
        #print("tag is", self.dragInfo["tag"])

        winX = event.x - self.mapPanel.canvasx(0)
        winY = event.y - self.mapPanel.canvasy(0)
        #print("mouse is now at", winX, winY)
        newX = winX - self.dragInfo["xCoord"]
        newY = winY - self.dragInfo["yCoord"]

        if self.dragInfo["tag"] == "map":
            for child in self.mapPanel.find_all():
                self.mapPanel.move(child, newX, newY)
        self.dragInfo["xCoord"] = winX
        self.dragInfo["yCoord"] = winY

    def map_right_clicked(self,event):
        if self.playEnabled:
            return
        x = self.mapPanel.canvasx(event.x)
        y = self.mapPanel.canvasy(event.y)
        widgets  = self.mapPanel.find_overlapping(x-1, y-1,x+1, y+1)
        print(widgets)
        if len(widgets)>1:
            point = self.mapPanel.gettags(widgets[1])[0]
            print("point is",point)
            if point == "highlight":
                currentPoint = self.mapPanel.find_withtag("highlight")[0]
                tags = self.mapPanel.gettags(currentPoint)
                index = int(tags[1].replace("curr_", ""))
                point = "point_" + str(index)
            if "point" in point:
                point = int(point.replace("point_",""))
                print("selected point is",point,"current delete status is",self.deleteStatus)
                if self.deleteStatus == "NO POINT SELECTED":
                    self.deleteStatus = "FIRST POINT SELECTED"
                    self.deleteList = [point]
                    x,y = self.pixelCoords[point]
                    ### translate point relative to viewport
                    x -= self.topLeftOfImage[0]
                    y -= self.topLeftOfImage[1]
                    ### adjust point to fit the 800x800 display panel
                    x = x * 800 / (1280 / self.mapScale)
                    y = y * 800 / (1280 / self.mapScale)
                    self.mapPanel.create_oval([x - 5, y - 5, x + 5, y + 5], fill="light blue", width=0, tags=("delete",))
                elif self.deleteStatus == "FIRST POINT SELECTED":
                    self.deleteStatus = "SECOND POINT SELECTED"
                    self.deleteList.append(point)
                    self.deleteList = sorted(self.deleteList)
                    coords = [(item[1], item[2]) for item in self.data[["file", "Lat", "Lon"]].values.tolist()]
                    centre = mapmanager.get_centre_of_points_alternate(coords, 14)
                    zoom = mapmanager.calculateZoomValueAlternate(coords)
                    deleteCoords = [mapmanager.get_coords(centre, c, zoom) for c in coords[self.deleteList[0]:self.deleteList[1]+1]]
                    for p in deleteCoords:
                        x,y = p
                        ### translate point relative to viewport
                        x -= self.topLeftOfImage[0]
                        y -= self.topLeftOfImage[1]
                        ### adjust point to fit the 800x800 display panel
                        x = x * 800 / (1280 / self.mapScale)
                        y = y * 800 / (1280 / self.mapScale)
                        self.mapPanel.create_oval([x - 5, y - 5, x + 5, y + 5], fill="light blue",width=0,tags=("delete",))
                print("delete status is",self.deleteStatus,"list is",self.deleteList)

    def callback_function(self):
        print("in callback function")
        self.delete_pressed(None)

    def escape_pressed(self,event):
        print("Escape pressed")
        self.deleteStatus = "NO POINT SELECTED"
        deletePoints = self.mapPanel.find_withtag("delete")
        print("deletepoints are",deletePoints)
        self.mapPanel.delete("delete")

    def delete_pressed(self,event):
        print("detected Delete Press")
        if self.deleteStatus == "FIRST POINT SELECTED":
            self.deleteStatus = "SECOND POINT SELECTED"
            self.deleteList.append(self.deleteList[0])
        if self.deleteStatus == "SECOND POINT SELECTED":
            self.deleteList = sorted(self.deleteList)

            self.killThreadFlag = True
            print("set kill thread flag to",self.killThreadFlag,"thread is",self.imageListLoadingThread)
            if not self.imageListLoadingThread is None:
                print("setting call to callback function")
                self.after(100,self.callback_function)
                print("returning")
                return
            print("self.deletelist is", self.deleteList)
            self.deleteStatus = "NO POINT SELECTED"

            self.currentPhotoPosition = 0
            self.imageList = []
            self.data.drop(self.data.index[self.deleteList[0]:self.deleteList[1] + 1], inplace=True)
            coords = [(item[1], item[2]) for item in self.data[["file", "Lat", "Lon"]].values.tolist()]
            self.pixelCoords = [mapmanager.get_coords(self.mapCentre, c, self.mapZoom) for c in coords]
            self.mapPanel.delete(tkinter.ALL)
            if self.imageListLoadingThread is None:
                self.killThreadFlag = False
                self.imageListLoadingThread = threading.Thread(target=self.buffer)
                self.imageListLoadingThread.daemon = True
                self.imageListLoadingThread.start()

            self.draw_all_gps_points()
            self.display_photo()



    ###
    ### Controls for the playback of photos
    ###

    def start_playback(self):
        if self.playEnabled==False:
            self.escape_pressed(None)
            self.mapPanel.unbind("<Button-3>")
            self.unbind("<Delete>")
            self.unbind("<Escape>")
            self.playEnabled=True
            ###
            ### mark current point with the currently selected infrastructure
            if self.infrastructureStatus != 0:
                currentPoint = self.mapPanel.find_withtag("highlight")[0]
                tags = self.mapPanel.gettags(currentPoint)
                index = int(tags[1].replace("curr_", ""))
                self.data.ix[index, "Infrastructure"] = self.infrastructureList[self.infrastructureStatus]
                self.draw_leg(self.pixelCoords[index], index)
            self.play()
            self.playButton.configure(bg="green")
            self.commentBox.configure(state=tkinter.DISABLED)
            self.skipBackwardButton.configure(state=tkinter.DISABLED)
            self.skipForwardButton.configure(state=tkinter.DISABLED)

    def play(self):
        if self.playEnabled:

            if self.playSpeed < 0:
                if self.display_photo():
                    self.currentPhotoPosition -= 1
                    if self.currentPhotoPosition <= 0:
                        self.currentPhotoPosition = 0
                        self.playEnabled = False
                else:
                    pass
            else:
                if self.display_photo():
                    self.currentPhotoPosition += 1
                    if self.currentPhotoPosition >= len(self.data):
                        self.currentPhotoPosition -= 1
                        self.playEnabled = False
                        self.stop()
            print("setting next call to play to 1 second")
            timeSinceLastDisplay = int(round(time.time() * 1000)) - self.lastPhotoUpdateTime
            print("time since last display is",timeSinceLastDisplay)
            self.currentAfterID=self.after(int(1000/abs(self.playSpeed))-timeSinceLastDisplay,self.play)

    def highlight_current_location(self):
        ###
        ### display a white circle around the current location on the track map
        ###
        try:
            self.mapPanel.delete("highlight")
        except Exception as e:
            ### the highlight cirle may not exist
            pass
        print("HERERERE")
        x, y = self.pixelCoords[self.currentPhotoPosition]
        self.mapPanel.delete("point_" + str(self.currentPhotoPosition))
        self.mapPanel.create_oval(x - 10, y - 10, x + 10, y + 10, fill="yellow", width=0, tags=("highlight","curr_" + str(self.currentPhotoPosition),))
        self.draw_leg((x,y),self.currentPhotoPosition)

    def stop(self):
        self.playEnabled = False
        self.playButton.configure(bg="red")
        self.skipBackwardButton.configure(state=tkinter.ACTIVE)
        self.skipForwardButton.configure(state=tkinter.ACTIVE)
        self.mapPanel.bind("<Button-3>", self.map_right_clicked)
        self.bind("<Delete>", self.delete_pressed)
        self.bind("<Escape>", self.escape_pressed)
        try:
            self.commentBox.configure(state=tkinter.NORMAL)
        except Exception as e:
            print(e)

    def increment_playback_speed(self):
        print("incrementing playback speed")
        self.playSpeed+=1
        if self.playSpeed==0:
            self.playSpeed = 1
        if self.playSpeed>5:
            self.playSpeed=5
        self.speedLabel.configure(text="Current Speed " + str(self.playSpeed) + "x")

    def decrement_playback_speed(self):
        self.playSpeed-=1
        #if self.playSpeed==0:
            #self.playSpeed = -1
        if self.playSpeed<1:
            self.playSpeed=1
        self.speedLabel.configure(text="Current Speed " + str(self.playSpeed) + "x")

    def visible_clicked(self):
        if self.infrastructureStatus == 1:
            self.infrastructureStatus =0
            self.visibleButton.configure(bg="SystemButtonFace")
        else:

            self.infrastructureStatus = 1
            self.statusChanged = True
            self.visibleButton.configure(bg="green")
            self.notVisibleButton.configure(bg="SystemButtonFace")
            self.unsureButton.configure(bg="SystemButtonFace")
            if not self.playEnabled:
                return
            if not self.currentAfterID is None:
                self.after_cancel(self.currentAfterID)
                timeSinceLastDisplay = int(round(time.time() * 1000)) - self.lastPhotoUpdateTime
                print("time since last display is",timeSinceLastDisplay)
                print("scheduling next display in ", int(1000 / abs(self.playSpeed)) - timeSinceLastDisplay)
                currentPoint = self.mapPanel.find_withtag("highlight")[0]
                tags = self.mapPanel.gettags(currentPoint)
                index = int(tags[1].replace("curr_",""))
                self.data.ix[index,"Infrastructure"] = self.infrastructureList[self.infrastructureStatus]
                self.draw_leg(self.pixelCoords[index],index)
                self.currentAfterID = self.after(int(1000 / abs(self.playSpeed)) - timeSinceLastDisplay, self.play)
            else:
                self.display_photo()

    def not_visible_clicked(self):
        if self.infrastructureStatus == 2:
            self.infrastructureStatus =0
            self.notVisibleButton.configure(bg="SystemButtonFace")
        else:

            self.infrastructureStatus = 2
            self.statusChanged = True
            self.notVisibleButton.configure(bg="red")
            self.visibleButton.configure(bg="SystemButtonFace")
            self.unsureButton.configure(bg="SystemButtonFace")
            if not self.playEnabled:
                return
            if not self.currentAfterID is None:
                self.after_cancel(self.currentAfterID)
                timeSinceLastDisplay = int(round(time.time() * 1000)) - self.lastPhotoUpdateTime
                print("time since last display is", timeSinceLastDisplay)
                print("scheduling next display in ", int(1000 / abs(self.playSpeed)) - timeSinceLastDisplay)
                currentPoint = self.mapPanel.find_withtag("highlight")[0]
                tags = self.mapPanel.gettags(currentPoint)
                index = int(tags[1].replace("curr_", ""))
                self.data.ix[index, "Infrastructure"] = self.infrastructureList[self.infrastructureStatus]
                self.draw_leg(self.pixelCoords[index], index)
                self.currentAfterID = self.after(int(1000 / abs(self.playSpeed)) - timeSinceLastDisplay, self.play)
            else:
                self.display_photo()

    def unsure_clicked(self):
        if self.infrastructureStatus == 3:
            self.infrastructureStatus =0
            self.unsureButton.configure(bg="SystemButtonFace")
        else:

            self.infrastructureStatus = 3
            self.statusChanged = True
            self.visibleButton.configure(bg="SystemButtonFace")
            self.notVisibleButton.configure(bg="SystemButtonFace")
            self.unsureButton.configure(bg="purple")
            if not self.playEnabled:
                return
            if not self.currentAfterID is None:
                self.after_cancel(self.currentAfterID)
                timeSinceLastDisplay = int(round(time.time() * 1000)) - self.lastPhotoUpdateTime
                print("time since last display is", timeSinceLastDisplay)
                print("scheduling next display in ",int(1000 / abs(self.playSpeed)) - timeSinceLastDisplay)
                currentPoint = self.mapPanel.find_withtag("highlight")[0]
                tags = self.mapPanel.gettags(currentPoint)
                index = int(tags[1].replace("curr_", ""))
                self.data.ix[index, "Infrastructure"] = self.infrastructureList[self.infrastructureStatus]
                self.draw_leg(self.pixelCoords[index], index)
                self.currentAfterID = self.after(int(1000 / abs(self.playSpeed)) - timeSinceLastDisplay, self.play)
            else:
                self.display_photo()


win = MainWindow()
win.mainloop()