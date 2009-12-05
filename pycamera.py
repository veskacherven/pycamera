#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import gobject #for idle loop

#Глобальные объекты и переменные
pipe=None
if hildon:
  src = gst.element_factory_make("v4l2src", "src")
else:
  src = gst.element_factory_make("videotestsrc")
caps1=gst.element_factory_make("capsfilter")
caps1.set_property('caps', gst.caps_from_string("video/x-raw-yuv,width=640,height=480,framerate=8/"))
tee=gst.element_factory_make("tee")
queue1= gst.element_factory_make("queue")
sink=gst.element_factory_make("xvimagesink")
queue2= gst.element_factory_make("queue")
colorsp=gst.element_factory_make("ffmpegcolorspace")
caps2=gst.element_factory_make("capsfilter")
caps2.set_property('caps', gst.caps_from_string("video/x-raw-rgb,bpp=24,depth=24,framerate=8/1"))
fakesink = gst.element_factory_make("fakesink")
pad=colorsp.get_pad("src")

mode="foto" # Режим foto,livefoto,video,livevideo,record,liverecord,stream,livestream
#Режимы на live с отображением картинки на экране
ShotPressed=False
#Кнопки
dispBtn=None
modeBtn=None
#Признак того, что кадр в буффере нкжно сохраненить в файл
save=False
#добавить трёхсекундный просмотр картинки после съёмки, если включено Live view
#show_image=False
#Буфер для картинки
picbuf=None
if hildon:
    #Путь для сохранения - вместо жестко прописаного добавить чтение ini файла и создание инишки при отсутствии с парамертами по умолчанию
    picpath="/media/mmc1/camera/images/"
else:
    picpath="./"

#---------------------------------------------------
def save_jpeg():
  global picbuf
  global picpath
  pixbuf=gtk.gdk.pixbuf_new_from_data(picbuf,gtk.gdk.COLORSPACE_RGB,False,8,640,480,3*640)
  filename=picpath+time.strftime("%y.%m.%d_%H-%M-%S", time.localtime())+".jpg"
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
      gobject.idle_add(pause_pipe) #Adds a function to be called whenever there are no higher priority events pending
    return True
#---------------------------------------------------
def pause_pipe():
  print ("pause pipe")
  pipe.set_state(gst.STATE_READY)
  return False #If the function returns FALSE it is automatically removed from the list

def key_press_cb(widget,event):
#При нажатии F6 устанавливаем признак save
  global pipe
  global save
  global ShotPressed
  if event.keyval==gtk.keysyms.F6:
    if ShotPressed==False: #Для избежания автоповтора нажатий
      ShotPressed=True
      if (mode=="foto") or (mode=="livefoto"):
        save=True
        print("save flag set")

  if event.keyval==gtk.keysyms.Escape: #а по ESC выходим
    window.destroy()
#---------------------------------------------------
def key_release_cb(widget,event):
#При отпускании F6 записываем буфер в jpeg
  global pipe
  global ShotPressed
  if event.keyval==gtk.keysyms.F6:
      if (mode=="foto") or (mode=="livefoto"):
        save_jpeg()
        pipe.set_state(gst.STATE_PLAYING)
        print ("resume pipe")
      ShotPressed=False  #снимаем признак нажатия кнопки спуска

#---------------------------------------------------
def expose_cb(widget, event):
  #При перерисовке области screen устанавливаем где будет вывод xvimagesink
  global sink
  if mode[0:4]=="live":
    sink.set_xwindow_id(widget.window.xid)
#---------------------------------------------------
def destroy(widget, data=None):
  # it is important to stop pipeline so there will be no
  # X-related errors when window is destroyed before the video sink
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
    dispBtn.set_label("Live view\n   on")
    mode="live"
  else:
    dispBtn.set_label("Live view\n   off")
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
  global pipe
  global caps1
  global resizer
  global tee
  global queue1
  global sink
  global queue2
  global colorsp
  global caps2
  global tmpcaps
  global fakesink
  global pad

  global mode
  print (mode)
  #Убиваем трубу
  try:
    pipe.set_state(gst.STATE_NULL)
  except AttributeError:
    pass
  pipe=None
  pipe=gst.Pipeline()

#  pad=colorsp.get_pad("src")
#  pad.add_buffer_probe(buffer_cb)

  if mode=="foto":
    pipe.add(src,caps1,colorsp,caps2,fakesink)
    gst.element_link_many(src,caps1,colorsp,caps2,fakesink)
    #gst-launch-0.10 videotestsrc ! video/x-raw-yuv,width=160,height=120,framerate=8/1 ! ffmpegcolorspace ! video/x-raw-rgb,bpp=24,depth=24,framerate=8/1 ! fakesink

  if mode=="livefoto":
    pipe.add(src,caps1,tee,queue1,sink,queue2,colorsp,caps2,fakesink)
    gst.element_link_many(src,caps1,tee,queue1,sink)
    gst.element_link_many(tee,queue2,colorsp,caps2,fakesink)
    #gst-launch-0.10 videotestsrc ! tee name=tee tee. ! queue ! xvimagesink tee. ! queue ! ffmpegcolorspace ! video/x-raw-rgb,width=640,height=480,bpp=24,depth=24,framerate=8/1 ! fakesink

  if mode=="video":
    #в режиме video труба создаётся только непосредственно при записи
    pass

  if mode=="livevideo":
    pipe.add(src,caps1,tee,queue1,sink,queue2,colorsp,caps2,fakesink)
    gst.element_link_many(src,caps1,tee,queue1,sink)
    gst.element_link_many(tee,queue2,colorsp,caps2,fakesink)

  pad.add_buffer_probe(buffer_cb)
  pipe.set_state(gst.STATE_PLAYING)
#---------------------------------------------------
def create_interface():
  global screen
  global dispBtn
  global modeBtn
  box=gtk.Fixed()
  window.add(box)
  screen = gtk.DrawingArea()
  screen.set_size_request(640, 480)
  screen.connect("expose-event",expose_cb)
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
#Основная программа
if hildon:
  window = hildon.Window()
  window.fullscreen()
else:
  window = gtk.Window()
window.connect("destroy", destroy)
window.connect("key_press_event",key_press_cb)
window.connect("key_release_event",key_release_cb)

create_interface()
mode_change(None)
window.show_all()
gtk.main()