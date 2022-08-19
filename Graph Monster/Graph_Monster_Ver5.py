import time
from ttkbootstrap import Window, Frame, Button, \
                        Text, Label, Labelframe, \
                        Canvas, Toplevel, Entry, \
                        StringVar, Menu, Style, \
                        IntVar, Scale, DoubleVar
from ttkbootstrap.dialogs.dialogs import Messagebox
from math import atan2, atan, cos, sin
from functools import partial


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


class GraphMonster:
    """
    This version supports more themes which can be easily maintained
    New feature: The physical-model-based graph reformater will reformat the graph
        by rearranging the nodes accoding to the edges connected to them, which can
        be considered as springs.
    """

    def __init__(self):
        self.mainWin = Window()
        self.mainWin.geometry("1550x900+200+50")
        self.mainWin.title("Graph Monster")

        self.NODENEIGHBORTOLERANCE = 5
        self.EMPTY = -1e9
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
        self.idealEdgeLen = IntVar(value=300)
        self.curScale = 1
        self.incre_idx = -1
        self.startNode = self.EMPTY
        self.motionTolerance = 1e-4
        self.lineStartNode = self.EMPTY
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
        menu.add_command(label="Graph Reformat", command=self.reformatUI)
        menubar.add_cascade(label="Theme", menu=menu2)
        for i, theme in enumerate(self.THEMENAME):
            menu2.add_radiobutton(
                label=theme,
                value=i,
                command=self.toggleTheme,
                variable=self.curTheme,
            )
        self.mainWin.config(menu=menubar)

        self.functionPanel = Frame(self.mainWin, padding=30)
        self.canvasPanel = Labelframe(self.mainWin, text="Canvas", padding=10)
        # self.functionPanel.place(relheight=1, relwidth=0.2)
        # self.canvasPanel.place(relx=0.2, rely=.03, relheight=.93, relwidth=.78)
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

        self.nodeEntry = Text(self.outputPanel, width=21, height=4)
        self.edgeEntry = Text(self.outputPanel, width=21, height=23)
        Label(
            self.outputPanel,
            text="Nodes [Label]",
        ).grid(row=0, column=0, sticky="NW")
        Button(
            self.outputPanel,
            text="Reset Labels",
            width=8,
            command=self.resetLabel,
        ).grid(row=0, column=1, sticky="NWE")
        self.nodeEntry.grid(row=1, column=0, columnspan=2, sticky="NWE")
        Label(
            self.outputPanel,
            text="Edges [(node_1, node_2, weight)]",
        ).grid(row=2, column=0, columnspan=2, sticky="NWE", pady=(10, 0))
        self.edgeEntry.grid(row=3, column=0, columnspan=2, sticky="NWE")

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
        self.mainWin.bind("<Control-q>",
                          partial(self.handleStateChange, self.STATE_NODE))
        self.mainWin.bind("<Control-w>",
                          partial(self.handleStateChange, self.STATE_LINE))
        self.mainWin.bind("<Control-e>",
                          partial(self.handleStateChange, self.STATE_DRAG))
        self.handleStateChange(self.STATE_NODE)
        self.toggleTheme()
        self.updateOutPut()
        self.mainWin.mainloop()

    def toggleTheme(self):
        themeIdx = self.curTheme.get()
        Style(self.THEMENAME[themeIdx])
        for tag in self.canvas.find_all():
            thisType = self.canvas.type(tag)
            self.canvas.itemconfigure(
                tag,
                fill=self.COLORBOOK[thisType][themeIdx],
            )

    def reformatUI(self):
        self.reformatWin = Toplevel(self.mainWin)
        self.reformatWin.geometry("+500+500")
        self.reformatWin.title("Graph Reformater")

        self.formatStatus = StringVar(value="Ready")
        self.reformatState = StringVar(value="Activate")

        frame = Labelframe(self.reformatWin, text="Parameters Setting")
        frame.grid(row=0, column=0, sticky="NSWE", padx=20, pady=10, ipady=5)

        Label(frame, text="Damping Factor (0.05 - 0.95)").grid(
            row=0,
            column=0,
            sticky="NW",
        )
        Entry(frame, justify="center", textvariable=self.damping).grid(
            row=1,
            column=0,
            padx=10,
            sticky="NWE",
        )
        Label(frame, text="Node Mass (10 - 100)").grid(
            row=0,
            column=1,
            sticky="NW",
        )
        Entry(frame, justify="center", textvariable=self.nodeMass).grid(
            row=1,
            column=1,
            padx=10,
            sticky="NWE",
        )
        Label(frame, text="Elasticity (1.0 - 10.0)").grid(
            row=2,
            column=0,
            sticky="NW",
        )
        Entry(frame, justify="center", textvariable=self.elasticity).grid(
            row=3,
            column=0,
            padx=10,
            sticky="NWE",
        )
        Label(frame, text="Ideal Edge Length").grid(
            row=2,
            column=1,
            sticky="NW",
        )
        Entry(frame, justify="center", textvariable=self.idealEdgeLen).grid(
            row=3,
            column=1,
            padx=10,
            sticky="NWE",
        )

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
                signal = self.manipulate()
            else:
                self.formatStatus.set("Invalid Input")
                return
            self.formatStatus.set("Converged" if signal else "Aborted")
        self.reformatState.set("Activate")

    def checkReformatParas(self):
        try:
            return 0.05 <= self.damping.get() <= 0.95 and \
                    10 <= self.nodeMass.get() <= 100 and \
                    0.5 <= self.elasticity.get() <= 10 and \
                    1 <= self.idealEdgeLen.get()
        except:
            return 0

    def manipulate(self):
        if not self.data["Node"]: return 1
        while self.reformatState.get() == "Stop":
            # set node status
            for node in self.data["Node"].values():
                for lineId in node.adjLines:
                    line = self.data["Line"][lineId]
                    endNode = line.node1 if line.node2 == node else line.node2
                    fx, fy = self.getForce(
                        self.getCenter(self.canvas.coords(node.canvasIds[0])),
                        self.getCenter(self.canvas.coords(
                            endNode.canvasIds[0])),
                    )
                    self.setNodeAcc(node, fx, fy)
            # move curves
            for node in self.data["Node"].values():
                deltaS = self.move(node)
                self.canvas.move(node.canvasIds[0], *deltaS)
                self.canvas.move(node.canvasIds[1], *deltaS)
            for line in self.data["Line"]:
                self.reconnect(line)
            self.canvas.update()
            time.sleep(self.CANVASUPDATEGAP)
            # Check for motion status
            for node in self.data["Node"].values():
                if any(node.a) and any(node.v):
                    break
            else:
                return 1
        # Set all nodes static
        for node in self.data["Node"].values():
            node.a = [0, 0]
            node.v = [0, 0]
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
        if vt[0]**2 + vt[1]**2 < self.motionTolerance and \
                node.a[0]**2 + node.a[1]**2 < self.motionTolerance:
            node.v = [0, 0]
            node.a = [0, 0]
        return vt

    def getForce(self, startCoord, endCoord):
        (x1, y1), (x2, y2) = startCoord, endCoord
        d = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
        f = self.elasticity.get() * (d -
                                     self.idealEdgeLen.get() * self.curScale)
        deg = atan2((y2 - y1), (x1 - x2))
        return -f * cos(deg), f * sin(deg)

    def explain(self):
        msg = """
        Switching to "Node" mode, you can "add" nodes to canvas and "drag" them.
        Switching to "Line" mode, you can "connect" 2 nodes with default weight "1".
        Switching to "Drag" mode, you can "scale" and "move" canvas.
        You can "right click" to "remove" nodes and edges.
        You can click the "middle key" (wheel) to "edit" an edge's weight.
        The "Reset Labels" button can "reset" the labels to make them neater.
        The nodes and edges are shown in the lower left corner.
        You can change the skin in "Theme" menu
        The "Graph Reformat" is a physics-based model which will reformat the graph by rearranging nodes accoding to thier connecting edges, which can be considered as springs.
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
                    # if click on a node
                    elif curIds and curIds[0] in self.data["Node"]:
                        self.startNode = self.data["Node"][curIds[0]]
                        self.lineBtn["state"] = self.dragBtn[
                            "state"] = "disabled"
                # if holding a node
                else:
                    self.startNode = self.EMPTY
                    self.lineBtn["state"] = self.dragBtn["state"] = "normal"

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
            if thisId in self.data["Node"]:
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

    def handleWheel(self, event):
        if self.curState == self.STATE_DRAG:
            event.x, event.y = self.getCanvasCoords(event)
            scale = 1 / self.SCALERATIO if event.num == 5 or event.delta == -120 else self.SCALERATIO
            self.curScale *= scale
            self.canvas.scale("all", event.x, event.y, scale, scale)
            for node in self.data["Node"].values():
                node.scale *= scale

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

    def updateOutPut(self):
        self.nodeEntry.delete("1.0", "end")
        self.edgeEntry.delete("1.0", "end")
        self.nodeEntry.insert(
            "1.0",
            str(list(map(
                lambda x: x.val,
                self.data["Node"].values(),
            ))),
        )
        edges = str([line.getView() for line in self.data["Line"].values()])
        self.edgeEntry.insert("1.0", edges)

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