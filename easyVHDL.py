import importlib
import __main__
import traceback
import sys
import copy
from collections import OrderedDict

from eWindow import *
from eTree import *

IN = 0
OUT = 1
SIGNAL = 2


class Work(object):
    _MODULE = __main__ #importlib.import_module(__name__)
    _ME = None
    _TIME = 0

    class ExprType:
        BIT = 0
        VECTOR = 1
        PORT = 2
        EXPR = 3
        ARCH = 4

    class Watcher(object):
        def __init__(self, default, port):
            self._x = default
            self._o = default
            self._port = port

        @property
        def x(self):
            return self._x

        @x.setter
        def x(self, value):
            self._o = self._x
            self._x = value
            Work()._run_callback(self._port.Name)

    def __new__(cls, *args, **kwargs):
        if not cls._ME:
            cls._ME = super(Work, cls).__new__(cls, *args, **kwargs)
            cls._ME.Entities = {}
            cls._ME._running = False
            cls._ME._run_c = None
            cls._ME._run_watch = None
            cls._ME._run_window = None

        return cls._ME

    def isBit(self, expr):
        return expr == 0 or expr == 1

    def isPort(self, expr):
        return isinstance(expr, Work._Port)

    def isArch(self, expr):
        return isinstance(expr, _ArchMap)
    
    def isValidExpr(self, expr):
        if self.isBit(expr):
            return True

        if isinstance(expr, _BasicGate):
            return True

        if self.isPort(expr):
            return True

        if self.isArch(expr):
            return True

        return False

    def getExprType(self, expr):
        if self.isBit(expr):
            return Work.ExprType.BIT

        if isinstance(expr, _BasicGate):
            return Work.ExprType.EXPR

        if self.isPort(expr):
            return Work.ExprType.PORT

        if self.isArch(expr):
            return Work.ExprType.ARCH

        return None
    
    
    def _NewEntity(self, name):
        if name in self.Entities:
            raise Exception("Component already defined")

        ent = self._Entity(self, name)
        self.Entities[name] = ent
        setattr(Work._MODULE, name, ent)
        return ent


    def _NewArchitecture(self, ent, arch):
        if arch in ent.Architectures:
            raise Exception("Architecture already in component")

        arch = self._Architecture(ent, arch)
        ent.Architectures[arch.name] = arch
        return arch
        

    def __getitem__(self, name):
        if not name in self.Entities:
            raise Exception("Component " + name + " not defined")
        return self.Entities[name]

    def Watch(self, *args):
        self._run_watch = args

    def Run(self, architecture, to):
        if not isinstance(architecture, Work._Architecture):
            raise Exception("Run must be done over a valid architecture")

        if len([port for port,mode in architecture.entity.Modes if mode == IN]) > 0:
            raise Exception("Only a component with no IN ports can be evaluated")

        self._running = True
        Work._TIME = 0
        self._run_c = Component(architecture)
        self._run_window = eWindows.WaveViewer(self._run_c.arch.name)
        
        # We must evaluate the whole sensivity list on 0!
        for port in self._run_c.arch.Sensivity:
            for process in self._run_c.arch.Sensivity[port]:
                process.evaluate(self._run_c)

        self._run_window.update(Work._TIME, self._run_watch[:])
        
        # Evaluate all Timed lists until we reach the end
        for i in range(0, to+1):
            Work._TIME = i
            self._run_c()
            #print "(", self._run_c.arch.a.x, ",",self._run_c.arch.b.x, ",",self._run_c.arch.c.x, ") =", self._run_c.arch.z.x

        # Final waveviewer update
        self._run_window.update(Work._TIME, self._run_watch[:])          

        self._running = False

    def _run_callback(self, port):
        if not self._running:
            return

        if port in self._run_c.arch.Sensivity:
            for process in self._run_c.arch.Sensivity[port]:
                process.evaluate(self._run_c)

        if self._run_c.arch.hasSignal(port):
            signal = getattr(self._run_c.arch, port)
            if signal in self._run_watch:
                self._run_window.update(Work._TIME, [signal])
                        
        
    class _Entity:
        def __init__(self, parent, name):
            self.name = name
            self.Modes = OrderedDict()
            self.Architectures = {}
        
        def Port(self, *args):
            if (type(args) == list or type(args) == tuple ) and (type(args[0]) == tuple or type(args[0]) == list):
                for port in args[0]:
                    self._addPort(port[0], port[1], port[2] if 2 in port else 0)
            elif type(args) == tuple :
                name = args[0]
                mode = args[1]
                default = args[2] if 2 in args else 0

                self._addPort(name, mode, default)
            else:
                raise Exception("Unknown parameters for Port");

            return self

        def _addPort(self, name, mode, default):
            names = name.split(",")
            for name in names:
                if self.hasPort(name):
                    raise Exception("Port is already defined")
                
                self.Modes[name] = mode
                setattr(self, name, default)

                # Set a global variable for that, in case it doesn't exist
                try:
                    port = getattr(Work._MODULE, name)
                    if not isinstance(port, Work._Port):
                        raise Exception("Conflictive name for port `" + name + "`")
                except AttributeError:
                    setattr(Work._MODULE, name, Work._Port(name))
                    pass


        def hasPort(self, port):
            return port in self.Modes

        def portMode(self, port):
            return self.Modes[port]

        def __call__(self, arch, sensivity = {}):
            for port in sensivity:
                None
                    
            

        def __enter__(self):
            return self

        def __exit__(self, e, msg, tb):
            if e:
                sys.stderr.write("Error: " + str(msg) + "\n")
                traceback.print_tb(tb, limit=1, file=sys.stderr)
                return True
            

    class _Port:
        def __init__(self, name):
            self.Name = name


    class _Architecture:
        def __init__(self, entity, name):
            self.name = name
            self.entity = entity
            self.Timed = []
            self.Sensivity = {}
            self.Signals = []
            self.edone = False
            setattr(entity, name, self)

        def hasSignal(self, signal):
            return signal in self.Signals

        def Signal(self, *args):
            if (type(args) == list or type(args) == tuple) and (type(args[0]) == tuple or type(args[0]) == list):
                for signal in args[0]:
                    self._addSignal(signal[0], signal[1] if 1 in signal else 0)
            elif type(args) == tuple :
                name = args[0]
                default = args[1] if 1 in args else 0

                self._addSignal(name, default)
            else:
                raise Exception("Unknown parameters for Signal");

            return self

        def _addSignal(self, name, default):
            names = name.split(",")
            for name in names:
                if self.entity.hasPort(name):
                    raise Exception("A port with the same name already exists")
                
                if self.hasSignal(name):
                    raise Exception("Signal is already defined")
                
                # Set a global variable for that, in case it doesn't exist
                try:
                    signal = getattr(Work._MODULE, name)
                    if not isinstance(signal, Work._Port):
                        raise Exception("Conflictive name for signal `" + name + "`")
                except AttributeError:
                    setattr(Work._MODULE, name, Work._Port(name))
                    pass
                
                self.Signals.append(name)
                setattr(self, name, Work.Watcher(default, getattr(Work._MODULE, name)))

        class _Process:
            def __init__(self, arch, sensivity):
                self.arch = arch
                self.events = {}
                self.cur = 0
                self.sensivity = sensivity
        
            def _isValidPort(self, port):
                if not self.arch.entity.hasPort(port):
                    raise Exception("Port or Signal `" + port + "` not found on `" + self.arch.entity.name + "`")

                if self.arch.entity.portMode(port) == OUT:
                    raise Exception("Can not use OUT port as input")


            def _doExprCheck(self, root):
                if root.left:
                    self._doExprCheck(root.left)
                if root.right:
                    self._doExprCheck(root.right)

                etype = Work().getExprType(root.data)
                if etype == Work.ExprType.PORT:
                    self._isValidPort(root.data.Name)


            def wait(self, time):
                if self.sensivity:
                    raise Exception("Can not `wait` on a sensivity process")
                self.cur += time
        

            def __call__(self, port, expr, options = {}):
                if type(options) != dict:
                    raise Exception("Options are not well formatted")

                port = port.Name
                if not self.arch.entity.hasPort(port) and not self.arch.hasSignal(port):
                    raise Exception("Port or Signal `" + port + "` not found on `" + self.arch.entity.name + "`")

                # If it is a port, it mustn't be IN
                if self.arch.entity.hasPort(port) and self.arch.entity.portMode(port) == IN:
                    raise Exception("Can not modify an IN Port")
                
                # Check if the expr is valid
                if not Work().isValidExpr(expr):
                    raise Exception("Expression not valid")

                etype = Work().getExprType(expr)
                if etype == Work.ExprType.PORT:
                    self._isValidPort(expr.Name)
                elif etype == Work.ExprType.EXPR:
                    self._doExprCheck(expr.Tree)
                # BITs and ARCHs are already checked                
                    
                # Everything was correct, we can add it
                at = self.cur
                if "after" in options:
                    at += options["after"]
                
                if not at in self.events:
                    self.events[at] = []
                self.events[at].append((port, expr))

                return self

            def evaluate(self, component):
                if not isinstance(component, Component):
                    raise Exception("A component must be used to evaluate an architecture")

                if not self.sensivity:
                    if not Work()._TIME in self.events:
                        return

                    events = self.events[Work()._TIME]
                else:
                    events = self.events[0]
    
                for f,e in events:
                    self.evaluate_i(component, f, e)

            def evaluate_i(self, component, f, e):
                ret = self._evaluate_i(component, e)
                if self.arch.hasSignal(f):
                    signal = getattr(self.arch, f)
                    signal.x = ret
                else:
                    setattr(component, f, ret)


            def _evaluate_i(self, component, event):
                etype = Work().getExprType(event)
                if etype == Work.ExprType.BIT:
                    return event
                elif etype == Work.ExprType.ARCH:
                    return event(component)
                elif etype == Work.ExprType.EXPR:
                    gate = event.Tree
                elif isinstance(event, CNode):
                    gate = event
                else:
                    print "TYPE:",etype, event
                    return 0
                
                left = 0
                right = 0

                if gate.left: left = self._evaluate_i(component, gate.left)
                if gate.right: right = self._evaluate_i(component, gate.right)

                gtype = Work().getExprType(gate.data)
                if gtype == Work.ExprType.EXPR:
                    return gate.data(left, right)
                elif gtype == Work.ExprType.PORT:
                    return getattr(component, gate.data.Name)
                else:
                    return gate.data


            def __enter__(self, *args):
                return self

            def __exit__(self, e, msg, tb):
                if e:
                    sys.stderr.write("Error: " + str(msg) + "\n")
                    traceback.print_tb(tb, limit=1, file=sys.stderr)
                    self.arch.edone = True
                    return False


        def Process(self, sensivity=()):
            if type(sensivity) != tuple and type(sensivity) != list:
                raise Exception("Malformed sensivity list")

            p = self._Process(self, bool(sensivity))
            
            if sensivity:
                for port in sensivity:
                    if not Work().isPort(port):
                        raise Exception("Sensivity list port expected")

                    if not self.hasSignal(port.Name) and not self.entity.hasPort(port.Name):
                        raise Exception("Port or Signal `" + port.Name + "` not found on `" + self.entity.name + "`")
                    
                    if not port.Name in self.Sensivity:
                        self.Sensivity[port.Name] = []
                    self.Sensivity[port.Name].append(p)
            else:
                self.Timed.append(p)

            return p

        def __call__(self, component, *args):
            if args and type(args[0]) == dict:
                sensivity = args[0]
            elif args:
                sensivity = {}
                i = 0
                for port,mode in self.entity.Modes.items():
                    if mode == IN:
                        sensivity[getattr(Work()._MODULE, port)] = args[i]
                        i += 1
                        if i >= len(args):
                            break
 
            for port in sensivity:
                value = sensivity[port]
                    
                # IS PORT COMPROBATION            
                setattr(component, port.Name, value)
                if port.Name in self.Sensivity:
                    for process in self.Sensivity[port.Name]:
                        process.evaluate(component)

            for process in self.Timed:
                process.evaluate(component)

            return self
    
        def __enter__(self, *args):
            return self

        def __exit__(self, e, msg, tb):
            if self.edone:
                return True
            
            if e:
                sys.stderr.write("Error: " + str(msg) + "\n")
                traceback.print_tb(tb, limit=1, file=sys.stderr)
                return True
            

