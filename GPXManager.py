import numpy as np
import pandas as pd
#import matplotlib.pyplot as plt
import bisect
#import xml.etree.ElementTree as ET
#import MainWindow
import mapmanager
import operator
from tkinter import filedialog,messagebox
import datetime
import math
import utilities as ut
from scipy import spatial
import time
import PIL
import os
import piexif





df = None
photoDf = None
imageObjectList = []
fileFlag = False

try:
  from lxml import etree
  print("running with lxml.etree")
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
    print("running with cElementTree on Python 2.5+")
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
      print("running with ElementTree on Python 2.5+")
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
        print("running with cElementTree")
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as etree
          print("running with ElementTree")
        except ImportError:
          print("Failed to import ElementTree from any known place")



def load_gpx(file,index):
    global df
    if ".gpx" not in file:
        df = None
        messagebox.showinfo("error", "selected file " + file + " is not a gpx file")
        return
    try:
        tree = etree.parse(file)
        root = tree.getroot()
        data = []
        count = 0
        uri = root.tag.replace("gpx","")
        for name in root.iter(uri+"name"):
            print(name.text)
        for track in root.iter(uri + "trk"):
            for seg in track.iter(uri + "trkpt"):
                #print(seg.get("name"))
                lat = float(seg.get("lat"))
                lon = float(seg.get("lon"))
                #print(seg.get("name"))
                point = [count, lat, lon]
                count += 1
                for child in seg:
                    if child.tag == uri + "time":
                        point.insert(0, child.text)
                if len(point) == 3:
                    point.insert(0, np.nan)
                data.append(point)
        df = pd.DataFrame(data)
        l = ["Time", "Record", "Lat", "Lon"]
        df.columns = l
        df["Time"] = pd.to_datetime(df["Time"],dayfirst=True)
        df["Track"] = "Track " + str(index)
        df.replace(np.inf, np.nan,inplace=True) ## because for some reason, last row speed is calculated as inf
        df = df.dropna()
        df.set_index("Time",inplace=True)
    except Exception as e:
        messagebox.showinfo("error", "Tried to load gpx file, incorrect format or corrupted data")
        print("____________________________________________OOPS_____________________________________________________")
        print(e)
        df = None

def load_tracks(fileList,timeDiff):
    if timeDiff[0] == "-":
        negative = True
    else:
        negative = False
    try:
        timeDiff = datetime.datetime.strptime(timeDiff,"%H:%M:%S")
        timeDiff = datetime.timedelta(hours=timeDiff.hour,minutes=timeDiff.minute,seconds=timeDiff.second)
    except Exception as e:
        timeDiff = datetime.timedelta(hours=0)
    global df,photoDf
    df = None
    for index,file in enumerate(fileList):
        load_gpx(file,index)
    df.reset_index(inplace=True)
    if negative:
        df["Time"] = df["Time"].apply(lambda x: x - timeDiff )
    else:
        df["Time"] = df["Time"].apply(lambda x: x + timeDiff)
    df.set_index("Time",inplace=True)
    print("len of df is", len(df))
    df["Infrastructure"] = "UNASSESSED"
    df.sort_index(inplace=True)
    if not photoDf is None:
        df =df.merge(photoDf,how="left",left_index=True,right_index=True)
        print("-"*100)
    else:
        df["file"] = ""
    df.dropna(inplace=True)
    df["Comments"] = ""
    print(df.head())
    #print("Found", len(photoDf), "points in track")

def load_photos(directory):
    global df,photoDf,imageObjectList
    imageObjectList = []
    photos = []
    photoDf = None
    df = None
    for path, subdirs, files in os.walk(directory):
        for name in files:
            if ".jpg" in name or ".JPG" in name:
                f =os.path.join(path, name)
                img = PIL.Image.open(f)
                exif_data = img._getexif()
                #print("exif data for",f,"is",exif_data)
                #xmp = piexif.load(f)
                #print(xmp.keys(),xmp["Exif"][36867],xmp["GPS"])

                date = datetime.datetime.strptime(exif_data[36867],"%Y:%m:%d %H:%M:%S")
                print([f, date])
                photos.append([f, date])
    photoDf = pd.DataFrame(photos,columns=["file","Time"])
    photoDf["Time"] = pd.to_datetime(photoDf["Time"])
    photoDf.set_index("Time",inplace=True)
    print("Found", len(photoDf),"photos")
    return len(photoDf)
    if not df is None:
        try:
            df.drop('file', axis=1, inplace=True)
        except Exception as e:
            pass
        df =df.merge(photoDf,how="left",left_index=True,right_index=True)
        print("-"*100)
        df.dropna(inplace=True)
        print(df.head())


def load_dataframe_from_csv(file):
    global fileFlag,df
    df = pd.read_csv(file,parse_dates={'datetime': ['Date', 'Time']})

    df.columns = ["Time","file","Lat","Lon","Infrastructure","Comments"]
    df.set_index("Time",inplace=True)

    df["file"].apply(check_file_exists)
    df["Comments"] = df["Comments"].fillna("")
    print(df.head())
    if fileFlag:
        messagebox.showinfo(message="one or more of the loaded photo files does not exist")
        fileFlag = False
        df = None
    return df

def check_file_exists(f):
    global fileFlag
    if not os.path.exists(f):
        fileFlag =True

def get_image_file_list():
    pass

def get_data():
    return df


def get_all_latlons():
    if df is None:
        return []
    return df[["file","Lat","Lon"]].values.tolist()

file = "C:/Users/NWatson/Desktop/Walking Photos/Photo Geotagger & Viewer/Example Garmin Tracks/Garmin Tracks 2.gpx"

directory = "C:/Users/NWatson/Desktop/Walking Photos/Photo Geotagger & Viewer/Example Garmin Photo Output/"

file = "C:/Users/NWatson/Desktop/Walking Photos/Photo Geotagger & Viewer/Example Garmin Tracks/test.csv.csv"

#load_dataframe_from_csv(file)

#load_photos(directory)

#exit()









#load_photos(directory)
#load_tracks([file])
#print(df.iloc[0].name)