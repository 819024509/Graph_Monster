from ttkbootstrap import Window, Frame, Button, \
                        Text, Label, Labelframe, \
                        Canvas, Toplevel, Entry, \
                        StringVar, Menu, Style, \
                        IntVar, DoubleVar, Notebook, \
                        Panedwindow, Checkbutton
from tkinter.filedialog import askopenfile, asksaveasfile
from ttkbootstrap.dialogs.dialogs import Messagebox
from math import atan2, atan, cos, sin
from pickle import dump, load
from functools import partial
from copy import deepcopy
import time


class Node:

    def __init__(self, val, canvasIds=[], scale=1):
        self.val = val
        # 2 elements: widget id and its label id
        self.canvasIds = canvasIds if canvasIds else []
        self.scale = scale
        self.adjLines = set()
        self.v = [0, 0]
        self.a = [0, 0]

    def __eq__(self, other):
        return isinstance(other, Node) and self.val == other.val

    def __str__(self):
        return str(self.val)


class Line:

    def __init__(self, node1, node2, weight=1, canvasIds=[]):
        if isinstance(node1, Node) and isinstance(node2, Node):
            self.node1 = node1
            self.node2 = node2
            self.weight = weight
            self.canvasIds = canvasIds
        else:
            raise TypeError("Error in Node type")

    def __eq__(self, other):
        return self.node1 == other.node1 and self.node2 == other.node2

    def getView(self):
        return (self.node1.val, self.node2.val, self.weight)

    def __str__(self):
        return str(self.getView())