class Entity(object):
    def __new__(cls, name):
        return Work()._NewEntity(name)
        

class Architecture(object):
    def __new__(cls, entity, name):
        return Work()._NewArchitecture(entity, name)


class Component(object):
    def __init__(self, architecture):
        if not isinstance(architecture, Work._Architecture):
            raise Exception("Invalid architecture")

        self.entity = architecture.entity
        self.arch = architecture
        self.archmap = None

        for port in self.entity.Modes:
            setattr(self, port, getattr(self.entity, port))

    def archCall(self, *args):
        for arg in args:
            atype = Work().getExprType(arg)
            if atype != Work.ExprType.PORT and atype != Work.ExprType.ARCH:
                raise Exception("Only Ports or Architectures may be passed to components")
                
        ports = self._sensivityFromArgs(*args)
        self.archmap.setPorts(ports)

        for port in ports:
            if not Work().isBit(ports[port]):
                return self.archmap

        self.arch(self, ports)
        
        return getattr(self, self.archmap.out)

    def __getattribute__(self, key):
        # When runing, we want the int value, not the architecture binding!
        if Work()._running:
            return object.__getattribute__(self, key)
        
        try:
            port = object.__getattribute__(self, key)
            entity = object.__getattribute__(self, "entity")
            archCall = object.__getattribute__(self, "archCall")

            if entity.hasPort(key):
                if entity.portMode(key) == OUT:
                    self.archmap = _ArchMap(self, key)
                    return archCall
            
            return port
                
        except AttributeError as e:
            raise Exception("Port " + key + " not found")

    def __call__(self, *args):        
        ports = self._sensivityFromArgs(*args)

        for port in ports:
            if not Work().isBit(ports[port]):
                raise Exception("Direct call must be done with bits only")

        self.arch(self, ports)
        
        return self

    def _sensivityFromArgs(self, *args):
        if not args:
            ports = ()
        else:
            if type(args[0]) == dict:
                ports = args[0]
            else:
                ports = {}
                i = 0
                for port,mode in self.entity.Modes.items():
                    if mode == IN:
                        ports[getattr(Work()._MODULE, port)] = args[i]
                        i += 1
                        if i >= len(args):
                            break

        if len(ports) < len([port for port,mode in self.entity.Modes.items() if mode == IN]):
            raise Exception("Not all IN ports have a valid entry")
        
        return ports

