import importlib
import traceback
import sys
from collections import OrderedDict

IN = 0
OUT = 1
SIGNAL = 2

class CNode:
    left , right, data = None, None, 0
    
    def __init__(self, data):
        # initializes the data members
        self.left = None
        self.right = None
        self.data = data


class CBOrdTree:
    def __init__(self):
        # initializes the root member
        self.root = None
    
    def addNode(self, data):
        # creates a new node and returns it
        return CNode(data)

    def insert(self, root, data):
        # inserts a new data
        if root == None:
            # it there isn't any data
            # adds it and returns
            return self.addNode(data)
        else:
            # enters into the tree
            if not root.left:
                # if the data is less than the stored one
                # goes into the left-sub-tree
                root.left = self.insert(root.left, data)
            else:
                # processes the right-sub-tree
                root.right = self.insert(root.right, data)
            return root

    def insertTree(self, root, node):
        if not root.left:
            root.left = node
        else:
            root.right = node
        return root


class Work(object):
    _MODULE = importlib.import_module(__name__)
    _ME = None
    _TIME = 0

    class ExprType:
        BIT = 0
        VECTOR = 1
        PORT = 2
        EXPR = 3
        ARCH = 4

    def __new__(cls, *args, **kwargs):
        if not cls._ME:
            cls._ME = super(Work, cls).__new__(cls, *args, **kwargs)
            cls._ME.Entities = {}

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
            self.edone = False
            setattr(entity, name, self)

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
                if not self.arch.entity.hasPort(port):
                    raise Exception("Port or Signal `" + port + "` not found on `" + self.arch.entity.name + "`")

                if self.arch.entity.portMode(port) == IN:
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
                
                events = self.events[Work()._TIME]
                for f,e in events:
                    self.evaluate_i(component, f, e)

            def evaluate_i(self, component, f, e):
                setattr(component, f, self._evaluate_i(component, e))


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
                return False
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

                    if not self.entity.hasPort(port.Name):
                        raise Exception("Port or Signal `" + port.Name + "` not found on `" + self.entity.name + "`")
                    
                    if not port.Name in self.Sensivity:
                        self.Sensivity[port.Name] = []
                    self.Sensivity[port.Name].append(p)
            else:
                self.Timed.append(p)

            return p

        def __call__(self, component, *args):
            if type(args[0]) == dict:
                sensivity = args[0]
            else:
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

            return self
    
        def __enter__(self, *args):
            return self

        def __exit__(self, e, msg, tb):
            return False
        
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
        self.lock = False

        for port in self.entity.Modes:
            if self.entity.portMode(port) != OUT:
                setattr(self, port, getattr(self.entity, port))
            else:
                setattr(self, port, self.archCall)

    def archCall(self, *args):
        ports = self._sensivityFromArgs(*args)
        self.archmap.setPorts(ports)

        for port in ports:
            if not Work().isBit(ports[port]):
                return self.archmap

        self.lock = True
        self.arch(self, ports)
        self.lock = False
        
        return getattr(self, self.archmap.out)

    def __getattribute__(self, key):
        lock = object.__getattribute__(self, "lock")
        if lock:
            return object.__getattribute__(self, key)
        
        try:
            port = object.__getattribute__(self, key)
            entity = object.__getattribute__(self, "entity")

            if entity.hasPort(key):
                #if entity.portMode(key) != OUT:
                    #raise Exception("Port " + key + " is not OUT")
                #else:
                if entity.portMode(key) == OUT:
                    self.archmap = _ArchMap(self, key)
            
            return port
                
        except AttributeError as e:
            raise Exception("Port " + key + " not found")

    def __call__(self, *args):        
        ports = self._sensivityFromArgs(*args)

        for port in ports:
            if not Work().isBit(ports[port]):
                raise Exception("Direct call must be done with bits only")

        self.lock = True
        self.arch(self, ports)
        self.lock = False
        
        return self

    def _sensivityFromArgs(self, *args):
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
        self.component.lock = True

        for port in self.sensivity:
            value = self.sensivity[port]

            ptype = Work().getExprType(value)
            if ptype == Work.ExprType.PORT:
                if not isinstance(expr0, Component):
                    raise Exception("Can not call a component architecture by an out port without using a valid component")
                
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

        self.component.lock = False
        return getattr(self.component, self.out)


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

    """
    def __call__(self, expr0, expr1=None):
        if expr1 == None:
            self.__init__(expr0)
        else:
            self.__init__(expr0, expr1)
        return self
    
    def __getattribute__(self, key):
        try:
            return object.__getattribute__(self, key)
        except AttributeError as e:
            try:
                c = getattr(Work._MODULE, key)
                c = c.__new__(c)
                c.trees = self.trees
                return c
            except AttributeError:
                raise Exception("Gate " + key + " does not exist")
    """
    
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
                        
def test():
    # Entity declaration, best way
    with Entity("INV"):
        # Assignin ports to the entity (ORDER MATTERS!, a b z != b a z)
        INV.Port([
            ["a", IN],
            ["z", OUT]
        ])
        
    with Entity("AND2"):
        AND2.Port([
            ["b", IN],
            ["a", IN],
            ["z", OUT]
        ])
     
    with Entity("NAND2"):
        NAND2.Port([
            ["a", IN],
            ["b", IN],
            ["z", OUT]
        ])
        
    with Entity("OR2"):
        OR2.Port([
            ["a", IN],
            ["b", IN],
            ["z", OUT]
        ])
     
    with Entity("NOR2"):
        NOR2.Port([
            ["a", IN],
            ["b", IN],
            ["z", OUT]
        ])
        
    with Entity("OR3"):
        OR3.Port([
            ["a", IN],
            ["b", IN],
            ["c", IN],
            ["z", OUT]
        ])

    Entity("Testbench")

    # Architecture declaration
    # We can assign it a variable, `logic`, or access it through `AND2.logic`
    with Architecture(INV, "logic") as logic:
        with logic.Process((a,)) as process:
            process(z, NOT(a))
            
    with Architecture(AND2, "logic") as logic:
        with logic.Process((a,b)) as process:
            process(z, AND(a, b))

    with Architecture(NAND2, "logic") as logic:
        cINV = Component(INV.logic)
        cAND2 = Component(AND2.logic)
        with logic.Process((a,b)) as process:
            process(z, cINV.z(cAND2.z(a, b)))
            
    with Architecture(OR2, "logic") as logic:
        with logic.Process((a,b)) as process:
            process(z, OR(a, b))

    with Architecture(NOR2, "logic") as logic:
        cINV = Component(INV.logic)
        cOR2 = Component(OR2.logic)
        with logic.Process((a,b)) as process:
            process(z, cINV.z(cOR2.z(a, b)))
            
    with Architecture(OR3, "logic") as logic:
        with logic.Process((a,b,c)) as process:
            process(z, OR(OR(a, b), c))

    with Architecture(Testbench, "test") as test:
        with test.Process() as process:
            process(a, 


    # Crida directa, evalua totes les sortides
    # Els valors (0, 1) s'associen a les entrades tal i com les hem declarat i
    # en el mateix ordre
    cNOR2 = Component(NOR2.logic)
    print cNOR2(0,1), cNOR2.z

    # Crida a la sortida z, retorna el valor directament
    cNAND2 = Component(NAND2.logic)
    print cNAND2.z(1,0)
    
    cOR3 = Component(OR3.logic)
    print cOR3.z(1,0,0)

    # Crida directa a la sortida indicant explicitament el valor de cada entrada
    cOR3 = Component(OR3.logic)
    print cOR3.z({a: 0, b:0, c:0})

test()
