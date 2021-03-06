#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gtk
try:
  import hildon
except ImportError:
  hildon=None
import pygst
pygst.require("0.10")
import gst
import Image
import time
import gobject #for idle loop and threads
gobject.threads_init()

#Глобальные объекты и переменные
pipe=None
if hildon:
  src = gst.element_factory_make("v4l2src", "src")
else:
  src = gst.element_factory_make("videotestsrc")

caps1=gst.element_factory_make("capsfilter")
caps1.set_property('caps', gst.caps_from_string("video/x-raw-rgb,width=640,height=480,framerate=25/1"))
tee=gst.element_factory_make("tee")
queue1= gst.element_factory_make("queue")
sink=gst.element_factory_make("xvimagesink")
queue2= gst.element_factory_make("queue")
colorsp=gst.element_factory_make("ffmpegcolorspace")
caps2=gst.element_factory_make("capsfilter")
caps2.set_property('caps', gst.caps_from_string("video/x-raw-rgb,bpp=24,depth=24"))
fakesink = gst.element_factory_make("fakesink")
mux=gst.element_factory_make("avimux")
filesink=gst.element_factory_make("filesink")
enc=gst.element_factory_make("jpegenc")
#enc=gst.element_factory_make("hantro4200enc") #если писать в mp4
caps3=gst.element_factory_make("capsfilter")
caps3.set_property('caps', gst.caps_from_string("video/x-raw-yuv,width=640,height=480,framerate=25/1"))
record=False #признак идущей записи видео
mode="foto" # Режим foto,livefoto,video,livevideo,record,liverecord,stream,livestream
#Режимы на live с отображением картинки на экране
ShotPressed=False #нажата ли кнопка съемки
#Кнопки
dispBtn=None
modeBtn=None
#Признак того, что кадр в буффере нужно сохраненить в файл
save=False
#добавить трёхсекундный просмотр картинки после съёмки, если включено Live view
#show_image=False
#Буфер для картинки
picbuf=None
if hildon:
    #Путь для сохранения - вместо жестко прописаного добавить чтение ini файла и создание инишки при отсутствии с парамертами по умолчанию    
    picpath="/media/mmc1/Images/"
    vidpath="/media/mmc1/Videos/"
    try:
      os.mkdir(picpath)
      os.mkdir(vidpath)
    except OSError:
      pass
else:
    picpath="./"
    vidpath="./"
#---------------------------------------------------
def save_jpeg():
  global picbuf
  global picpath
  pixbuf=gtk.gdk.pixbuf_new_from_data(picbuf,gtk.gdk.COLORSPACE_RGB,False,8,640,480,3*640)
  filename=picpath+time.strftime("%y%m%d_%H%M%S", time.localtime())+".jpg"
  pixbuf.save(filename,"jpeg",{"quality":"100"})
  print (filename)
#---------------------------------------------------
def buffer_cb(pad,buffer):
#Если установлен признак save сохраняем буфер кадра в picbuf
    global save
    global picbuf
    if save:
      print ("frame buffer copied")
      save=False
      picbuf=buffer
      if mode=="livefoto": # в режиме live на время записи останавливаем pipeline
        gobject.idle_add(pause_pipe) #Adds a function to be called whenever there are no higher priority events pending
    return True
#---------------------------------------------------
def pause_pipe():
  global pipe
  print ("pause pipe")
  pipe.set_state(gst.STATE_NULL)
  pipe=None
  return False #If the function returns FALSE it is automatically removed from the list

def key_press_cb(widget,event):
#При нажатии F6 устанавливаем признак save
  global pipe
  global save
  global ShotPressed
  global record
  global vidpath
  print("key ",event.keyval," pressed")
  print ("record=",record)
  if event.keyval==gtk.keysyms.F6:
    if ShotPressed==False: #Для избежания автоповтора нажатий
      ShotPressed=True
      if (mode=="foto") or (mode=="livefoto"):
        save=True
        print("save flag set")
      if mode=="video": # устанавливаем имя файла для видео
        if record==False: #если запись не идет, то начинаем писать
          record=True
          filename=vidpath+time.strftime("%y%m%d_%H%M%S", time.localtime())+".avi"
          filesink.set_property('location', filename)
          pipe.set_state(gst.STATE_PLAYING)
          print("record start")
        else: #останавливаем запись
          pipe.set_state(gst.STATE_NULL)
          record=False
          print("record stop")  

      if mode=="livevideo": # устанавливаем имя файла для видео
        if record==False: #если запись не идет, то начинаем писать
          record=True
          pipe.set_state(gst.STATE_NULL)
          filename=vidpath+time.strftime("%y%m%d_%H%M%S", time.localtime())+".avi"
          filesink.set_property('location', filename)
          sink.set_xwindow_id(screen.window.xid)
          pipe.set_state(gst.STATE_PLAYING)
          print("record start")
        else: #останавливаем запись
          make_pipe()
          print("record stop")  

  if event.keyval==gtk.keysyms.Escape: #по ESC выходим
    window.destroy()