class _ArchMap:
    def __init__(self, component, out):
        self.component = component
        self.sensivity = None
        self.out = out

    def setPorts(self, ports):
        self.sensivity = ports

    def __call__(self, expr0=None, expr1=None):
        for port in self.sensivity:
            value = self.sensivity[port]
            ptype = Work().getExprType(value)
            if ptype == Work.ExprType.PORT:
                if not isinstance(expr0, Component):
                    raise Exception("Can not call a component architecture by an out port without using a valid component")

                if expr0.arch.hasSignal(value.Name):
                    signal = getattr(expr0.arch, value.Name)
                    setattr(self.component, port.Name, signal.x)
                else:
                    setattr(self.component, port.Name, getattr(expr0, value.Name))

            elif ptype == Work.ExprType.ARCH:
                if not isinstance(expr0, Component):
                    raise Exception("Can not call a component architecture by an out port without using a valid component")

                value(expr0)
                archres = getattr(value.component, value.out)
                setattr(self.component, port.Name, archres)

        for port in self.sensivity:
            value = self.sensivity[port]
            
            if port.Name in self.component.arch.Sensivity:
                for process in self.component.arch.Sensivity[port.Name]:
                    process.evaluate(self.component)

        ret = getattr(self.component, self.out)
        return ret


class _BasicGate(object):
    def __init__(self, gate, expr0, expr1 = None):
        self.Gate = gate
        tree = CBOrdTree()
        self.Tree = tree.insert(None, self)
        
        if not Work().isValidExpr(expr0):
            raise Exception(str(expr0) + " is not a valid expression")
            
        if isinstance(expr0, _BasicGate):
            tree.insertTree(self.Tree, expr0.Tree)
        else:
            tree.insert(self.Tree, expr0)

        if expr1:
            if not Work().isValidExpr(expr1):
                raise Exception(str(expr1) + " is not a valid expression")
        
            if isinstance(expr1, _BasicGate):
                tree.insertTree(self.Tree, expr1.Tree)
            else:           
                tree.insert(self.Tree, expr1)

    
class NOT(_BasicGate):
    def __init__(self, expr):
        super(self.__class__, self).__init__("NOT", expr)
    def __call__(self, expr0, expr1):
        return int(not expr0)
    
class AND(_BasicGate):
    def __init__(self, expr0, expr1):
        super(self.__class__, self).__init__("AND", expr0, expr1)
    def __call__(self, expr0, expr1):
        return expr0 & expr1
    
class OR(_BasicGate):
    def __init__(self, expr0, expr1):
        super(self.__class__, self).__init__("OR", expr0, expr1)
    def __call__(self, expr0, expr1):
        return expr0 | expr1        
    
class XOR(_BasicGate):
    def __init__(self, expr0, expr1):
        super(self.__class__, self).__init__("XOR", expr0, expr1)
    def __call__(self, expr0, expr1):
        return expr0 ^ expr1
                        