class GraphMonster:
    """
    New features:
        1. It is able to track the graph now. You may use Ctrl-Z/Y to cancel/redo changes.
        2. The customized output style can be exported and imported now.
        3. You can go back to default customized output style with one click on the menubar.
    Undesirable "feature":
        1. Once scaled, the canvas will be falsely treated as a new graph even w/o other changes.
    Possible solution:
        Build a finer logging mechanism to exactly trace every operation
            (e.g., ["move"/"add"/"delete"/"import"] [nodeObj/lineObj/graph] [oldCoordinate] [newCoordinate]),
            and then build a redo mechanism to restore any changes indicated by the log entry.
    """

    def __init__(self):
        self.mainWin = Window()
        self.mainWin.geometry("1550x900+200+50")
        self.mainWin.title("Graph Monster")

        self.NODENEIGHBORTOLERANCE = 5
        self.EMPTY = -1e9
        self.OUTPUTSTYLES = (" List ", " Line ", "Customized Style")
        self.THEMENAME = ("minty", "darkly", "solar", "cyborg")
        self.COLORBOOK = {
            "oval": ("#E4E4E4", "grey", "#3f98d7", "#555555"),
            "line": ("#17A2B8", "#FF7851", "#d95092", "#77b300"),
            "text": ("black", "#32fbe2", "white", "white"),
        }
        '''
        {type: (color, )}
        '''
        self.LINETAGOFFSET = 10
        self.SCALERATIO = 1.3
        self.NODEWIDTH = 2
        self.NODESIZE = 20
        self.LINEWIDTH = 3
        self.CANVASUPDATEGAP = 1 / 120
        self.curTheme = IntVar(value=1)
        self.damping = DoubleVar(value=.1)
        self.nodeMass = IntVar(value=15)
        self.elasticity = DoubleVar(value=1)
        self.customNodeMode = IntVar(value=1)
        self.customLineMode = IntVar(value=1)
        self.idealEdgeLen = IntVar(value=300)
        self.repelFactor = DoubleVar(value=40)
        self.repelThreshold = DoubleVar(value=200.0)
        self.formatStatus = StringVar(value="Ready")
        self.reformatState = StringVar(value="Activate")
        self.curScale = 1
        self.incre_idx = -1
        self.startNode = self.EMPTY
        self.motionTolerance = 1e-4
        self.lineStartNode = self.EMPTY
        self.graphHistory = []
        self.historyIdx = -1
        self.defaultOutputStyle = {
            "Node": {
                "unit": "label",
                "list": ["[", "]"],
                "sep": ", "
            },
            "Line": {
                "unit": "(node1, node2, weight)",
                "list": ["[", "]"],
                "sep": ", "
            },
        }
        self.curOutputStyle = deepcopy(self.defaultOutputStyle)
        self.ouputData = {
            "Node": [
                StringVar(value="label"),
                StringVar(value="["),
                StringVar(value="]"),
                StringVar(value=", ")
            ],
            "Line": [
                StringVar(value="(node1, node2, weight)"),
                StringVar(value="["),
                StringVar(value="]"),
                StringVar(value=", ")
            ],
        }
        self.data = {"Node": {}, "Line": {}}
        """
        self.data = {
            "Node": {
                tag: Node(Label, [canvasIds], scale)\n
                the node centered at ((x1 + x2) / 2, (y1 + y2) / 2)
                has the label "Label" and has been scaled by "scale"
            }
            "Line": {
                tag: Line(Node_1, Node_2, weight=1, [canvasIds])\n
                the edge from "node_1" to "node_2" has weight "weight"
            }
        }
        """

        menubar = Menu(self.mainWin)
        menu = Menu(menubar, tearoff=0)
        menu2 = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="System", menu=menu)
        menu.add_command(label="Guide", command=self.explain)
        menu.add_separator()
        menu.add_command(label="Export Graph", command=self.exportGraph)
        menu.add_command(label="Import Graph", command=self.importGraph)
        menubar.add_cascade(label="Theme", menu=menu2)
        for i, theme in enumerate(self.THEMENAME):
            menu2.add_radiobutton(
                label=theme,
                value=i,
                command=self.toggleTheme,
                variable=self.curTheme,
            )
        menubar.add_command(label="Graph Reformatter", command=self.reformatUI)
        menubar.add_command(label="Output Customizer",
                            command=self.outputCustomUI)
        self.mainWin.config(menu=menubar)

        self.functionPanel = Frame(self.mainWin, padding=30)
        self.canvasPanel = Labelframe(self.mainWin, text="Canvas", padding=10)
        self.functionPanel.grid(row=0, column=0, sticky="NWS")
        self.canvasPanel.grid(row=0, column=1, sticky="NWES", pady=(30, 50))

        self.btnPanel = Labelframe(self.functionPanel, text="Pen", padding=10)
        self.outputPanel = Labelframe(
            self.functionPanel,
            text="Graph Outputs",
            padding=10,
        )
        self.btnPanel.grid(row=0, column=0, sticky="NWE")
        self.outputPanel.grid(row=1, column=0, sticky="NWE", pady=20)

        self.STATE_NODE = 10001
        self.STATE_LINE = 10002
        self.STATE_DRAG = 10003
        self.NodeBtn = Button(
            self.btnPanel,
            text="O (Node)",
            command=partial(self.handleStateChange, self.STATE_NODE),
            width=25,
        )
        self.lineBtn = Button(
            self.btnPanel,
            text="→   (Line)",
            command=partial(self.handleStateChange, self.STATE_LINE),
            width=25,
        )
        self.dragBtn = Button(
            self.btnPanel,
            text="🤏 (Drag)",
            command=partial(self.handleStateChange, self.STATE_DRAG),
            state="disabled",
            width=25,
        )
        self.NodeBtn.grid(row=0, column=0, sticky="NWE")
        self.lineBtn.grid(row=1, column=0, sticky="NWE")
        self.dragBtn.grid(row=2, column=0, sticky="NWE")
        self.stateToWidget = {
            self.STATE_NODE: self.NodeBtn,
            self.STATE_LINE: self.lineBtn,
            self.STATE_DRAG: self.dragBtn,
        }

        panedWindow = Panedwindow(self.outputPanel,
                                  orient="vertical",
                                  height=625)
        panedWindow.grid(row=0, column=0, sticky="NWES")
        nodeFrame = Frame(panedWindow)
        nodeFrame.pack(side="top", expand=1, fill="both")
        edgeFrame = Frame(panedWindow)
        edgeFrame.pack(side="bottom", expand=1, fill="both")
        panedWindow.add(nodeFrame)
        panedWindow.add(edgeFrame)
        Label(
            nodeFrame,
            text="Nodes",
        ).pack(side="top", pady=(0, 3))
        Label(
            edgeFrame,
            text="Edges",
        ).pack(side="top", pady=(5, 0))
        nodeNb = Notebook(nodeFrame)
        nodeNb.pack(side="top", expand=1, fill="both")
        edgeNb = Notebook(edgeFrame)
        edgeNb.pack(side="top", expand=1, fill="both")

        nodetmpFrames = [Frame(nodeNb) for _ in range(3)]
        edgetmpFrames = [Frame(edgeNb) for _ in range(3)]

        for i, frame in enumerate(nodetmpFrames):
            frame.pack(side="top", fill="both", expand=1)
            nodeNb.add(frame, text=self.OUTPUTSTYLES[i])
        for i, frame in enumerate(edgetmpFrames):
            frame.pack(side="bottom", fill="both", expand=1)
            edgeNb.add(frame, text=self.OUTPUTSTYLES[i])

        self.nodeEntrys = [
            Text(nodetmpFrames[i], width=21, height=2) for i in range(3)
        ]
        self.edgeEntrys = [
            Text(edgetmpFrames[i], width=21, height=5) for i in range(3)
        ]

        for i, entry in enumerate(self.nodeEntrys):
            entry.pack(side="top", fill="both", expand=1)

        for i, entry in enumerate(self.edgeEntrys):
            entry.pack(side="bottom", fill="both", expand=1)

        Button(
            nodeFrame,
            text="Reset Labels",
            width=25,
            command=self.resetLabel,
        ).pack(side="bottom", pady=10)

        self.canvas = Canvas(
            self.canvasPanel,
            width=1150,
            height=790,
            bg="red",
        )

        self.canvas.grid(row=0, column=0, sticky="SNWE")
        self.canvas.bind("<ButtonPress-1>", self.handleLeftClick)
        self.canvas.bind("<ButtonPress-2>", self.handleMidClick)
        self.canvas.bind("<ButtonPress-3>", self.handlerightClick)
        self.canvas.bind("<MouseWheel>", self.handleWheel)
        self.canvas.bind("<B1-Motion>", self.handleMove)
        self.canvas.bind("<Motion>", self.handleMotion)

        self.mainWin.bind(
            "<Control-q>",
            partial(self.handleStateChange, self.STATE_NODE),
        )
        self.mainWin.bind(
            "<Control-w>",
            partial(self.handleStateChange, self.STATE_LINE),
        )
        self.mainWin.bind(
            "<Control-e>",
            partial(self.handleStateChange, self.STATE_DRAG),
        )
        self.mainWin.bind("<Control-z>", self.popCurData)
        self.mainWin.bind("<Control-y>", self.redoCurData)

        self.handleStateChange(self.STATE_NODE)
        self.toggleTheme()
        self.updateOutPut()
        self.pushCurData()
        self.mainWin.mainloop()

    def pushCurData(self, event=None):
        data = self.encodeData()
        if not self.graphHistory or self.graphHistory[self.historyIdx] != data:
            self.historyIdx += 1
            if len(self.graphHistory) == self.historyIdx:
                self.graphHistory.append(None)
            self.graphHistory[self.historyIdx] = (data, self.curScale)

    def popCurData(self, event):
        if self.historyIdx:
            self.historyIdx -= 1
            data, scale = self.graphHistory[self.historyIdx]
            self.deployData(data)
            self.curScale = scale

    def redoCurData(self, event):
        if len(self.graphHistory) - 1 > self.historyIdx:
            self.historyIdx += 1
            data, scale = self.graphHistory[self.historyIdx]
            self.deployData(data)
            self.curScale = scale

    def toggleTheme(self):
        themeIdx = self.curTheme.get()
        Style(self.THEMENAME[themeIdx])
        for tag in self.canvas.find_all():
            thisType = self.canvas.type(tag)
            self.canvas.itemconfigure(
                tag,
                fill=self.COLORBOOK[thisType][themeIdx],
            )

    def encodeData(self):
        compressedData = {"Node": {}, "Line": [], "curId": self.incre_idx}
        for idx in self.canvas.find_all():
            thisType = self.canvas.type(idx)
            if thisType == "oval":
                compressedData["Node"][tuple(self.canvas.coords(idx))] = \
                    deepcopy(self.data["Node"][idx])
            elif thisType == "line":
                compressedData["Line"].append(deepcopy(self.data["Line"][idx]))
        return compressedData

    def deployData(self, data):
        # Erase previous data
        self.canvas.delete("all")
        self.data = {"Node": {}, "Line": {}}
        # Parse and load data
        self.incre_idx = data["curId"]
        nodeValToObj = {}
        scale = 1
        for coord, node in data["Node"].items():
            scale = node.scale
            nodeId = self.drawNode(*coord)
            textId = self.drawText(
                *self.getCenter(coord),
                mode=0,
                text=str(node.val),
            )
            node.canvasIds = [nodeId, textId]
            node.adjLines = set()
            self.data["Node"][nodeId] = node
            nodeValToObj[node.val] = node
        self.curScale = scale
        for line in data["Line"]:
            line.node1 = nodeValToObj[line.node1.val]
            line.node2 = nodeValToObj[line.node2.val]
            lineCoord = self.getLineCoords(line.node1, line.node2)
            textCoord = self.linearComb(*lineCoord)
            lineId = self.drawLine(*lineCoord)
            textId = self.drawText(*textCoord, 1, str(line.weight))
            line.node1.adjLines.add(lineId)
            line.node2.adjLines.add(lineId)
            line.canvasIds = [lineId, textId]
            self.data["Line"][lineId] = line
        self.updateOutPut()

    def exportGraph(self):
        self.reformatState.set("Activate")
        try:
            obj = asksaveasfile(
                title="Save Graph Monster Data",
                mode="wb",
                filetypes=(("Graph Monster Graph", "*.gmg"), ),
                defaultextension=".gmg",
            )
            if obj:
                with obj as file:
                    dump(self.encodeData(), file)
        except:
            Messagebox.show_error(title="Error", message="Saving Failed")

    def importGraph(self):
        self.reformatState.set("Activate")
        try:
            obj = askopenfile(
                title="Load Graph Monster Data",
                mode="rb",
                filetypes=(("Graph Monster Graph", "*.gmg"), ),
                defaultextension=".gmg",
            )
            if obj:
                with obj as file:
                    self.deployData(load(file))
                    self.pushCurData()
        except:
            Messagebox.show_error(title="Error", message="Loading Failed")

    def closeReformat(self):
        self.reformatState.set("Activate")
        self.reformatWin.destroy()

    def reformatUI(self):
        self.reformatWin = Toplevel(self.mainWin)
        self.reformatWin.geometry("+100+400")
        self.reformatWin.title("Graph Reformatter")
        self.reformatWin.attributes("-topmost", 1)
        self.reformatWin.protocol("WM_DELETE_WINDOW", self.closeReformat)

        self.formatStatus = StringVar(value="Ready")
        self.reformatState = StringVar(value="Activate")

        frame = Labelframe(self.reformatWin, text="Parameters Setting")
        frame.grid(row=0, column=0, sticky="NSWE", padx=30, pady=20, ipady=5)

        Label(
            frame,
            text="Damping Factor (0.05 - 0.95)",
        ).grid(row=0, column=0, sticky="NW")
        Entry(
            frame,
            justify="center",
            textvariable=self.damping,
        ).grid(row=1, column=0, padx=10, sticky="NWE")
        Label(
            frame,
            text="Node Mass (10 - 100)",
        ).grid(row=0, column=1, sticky="NW")
        Entry(
            frame,
            justify="center",
            textvariable=self.nodeMass,
        ).grid(row=1, column=1, padx=10, sticky="NWE")
        Label(
            frame,
            text="Elasticity (1.0 - 10.0)",
        ).grid(row=2, column=0, sticky="NW")
        Entry(
            frame,
            justify="center",
            textvariable=self.elasticity,
        ).grid(row=3, column=0, padx=10, sticky="NWE")
        Label(
            frame,
            text="Ideal Edge Length",
        ).grid(row=2, column=1, sticky="NW")
        Entry(
            frame,
            justify="center",
            textvariable=self.idealEdgeLen,
        ).grid(row=3, column=1, padx=10, sticky="NWE")
        Label(
            frame,
            text="Node Repel Radius",
        ).grid(row=4, column=0, sticky="NW")
        Entry(
            frame,
            justify="center",
            textvariable=self.repelThreshold,
        ).grid(row=5, column=0, padx=10, sticky="NWE")
        Label(
            frame,
            text="Node Repel Factor (10.0 - 75.0)",
        ).grid(row=4, column=1, sticky="NW")
        Entry(
            frame,
            justify="center",
            textvariable=self.repelFactor,
        ).grid(row=5, column=1, padx=10, sticky="NWE")

        Button(
            self.reformatWin,
            textvariable=self.reformatState,
            text="Activate",
            command=self.activate,
        ).grid(row=2, column=0, padx=60, sticky="NWE")
        Label(
            self.reformatWin,
            textvariable=self.formatStatus,
            anchor="n",
        ).grid(row=3, column=0, sticky="NWSE")

    def activate(self):
        signal = 0
        if self.reformatState.get() == "Activate":
            self.reformatState.set("Stop")
            if self.checkReformatParas():
                self.formatStatus.set("Running...")
                while self.reformatState.get() == "Stop" and self.data["Node"]:
                    coordBook = {
                        idx: self.canvas.coords(idx)
                        for idx in self.data["Node"]
                    }
                    signal = self.manipulate(coordBook)
                    if signal and self.formatStatus.get() != "Converged":
                        self.formatStatus.set("Converged")
                    elif not signal and self.formatStatus.get() != "Running":
                        self.formatStatus.set("Running")
                # Set all nodes static
                for node in self.data["Node"].values():
                    node.a = [0, 0]
                    node.v = [0, 0]
            else:
                self.formatStatus.set("Invalid Input")
                self.reformatState.set("Activate")
                return
            self.formatStatus.set("Converged" if signal else "Aborted")
        self.reformatState.set("Activate")

    def checkReformatParas(self):
        try:
            return 0.05 <= self.damping.get() <= 0.95 and \
                    10 <= self.nodeMass.get() <= 100 and \
                    0.5 <= self.elasticity.get() <= 10 and \
                    1 <= self.idealEdgeLen.get() and \
                    10 <= self.repelFactor.get() <= 75
        except:
            return 0

    def getAdjNodes(self, node: Node) -> set[str]:
        '''
        return set of node ids
        '''
        total = set()
        for lineId in node.adjLines:
            line = self.data["Line"][lineId]
            if line.node1 == node or line.node2 == node:
                total.add(line.node1.canvasIds[0] if line.node2 ==
                          node else line.node2.canvasIds[0])
        return total

    def manipulate(self, coordBook):
        if not coordBook: return 1
        # set node status
        for node in self.data["Node"].values():
            holdingNodes = self.canvas.find_withtag("current")
            if holdingNodes and node.canvasIds[0] == holdingNodes[0]: continue
            fx = fy = 0
            adjNodeIds = self.getAdjNodes(node)
            startCoord = self.getCenter(coordBook[node.canvasIds[0]])
            for endNode in self.data["Node"].values():
                endCoord = self.getCenter(coordBook[endNode.canvasIds[0]])
                if endNode.canvasIds[0] in adjNodeIds:
                    dfx, dfy = self.getForce(startCoord, endCoord)
                elif endNode != node:
                    dfx, dfy = self.getRepel(startCoord, endCoord)
                else:
                    dfx = dfy = 0
                fx += dfx
                fy += dfy
            self.setNodeAcc(node, fx, fy)
            deltaS = self.move(node)
            self.canvas.move(node.canvasIds[0], *deltaS)
            self.canvas.move(node.canvasIds[1], *deltaS)
            if not node.adjLines:
                node.a = [0, 0]
                node.v = [0, 0]
        for line in self.data["Line"]:
            self.reconnect(line)
        self.canvas.update()
        time.sleep(self.CANVASUPDATEGAP)
        # Check for motion status
        for node in self.data["Node"].values():
            if max(node.a) >= self.motionTolerance and max(
                    node.v) >= self.motionTolerance:
                break
        else:
            return 1
        return 0

    def setNodeAcc(self, node, fx, fy):
        ax, ay = fx / self.nodeMass.get(), fy / self.nodeMass.get()
        node.a[0] = ax
        node.a[1] = ay

    def move(self, node):
        vt = node.v
        vt[0] += node.a[0]
        vt[1] += node.a[1]
        vt[0] *= (1 - self.damping.get())
        vt[1] *= (1 - self.damping.get())
        return vt

    def getForce(self, startCoord, endCoord):
        (x1, y1), (x2, y2) = startCoord, endCoord
        d = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
        f = self.elasticity.get() * (d -
                                     self.idealEdgeLen.get() * self.curScale)
        deg = atan2((y2 - y1), (x1 - x2))
        return -f * cos(deg), f * sin(deg)

    def getRepel(self, startCoord, endCoord):
        (x1, y1), (x2, y2) = startCoord, endCoord
        d = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
        length = self.repelThreshold.get() * self.curScale
        if d > length:
            return 0, 0
        f = -length / ((d + 1e-3) / self.repelFactor.get())**2
        deg = atan2((y2 - y1), (x1 - x2))
        return -f * cos(deg), f * sin(deg)

    def explain(self):
        msg = """
        Switching to "Node" mode (Ctrl + q), you can "add" nodes to canvas and "drag" them.
        Switching to "Line" mode (Ctrl + w), you can "connect" 2 nodes with default weight "1".
        Switching to "Drag" mode (Ctrl + e), you can "scale" and "move" canvas.
        You can "right click" to "remove" nodes and edges.
        You can click the "middle key" (wheel) to "edit" an edge's weight.
        The "Reset Labels" button can "reset" the labels to make them neater.
        The nodes and edges are shown in the lower left corner. There is a fine line between 2 regions, and you can drag it to adjust te relative size between them.
        You can change the skin in "Theme" menu.
        The "Graph Reformatter" is a physics-based model which will reformat the graph by rearranging nodes accoding to thier connectivity. Edges can be considered as springs.
        You can save and load the graph using "Export Graph" and "Import Graph".
        You can customize graph output using "Output Customizer". You can find detailed guide there.
        You can press Ctrl+Z/Y to cancel and redo operations.
        """
        Messagebox.ok(title="Guide", message=msg.replace("  ", ""))

    def getCanvasCoords(self, event):
        return self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def resetLabel(self):
        self.incre_idx = -1
        for tag in self.data["Node"]:
            node = self.data["Node"][tag]
            node.val = self.getNodeIdx()
            textId = node.canvasIds[-1]  # Text id
            self.canvas.itemconfig(textId, text=node.val)
        self.updateOutPut()

    def handleMidClick(self, event):
        curIds = self.canvas.find_withtag("current")
        if curIds and (curId := curIds[0]) in self.data["Line"]:
            line = self.data["Line"][curId]
            self.edgeConfigUI(
                curId,
                f"{line.node1.val} -> {line.node2.val}",
                event.x,
                event.y,
            )

    def edgeConfigUI(self, lineId, edgeInfo: str, x, y):
        setWin = Toplevel(self.mainWin)
        setWin.geometry(f"+{x+550}+{y+230}")

        self.settingStatus = StringVar(value="Ready")

        frame = Labelframe(setWin, text=f"Edge Setter ({edgeInfo}) ")
        frame.grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            ipady=5,
            sticky="NSWE",
        )

        self.edgeWeightEntry = Entry(frame, justify="center")
        self.edgeWeightEntry.grid(
            row=1,
            column=0,
            padx=5,
            sticky="NWE",
        )
        Button(
            setWin,
            text="Commit",
            command=partial(self.commitWeight, lineId),
        ).grid(row=2, column=0, padx=60, sticky="NWE")
        Label(
            setWin,
            textvariable=self.settingStatus,
            anchor="n",
        ).grid(row=3, column=0, sticky="NWSE")

        setWin.mainloop()

    def commitWeight(self, lineId):
        try:
            weight = eval(self.edgeWeightEntry.get())
            line = self.data["Line"][lineId]
            textId = line.canvasIds[-1]
            line.weight = weight
            self.canvas.itemconfig(textId, text=str(weight))
            self.settingStatus.set(f"Successfully set to {weight}")
            self.updateOutPut()
            # weight set
            self.pushCurData()
        except:
            self.settingStatus.set("Invalid Input")

    def handleStateChange(self, toState, event=None):
        self.curState = toState
        for state, widget in self.stateToWidget.items():
            widget["state"] = "disabled" \
                                if state == self.curState \
                                else "normal"
        self.canvas["cursor"] = "" \
                                if self.curState != self.STATE_DRAG \
                                else "fleur"

    def handleLeftClick(self, event):
        if self.curState == self.STATE_DRAG:
            self.canvas.scan_mark(event.x, event.y)
        else:
            event.x, event.y = self.getCanvasCoords(event)
            # if state is node
            if self.curState == self.STATE_NODE:
                # if not holding a node
                if self.startNode == self.EMPTY:
                    # if clicked on nothing
                    if not (curIds := self.canvas.find_withtag("current")):
                        offset = self.NODESIZE * self.curScale
                        key = (
                            event.x - offset,
                            event.y - offset,
                            event.x + offset,
                            event.y + offset,
                        )
                        idx = self.getNodeIdx()
                        nodeId = self.drawNode(*key)
                        self.data["Node"][nodeId] = Node(
                            idx,
                            scale=self.curScale,
                            canvasIds=[
                                nodeId,
                                self.drawText(
                                    key[0] + offset,
                                    key[1] + offset,
                                    mode=0,
                                    text=str(idx),
                                )
                            ],
                        )
                        self.pushCurData()
                    # if click on a node
                    elif curIds and curIds[0] in self.data["Node"]:
                        self.startNode = self.data["Node"][curIds[0]]
                        self.lineBtn["state"] = self.dragBtn[
                            "state"] = "disabled"
                # if holding a node
                else:
                    self.startNode = self.EMPTY
                    self.lineBtn["state"] = self.dragBtn["state"] = "normal"
                    # Trace Movement
                    self.pushCurData()

            # If state is line, clicked on a node, and the node is a different one (no self-loop)
            elif self.curState == self.STATE_LINE and \
                    (curIds := self.canvas.find_withtag("current")) and \
                    (nodeId := curIds[0]) in self.data["Node"]:
                # Get the current node info (center and label)
                lineEndNode = self.data["Node"][nodeId]
                # If we choose the end of a line
                if self.lineStartNode != self.EMPTY:
                    # self-loop check
                    if lineEndNode == self.lineStartNode:
                        return
                    # replicacy check
                    for line in self.data["Line"].values():
                        if line.node1 == self.lineStartNode and line.node2 == lineEndNode:
                            return
                    coords = self.getLineCoords(self.lineStartNode,
                                                lineEndNode)
                    lineId = self.drawLine(*coords)
                    self.data["Line"][lineId] = Line(
                        self.lineStartNode,
                        lineEndNode,
                        1,
                        [
                            lineId,
                            self.drawText(
                                *self.linearComb(*coords), mode=1, text="1")
                        ],
                    )
                    self.lineStartNode.adjLines.add(lineId)
                    lineEndNode.adjLines.add(lineId)
                    self.lineStartNode = self.EMPTY
                    self.NodeBtn["state"] = self.dragBtn["state"] = "normal"
                    self.canvas.config(cursor="")
                    self.canvas.delete("tmp")  # Get rid of assist line
                    # Trace add
                    self.pushCurData()
                # If we choose the start of a line
                else:
                    self.lineStartNode = lineEndNode
                    self.NodeBtn["state"] = self.dragBtn["state"] = "disabled"
                    self.canvas.config(cursor="tcross")
        self.updateOutPut()

    def handlerightClick(self, event):
        if self.curState == self.STATE_LINE and not self.canvas.coords(
                "current") and self.lineStartNode != self.EMPTY:
            self.lineStartNode = self.EMPTY
            self.NodeBtn["state"] = self.dragBtn["state"] = "normal"
            self.canvas.config(cursor="")
            self.canvas.delete("tmp")  # get rid of assist line
        elif (curIds := self.canvas.find_withtag("current")) and \
                self.lineStartNode == self.EMPTY:
            thisId = curIds[0]
            if thisId in self.data["Node"] and \
                    self.data["Node"][thisId] != self.startNode:
                node = self.data["Node"][thisId]
                # maintain canvas
                self.canvas.delete(*node.canvasIds)  # node & text
                self.canvas.delete(*node.adjLines)  # edge
                self.canvas.delete(*[  # edge text
                    self.data["Line"][x].canvasIds[-1] for x in node.adjLines
                ])
                # maintain data
                del self.data["Node"][thisId]  # node
                for lineId in node.adjLines.copy():  # edge
                    # maintain adjacent nodes
                    line = self.data["Line"][lineId]
                    for connectedNode in (line.node1, line.node2):
                        connectedNode.adjLines.discard(lineId)
                    del self.data["Line"][lineId]

            elif thisId in self.data["Line"]:
                line = self.data["Line"][thisId]
                # maintain data
                for connectedNode in (line.node1, line.node2):
                    connectedNode.adjLines.discard(thisId)  # adjacent nodes
                del self.data["Line"][thisId]  # edge
                # maintain canvas
                self.canvas.delete(*line.canvasIds)

            # Trace delete
            self.pushCurData()

        self.updateOutPut()

    def handleMotion(self, event):
        event.x, event.y = self.getCanvasCoords(event)
        self.canvas.delete("tmp")
        if self.curState == self.STATE_LINE and self.lineStartNode != self.EMPTY:
            self.canvas.create_line(
                self.getLineCoords(self.lineStartNode, Node(-1, scale=0),
                                   event.x, event.y),
                width=self.LINEWIDTH,
                state="disabled",
                arrow="last",
                fill="grey",
                tags="tmp",
                dash=".",
            )
        elif self.curState == self.STATE_NODE and self.startNode != self.EMPTY:
            ## Change Node
            nodeId, textId = self.startNode.canvasIds
            offset = self.NODESIZE * self.data["Node"][nodeId].scale
            ovalCoord = [
                event.x - offset,
                event.y - offset,
                event.x + offset,
                event.y + offset,
            ]
            self.canvas.coords(textId, list(self.getCenter(ovalCoord)))
            self.canvas.coords(nodeId, ovalCoord)
            ## Change adjacent edges
            for lineId in self.startNode.adjLines:
                self.reconnect(lineId)

    def handleWheel(self, event, signal=0):
        if self.curState == self.STATE_DRAG and not signal:
            event.x, event.y = self.getCanvasCoords(event)
            scale = 1 / self.SCALERATIO if event.num == 5 or event.delta == -120 else self.SCALERATIO
            self.curScale *= scale
            self.canvas.scale("all", event.x, event.y, scale, scale)
            for node in self.data["Node"].values():
                node.scale *= scale
        elif signal:
            scale = 1 / self.SCALERATIO if event.num == 5 else self.SCALERATIO
            self.curScale *= scale
            self.canvas.scale("all", event.x, event.y, scale, scale)

    def handleMove(self, event):
        if self.curState == self.STATE_DRAG:
            self.canvas.scan_dragto(event.x, event.y, gain=1)

    def getNodeIdx(self):
        self.incre_idx += 1
        return self.incre_idx

    def getSlope(self, x0, y0, x1, y1):
        return atan((y0 - y1) / (x0 - x1)) if x0 != x1 else self.EMPTY

    def getCenter(self, coord):
        return (coord[0] + coord[2]) / 2, (coord[1] + coord[3]) / 2

    def getLineCoords(self, startNode, endNode, xt=None, yt=None):
        xs, ys = self.getCenter(self.canvas.coords(startNode.canvasIds[0]))
        if xt is None:
            xt, yt = self.getCenter(self.canvas.coords(endNode.canvasIds[0]))
        deg = self.getSlope(xs, ys, xt, yt)
        flag = -1 if xs > xt else 1
        dx, dy = cos(deg) * self.NODESIZE, \
                 sin(deg) * self.NODESIZE
        return (
            xs + flag * dx * startNode.scale,
            ys + flag * dy * startNode.scale,
            xt - flag * dx * endNode.scale,
            yt - flag * dy * endNode.scale,
        )

    def explainCustomizer(self):
        msg = """
        This UI allows you to customize your graph output.
        "Line" Mode: Every "unit" will be displayed at each line.
        "List" Mode: The "unit"s will be enclosed by "container start" and "container end" and seperated by "container seperator". The information will be displayed in one line.
        The token for node is "label".
        The token "node1" is for the start of an edge, "node2" is for the end of an edge, "weight" is for the weight of an edge.
        """
        Messagebox.ok(title="Customizer Guide", message=msg.replace("  ", ""))

    def outputCustomUI(self):
        """
        UIdata: self.outputData
            by self.loadStyleToUIData
            to
            back by self.parseCustom and self.applyCustom
        StyleData: self.curOutputStyle

        UI
        """
        self.customWin = Toplevel(self.mainWin)
        self.customWin.geometry("+1000+100")
        self.customWin.title("Graph Reformatter")
        self.customWin.attributes("-topmost", 1)

        self.customLineMode = IntVar(value=1)
        self.customNodeMode = IntVar(value=1)
        self.lineModeStatus = StringVar(value="List")
        self.nodeModeStatus = StringVar(value="List")
        self.modeStatusBook = ["Line", "List"]
        labels = ("Unit", "Container Left", "Container Right",
                  "Container Seperator")
        self.CustomStatusIndicator = StringVar(value="Ready")

        menubar = Menu(self.customWin)
        menubar.add_command(label="Guide", command=self.explainCustomizer)
        menubar.add_command(label="Import Style", command=self.importStyle)
        menubar.add_command(label="Export Style", command=self.exportStyle)
        menubar.add_command(
            label="Default Style",
            command=partial(
                self.loadStyleToUIData,
                self.defaultOutputStyle,
                1,
                1,
            ),
        )
        self.customWin.config(menu=menubar)

        nodeHeader = Frame(self.customWin)
        nodeSetter = Frame(self.customWin)
        lineHeader = Frame(self.customWin)
        lineSetter = Frame(self.customWin)
        nodeHeader.pack(side="top", fill="x", expand=1, padx=20, pady=(20, 0))
        nodeSetter.pack(side="top", fill="x", expand=1, padx=20, pady=5)
        lineHeader.pack(side="top", fill="x", expand=1, padx=20, pady=(0, 5))
        lineSetter.pack(side="top", fill="x", expand=1, padx=20, pady=(0, 0))

        def install(header, setter, data, modeVar, statusVar, which):
            Label(header, text=which).pack(side="left")
            Checkbutton(
                header,
                textvariable=statusVar,
                onvalue=1,
                offvalue=0,
                variable=modeVar,
                bootstyle="square-toggle",
                command=partial(self.toggleCusMode, modeVar, statusVar),
            ).pack(side="left", padx=15)
            tmpFrames = [Frame(setter) for _ in range(4)]
            for i, frame in enumerate(tmpFrames):
                name = labels[i]
                frame.pack(side="left", fill="x", expand=1, padx=10)
                Label(frame, text=name).pack(side="top", fill="x", expand=1)
                Entry(frame, textvariable=data[i],
                      justify="center").pack(side="top",
                                             fill="x",
                                             expand=1,
                                             pady=(0, 20))

        install(nodeHeader, nodeSetter, self.ouputData["Node"],
                self.customNodeMode, self.nodeModeStatus, "Nodes")
        install(lineHeader, lineSetter, self.ouputData["Line"],
                self.customLineMode, self.lineModeStatus, "Edges")

        Button(
            self.customWin,
            text="Commit",
            command=self.applyCustom,
            width=20,
        ).pack(side="top")
        Label(
            self.customWin,
            textvariable=self.CustomStatusIndicator,
        ).pack(side="bottom")

    def importStyle(self):
        try:
            obj = askopenfile(
                title="Load Cutomized Output Style",
                mode="rb",
                filetypes=(("Graph Monster Style", "*.gms"), ),
                defaultextension=".gms",
            )
            if obj:
                with obj as file:
                    data, nodeModeData, lineModeData = load(file)
                    self.customNodeMode.set(nodeModeData)
                    self.customLineMode.set(lineModeData)
                    self.loadStyleToUIData(data, nodeModeData, lineModeData)
            else:
                self.CustomStatusIndicator.set("File not opened")
        except:
            Messagebox.show_error(title="Error", message="Loading Failed")

    def exportStyle(self):
        try:
            obj = asksaveasfile(
                title="Save Cutomized Output Style",
                mode="wb",
                filetypes=(("Graph Monster Style", "*.gms"), ),
                defaultextension=".gms",
            )
            if obj:
                with obj as file:
                    dump(
                        [
                            self.curOutputStyle,
                            self.customNodeMode.get(),
                            self.customLineMode.get(),
                        ],
                        file,
                    )
            else:
                self.CustomStatusIndicator.set("File not opened")
        except:
            Messagebox.show_error(title="Error", message="Saving Failed")

    def loadStyleToUIData(self, style, nodeMode, lineMode):
        """
        base data to UI data
        """
        for label in ("Node", "Line"):
            self.ouputData[label][0].set(style[label]["unit"])
            self.ouputData[label][1].set(style[label]["list"][0])
            self.ouputData[label][2].set(style[label]["list"][1])
            self.ouputData[label][3].set(style[label]["sep"])
        self.customNodeMode.set(nodeMode)
        self.customLineMode.set(lineMode)
        self.toggleCusMode(self.customNodeMode, self.nodeModeStatus)
        self.toggleCusMode(self.customLineMode, self.lineModeStatus)

    def parseCustom(self, styleOutputData=None):
        """
        UI data to base data
        """
        if styleOutputData is None:
            styleOutputData = self.ouputData
        ans = deepcopy(self.defaultOutputStyle)
        data = styleOutputData["Node"]
        ans["Node"]["unit"] = data[0].get()
        ans["Node"]["list"] = [data[1].get(), data[2].get()]
        ans["Node"]["sep"] = data[3].get()
        data = styleOutputData["Line"]
        ans["Line"]["unit"] = data[0].get()
        ans["Line"]["list"] = [data[1].get(), data[2].get()]
        ans["Line"]["sep"] = data[3].get()
        return ans

    def applyCustom(self, UIData=None):
        """
        Button event handler; receive UI data
        flow: Parsing -> Check -> Apply
        """
        tmp = self.parseCustom(UIData)
        if self.checkCustomedStyle(tmp, self.customNodeMode.get(),
                                   self.customLineMode.get()):
            self.curOutputStyle = tmp
            self.CustomStatusIndicator.set("Succeeded")
            self.updateOutPut()
        else:
            self.CustomStatusIndicator.set("Invalid Input")

    def toggleCusMode(self, modeVar, statusVar):
        statusVar.set(self.modeStatusBook[modeVar.get()])

    def checkCustomedStyle(self, style, modeN, modeL):
        '''
        check base data
        mode = 0: line mode
        mode = 1: list mode
        '''
        nodeU, nodeL, nodeS = style["Node"].values()
        lineU, lineL, lineS = style["Line"].values()
        return (not modeN or (all(nodeL) and nodeS)) and \
                (not modeL or (all(lineL) and lineS))

    def getCustomedOutput(self, modeN, modeL):
        '''
        use base data to get strings
            mode = 0: line mode
            mode = 1: list mode
        '''
        nodeU, nodeL, nodeS = self.curOutputStyle["Node"].values()
        lineU, lineL, lineS = self.curOutputStyle["Line"].values()
        nodeUnits = [
            nodeU.replace("label", str(x)) for x in self.data["Node"].values()
        ]
        nodeStr = (nodeS.join(nodeUnits)).join(nodeL) if modeN \
                else "\n".join(nodeUnits)
        lineUnits = [
            lineU.replace("node1", str(x.node1)).replace(
                "node2", str(x.node2)).replace("weight", str(x.weight))
            for x in self.data["Line"].values()
        ]
        lineStr = (lineS.join(lineUnits)).join(lineL) if modeL \
                else "\n".join(lineUnits)
        return nodeStr, lineStr

    def updateOutPut(self):
        for entry in self.nodeEntrys:
            entry.delete("1.0", "end")
        for entry in self.edgeEntrys:
            entry.delete("1.0", "end")
        # Python
        self.nodeEntrys[0].insert(
            "1.0",
            str(list(map(
                lambda x: x.val,
                self.data["Node"].values(),
            ))),
        )
        self.edgeEntrys[0].insert(
            "1.0",
            str([line.getView() for line in self.data["Line"].values()]),
        )
        # Line
        self.nodeEntrys[1].insert(
            "1.0",
            "\n".join(map(str, self.data["Node"].values())),
        )
        self.edgeEntrys[1].insert(
            "1.0",
            "\n".join(" ".join(map(str, line.getView()))
                      for line in self.data["Line"].values()),
        )
        # customized
        nodeStr, lineStr = self.getCustomedOutput(self.customNodeMode.get(),
                                                  self.customLineMode.get())
        self.nodeEntrys[2].insert("1.0", nodeStr)
        self.edgeEntrys[2].insert("1.0", lineStr)

    def linearComb(self, x1, y1, x2, y2, ratio=0.7):
        # offset = 0.1 * max(abs(x1 - x2), abs(y1 - y2))
        # offset = -self.LINETAGOFFSET / self.getSlope(x1, y1, x2, y2)
        offset = self.LINETAGOFFSET * self.curScale
        return (
            x1 * ratio + x2 * (1 - ratio) + offset,
            y1 * ratio + y2 * (1 - ratio) + offset,
        )

    def reconnect(self, lineId):
        line = self.data["Line"][lineId]
        lineCoord = self.getLineCoords(line.node1, line.node2)
        textCoord = self.linearComb(*lineCoord)
        self.canvas.coords(lineId, list(lineCoord))
        self.canvas.coords(line.canvasIds[-1], list(textCoord))

    def drawNode(self, x1, y1, x2, y2):
        return self.canvas.create_oval(
            x1,
            y1,
            x2,
            y2,
            fill=self.COLORBOOK["oval"][self.curTheme.get()],
            width=self.NODEWIDTH,
            activeoutline="red",
        )

    def drawLine(self, x1, y1, x2, y2):
        return self.canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            width=self.LINEWIDTH,
            fill=self.COLORBOOK["line"][self.curTheme.get()],
            activedash=".",
            activefill="blue",
            arrow="last",
        )

    def drawText(self, x, y, mode, text):
        """ Create a label for:
            mode = 0: Node
            mode = 1: Line
        """
        return self.canvas.create_text(
            x,
            y,
            font=("", 13, "bold"),
            text=text,
            state="disabled",
            fill=self.COLORBOOK["text"][self.curTheme.get()],
        )


if __name__ == "__main__":
    GraphMonster()
