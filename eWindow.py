import wx
import threading
import Queue
from time import sleep

class eWindows(threading.Thread):
    _ME = None
    _APP = None
    _WX = None
    _RUNNING = True

    EVT_WINDOW = 1
    EVT_WIDGET_CREATE = 2
        
    class Panel(wx.MDIChildFrame):
        def __init__(self, parent, title, size):
            wx.MDIChildFrame.__init__(self, parent, wx.NewId(), title, size=size)
            self.CreateStatusBar()

    class Frame(wx.MDIParentFrame):
        def __init__(self, title, size):
            wx.MDIParentFrame.__init__(self, None, wx.NewId(), title, size=size)
            self.Bind(wx.EVT_CLOSE, self.OnClose)

        def OnClose(self, e):
            eWindows._RUNNING = False
   
    def __new__(cls, *args, **kwargs):
        if not cls._ME:
            cls._ME = super(eWindows, cls).__new__(cls, *args, **kwargs)
            threading.Thread.__init__(cls._ME)
            cls.app = None

            cls._ME.inQueue = Queue.Queue()
            cls._ME.outQueue = Queue.Queue()
            cls._ME.start()

            # Block until we have an app
            while not cls._APP:
                sleep(0)

        # Block until we have a window
        cls._ME.inQueue.put((cls.EVT_WINDOW,0))
        return cls._ME.outQueue.get(True)

    def run(self):
        eWindows._APP = wx.PySimpleApp(redirect=False)
        eWindows._WX = self.Frame("eVHDL", (1000, 600))
        eWindows._WX.Show(True)
        
        while eWindows._RUNNING: 
            while eWindows._APP.Pending(): 
                eWindows._APP.Dispatch()  

            while not self.inQueue.empty():
                e,arg = self.inQueue.get()

                if e == eWindows.EVT_WINDOW:
                    f = eWindows.Panel(eWindows._WX, "", (670, 300))
                    f.Show(True)                
                    self.outQueue.put(f)
                elif e == eWindows.EVT_WIDGET_CREATE:
                    parent, widget, pos,span = arg
                    w = widget(parent)
                    setattr(parent, "w" + str(widget.__name__), w)
                    parent.sizer.Add(w,pos,span,wx.EXPAND)
                    parent.sizer.Fit(parent)

            eWindows._APP.Yield()
            sleep(0.2)
            eWindows._APP.ProcessIdle()
    
    class WaveViewer:
        class Graph(wx.Panel):
            def __init__(self, parent):
                super(self.__class__, self).__init__(parent, size=(520, 200))
                self.parent = parent
                self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

                self.Bind(wx.EVT_SIZE, self.on_size)
                self.Bind(wx.EVT_PAINT, self.on_paint)
                
            def on_size(self, event):
                event.Skip()
                self.Refresh()

            def on_paint(self, event):
                w, h = self.GetSize()
                w -= 1
                dc = wx.AutoBufferedPaintDC(self)
                dc.SetBackground(wx.Brush(wx.BLUE))
                dc.Clear()
                dc.SetBrush(wx.BLUE_BRUSH)
                dc.SetPen(wx.Pen(wx.WHITE, 1))

                draw = self.parent.obj.Draw
                for watch in draw:
                    points = len(draw[watch])
                    if points <= 1:
                        continue

                    n = self.parent.obj.positions[watch]
                    t0,v0 = draw[watch][0]
                    for i in range(1, points):
                        t1,v1 = draw[watch][i]
                    
                        if t0 != t1 or v0 != v1:
                            h = 30 if v0 == 0 else 10
                            ah = n * 35

                            dc.DrawLine(t0*w/200, h + ah, t1*w/200, h + ah)

                            if v0 != v1:
                                dc.DrawLine(t1*w/200, 30 + ah, t1*w/200, 10 + ah)
                        
                        t0 = t1
                        v0 = v1
        
        def __init__(self, title):
            self.window = eWindows()
            self.queue = Queue.Queue()
            self.labels = {}
            self.positions = {}
            self.Draw = {}

            self.window.SetForegroundColour(wx.BLACK)
            self.window.SetTitle("WaveViewer - " + title)
            self.window.obj = self
            self.window.sizer = wx.GridBagSizer()
            self.window.SetSizerAndFit(self.window.sizer)
            
            eWindows._ME.inQueue.put((eWindows.EVT_WIDGET_CREATE, (self.window, self.Graph,(0,0),(1,1))))           
                    
        def update(self, time, watch):
            for w in watch:
                t,o,x,w = (time,w._o,w._x,w)

                if not w in self.labels:
                    self.labels[w] = t
                    self.Draw[w._port.Name] = []
                    self.positions[w._port.Name] = len(self.positions)
                    # Add label!
                elif self.labels[w] == t:
                    continue

                self.Draw[w._port.Name].append((t, x))

                if hasattr(self.window, "wGraph"):
                    self.window.wGraph.Refresh()