#---------------------------------------------------
def key_release_cb(widget,event):
#При отпускании F6 записываем буфер в jpeg
  global pipe
  global ShotPressed
  print("key ",event.keyval," released")
  if event.keyval==gtk.keysyms.F6:
      if mode=="foto":
        save_jpeg()
      if mode=="livefoto":
        save_jpeg()
        print ("resume pipe")
        make_pipe()
        print ("pipe resumed")
      ShotPressed=False  #снимаем признак нажатия кнопки спуска
#---------------------------------------------------
def destroy(widget, data=None):
  global pipe
  pipe.set_state(gst.STATE_NULL)
  gtk.main_quit()
#---------------------------------------------------
def mode_change (widget, data=None):
# изменение режима фото/видео
  global mode
  global modeBtn
  global dispBtn
  if dispBtn.get_active():
    dispBtn.set_label("Live view\n     on")
    mode="live"
  else:
    dispBtn.set_label("Live view\n     off")
    mode=""

  if modeBtn.get_active():
    modeBtn.set_label("Video")
    mode=mode+"video"
  else:
    modeBtn.set_label("Foto")
    mode=mode+"foto"
  make_pipe()
#---------------------------------------------------
def make_pipe():
  global screen
  global pipe
  global caps1
  global resizer
  global scalecaps
  global tee
  global queue1
  global sink
  global queue2
  global colorsp
  global caps2
  global fakesink
  global pad
  global record
  global mode
  print (mode)
  #Kill pipeline before create new
  try:
    pipe.set_state(gst.STATE_NULL)
  except AttributeError:
    pass
  pipe=None
  pipe=gst.Pipeline()
  record=False

  if mode=="foto":
    pipe.add(src,caps1,colorsp,caps2,fakesink)
    gst.element_link_many(src,caps1,colorsp,caps2,fakesink)
    pipe.set_state(gst.STATE_PLAYING)
    #gst-launch-0.10 videotestsrc ! video/x-raw-yuv,width=640,height=480,framerate=8/1 ! ffmpegcolorspace ! video/x-raw-rgb,bpp=24,depth=24,framerate=8/1 ! fakesink

  if mode=="livefoto":
    pipe.add(src,caps1,tee,queue1,sink,queue2,colorsp,caps2,fakesink)
    gst.element_link_many(src,caps1,tee,queue1,sink)
    gst.element_link_many(tee,queue2,colorsp,caps2,fakesink)
    pipe.set_state(gst.STATE_PLAYING)
    #gst-launch-0.10 videotestsrc ! tee name=tee tee. ! queue ! xvimagesink tee. ! queue ! ffmpegcolorspace ! video/x-raw-rgb,width=640,height=480,bpp=24,depth=24,framerate=8/1 ! fakesink

  if mode=="video":
    #в режиме video труба создаётся но не стартует до нажатия кнопки
    pipe.add(src,colorsp,caps3,enc,filesink)
    gst.element_link_many(src,colorsp,caps3,enc,filesink)
    pipe.set_state(gst.STATE_NULL)
#gst-launch avimux name=mux ! filesink location=/media/mmc1/camera/videos/video.avi \
#{v4l2src ! video/x-raw-yuv,width=320,height=240,framerate=25/1 \
#! queue ! hantro4200enc profile-and-level=245 bit-rate=512 intra-mode=true \
#! queue ! mux. } { dsppcmsrc ! queue ! mux. }

  if mode=="livevideo":
  #создаем трубу в /dev/null ,при нажатии пишем в файл
    pipe.add(src,caps1,tee,queue1,sink,queue2,colorsp,caps3,enc,filesink)
    gst.element_link_many(src,caps1,tee,queue1,sink)
    gst.element_link_many(tee,queue2,colorsp,caps3,enc,filesink)
    filesink.set_property('location', "/dev/null") 
    pipe.set_state(gst.STATE_PLAYING)

  if mode[0:4]=="live": #put sink picture in its place
    sink.set_xwindow_id(screen.window.xid)
#---------------------------------------------------
def create_interface():
  global screen
  global dispBtn
  global modeBtn
  box=gtk.Fixed()
  window.add(box)
  screen = gtk.DrawingArea()
  screen.set_size_request(640, 480)
  box.put(screen,0,0)
  hbox=gtk.VBox()
  hbox.set_size_request(150, 480)
  box.put(hbox,645,0)

  modeBtn = gtk.ToggleButton("Foto")
  modeBtn.connect("toggled",mode_change)
  hbox.add(modeBtn)

  dispBtn = gtk.ToggleButton("Live view\n   on")
  dispBtn.connect("toggled",mode_change)
  hbox.add(dispBtn)
#---------------------------------------------------
#main program
if hildon:
  window = hildon.Window()
  window.fullscreen()
else:
  window = gtk.Window()
window.connect("destroy", destroy)
window.connect("key_press_event",key_press_cb)
window.connect("key_release_event",key_release_cb)

create_interface() #draw buttons
mode_change(None) #make pipeline

#assign callback function to framebuffer
pad=colorsp.get_pad("src")
pad.add_buffer_probe(buffer_cb)

window.show_all()
gtk.main()
