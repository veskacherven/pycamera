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
#Глобальные объекты и переменные
current_pipe=None
foto_pipe=None
live_foto_pipe=None
video_pipe=None
live_video_pipe=None
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

sink1=None #xvimagesink для вывода картинки

def save_jpeg():
  global picbuf
  global picpath
  pixbuf=gtk.gdk.pixbuf_new_from_data(picbuf,gtk.gdk.COLORSPACE_RGB,False,8,640,480,3*640)
  filename=picpath+time.strftime("%y.%m.%d_%H-%M-%S", time.localtime())+".jpg"
  pixbuf.save(filename,"jpeg",{"quality":"100"})
  print (filename)

def buffer_cb(pad,buffer):
#Если установлен признак save сохраняем буфер кадра в picbuf
    global save
    global picbuf
    if save==True:
      save=False
      picbuf=buffer
    return True

def key_press_cb(widget,event):
#При нажатии F6 устанавливаем признак save
    global save
    if event.keyval==gtk.keysyms.F6:
        save=True
    if event.keyval==gtk.keysyms.Escape: #а по ESC выходим
        window.destroy()

def key_release_cb(widget,event):
#При отпускании F6 записываем буфер в jpeg
    if event.keyval==gtk.keysyms.F6:
        save_jpeg()

def expose_cb(widget, event):
    #При перерисовке области screen устанавливаем где будет вывод xvimagesink
    sink1.set_xwindow_id(widget.window.xid)

def destroy(widget, data=None):
  # it is important to stop pipeline so there will be no
  # X-related errors when window is destroyed before the video sink
  global current_pipe
  current_pipe.set_state(gst.STATE_NULL)
  gtk.main_quit()

def mode_change (widget, data=None):
# изменение режима фото/видео
#    pipeline.set_state(gst.STATE_NULL)
    if modeBtn.get_active():
      modeBtn.set_label("Video")
    else:
      modeBtn.set_label("Foto")

def disp_change (widget, data=None): 
# изменение отображения live view
    if dispBtn.get_active():
      dispBtn.set_label("Live view\n   off")
#      make_foto_pipe()  #Труба для фото
    else:
      dispBtn.set_label("Live view\n   on")
#      make_live_foto_pipe()  #Труба для фото c предпросмотром

def make_live_foto_pipe():
  global sink1
  global live_foto_pipe
  global current_pipe
  live_foto_pipe=gst.Pipeline()
  src = gst.element_factory_make("videotestsrc", "src")
  #src = gst.element_factory_make("v4l2src", "src")
  tee=gst.element_factory_make("tee", "tee")
  queue1= gst.element_factory_make("queue", "queue1")
  resizer = gst.element_factory_make("videoscale", "resizer")
  caps1=gst.element_factory_make("capsfilter", "caps1")
  caps1.set_property('caps', gst.caps_from_string("video/x-raw-yuv,width=160,height=120"))
  sink1=gst.element_factory_make("xvimagesink", "sink")
  queue2= gst.element_factory_make("queue", "queue2")
  colorsp=gst.element_factory_make("ffmpegcolorspace", "colorsp1")
  caps2=gst.element_factory_make("capsfilter", "caps2")
  caps2.set_property('caps', gst.caps_from_string("video/x-raw-rgb,width=640,height=480,bpp=24,depth=24,framerate=8/1"))
  sink2 = gst.element_factory_make("fakesink", "sink2")
  pad=colorsp.get_pad("src")
  pad.add_buffer_probe(buffer_cb)
  live_foto_pipe.add(src,tee,queue1,resizer,caps1,sink1,queue2,colorsp,caps2,sink2)
  gst.element_link_many(src,tee,queue1,resizer,caps1,sink1)
  gst.element_link_many(tee,queue2,colorsp,caps2,sink2)
  current_pipe=live_foto_pipe
  current_pipe.set_state(gst.STATE_PLAYING)

def make_foto_pipe():
  global sink1
  foto_pipeline = gst.Pipeline()
  #pipeline.set_state(gst.STATE_NULL)
  src = gst.element_factory_make("videotestsrc", "src")
  #src = gst.element_factory_make("v4l2src", "src")
  colorsp=gst.element_factory_make("ffmpegcolorspace", "colorsp1")
  caps2=gst.element_factory_make("capsfilter", "caps2")
  caps2.set_property('caps', gst.caps_from_string("video/x-raw-rgb,width=640,height=480,bpp=24,depth=24,framerate=8/1"))
  sink2 = gst.element_factory_make("fakesink", "sink2")
  pad=colorsp.get_pad("src")
  pad.add_buffer_probe(buffer_cb)
  foto_pipeline.add(src,colorsp,caps2,sink2)
  gst.element_link_many(src,colorsp,caps2,sink2)
  pipeline.set_state(gst.STATE_PLAYING)

def create_interface():
  global screen
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
  dispBtn.connect("toggled",disp_change)
  hbox.add(dispBtn)

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
make_live_foto_pipe()  #Труба для фото
window.show_all()
gtk.main()