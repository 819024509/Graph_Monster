from ttkbootstrap import Window, Frame, Button, \
                        Text, Label, Labelframe, \
                        Canvas, Toplevel, Entry, \
                        StringVar, Menu, Style
from ttkbootstrap.dialogs.dialogs import Messagebox
from math import atan, cos, sin
from functools import partial


class Node:

    def __init__(self, val, canvasIds=[], scale=1):
        self.val = val
        # 2 elements: widget id and its label id
        self.canvasIds = canvasIds if canvasIds else []
        self.scale = scale
        self.adjLines = set()

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
    This version is more maintainable than the previous one
    by redesigning the structure of self.data.

    The curves in canvas are now no longer need to be deleted 
    and redrawn, which means they are preserved as much as
    possible.
    """

    def __init__(self):
        self.mainWin = Window()
        self.mainWin.geometry("1550x900+200+50")
        self.mainWin.title("Graph Monster")

        self.NODENEIGHBORTOLERANCE = 5
        self.EMPTY = -1e9
        self.THEMENAME = ("minty", "darkly")
        self.COLORBOOK = {
            "oval": ("#E4E4E4", "grey"),
            "line": ("#17A2B8", "#FF7851"),
            "text": ("black", "#32fbe2"),
        }
        '''
        {type: (color, )}
        '''
        self.TAGCOLORLIGHT = "#FF7851"
        self.TAGCOLORNIGHT = "#56CC9D"
        self.NODEFILLCOLOR = "#EEEEEE"
        self.EDGEFILLCOLOR = "grey"
        self.LINETAGOFFSET = 10
        self.SCALERATIO = 1.3
        self.NODEWIDTH = 2
        self.NODESIZE = 20
        self.LINEWIDTH = 3
        self.curScale = 1
        self.incre_idx = -1
        self.curTheme = 1
        self.startNode = self.EMPTY
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
        menubar.add_cascade(label="System", menu=menu)
        menu.add_command(label="Guide", command=self.explain)
        menu.add_command(label="Theme", command=self.toggleTheme)
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

        self.handleStateChange(self.STATE_NODE)
        self.toggleTheme()
        self.updateOutPut()
        self.mainWin.mainloop()

    def toggleTheme(self):
        self.curTheme = (self.curTheme + 1) % len(self.THEMENAME)
        Style(self.THEMENAME[self.curTheme])
        for tag in self.canvas.find_all():
            thisType = self.canvas.type(tag)
            self.canvas.itemconfigure(
                tag,
                fill=self.COLORBOOK[thisType][self.curTheme],
            )

    def explain(self):
        msg = """
        Switching to "Node" mode, you can "add" nodes to canvas and "drag" them.
        Switching to "Line" mode, you can "connect" 2 nodes with default weight "1".
        Switching to "Drag" mode, you can "scale" and "move" canvas.
        You can "right click" to "remove" nodes and edges.
        You can click the "middle key" (wheel) to "edit" an edge's weight.
        The "Reset Labels" button can "reset" the labels to make them neater.
        The nodes and edges are shown in the lower left corner.
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

    def handleStateChange(self, toState):
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
                line = self.data["Line"][lineId]
                lineCoord = list(self.getLineCoords(line.node1, line.node2))
                textId = line.canvasIds[-1]
                self.canvas.coords(lineId, lineCoord)
                self.canvas.coords(textId, list(self.linearComb(*lineCoord)))

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
        offset = self.LINETAGOFFSET
        return (
            x1 * ratio + x2 * (1 - ratio) + offset,
            y1 * ratio + y2 * (1 - ratio) + offset,
        )

    def drawNode(self, x1, y1, x2, y2):
        return self.canvas.create_oval(
            x1,
            y1,
            x2,
            y2,
            fill=self.COLORBOOK["oval"][self.curTheme],
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
            fill=self.COLORBOOK["line"][self.curTheme],
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
            fill=self.COLORBOOK["text"][self.curTheme],
        )


if __name__ == "__main__":
    GraphMonster()