from ttkbootstrap import Window, Frame, Button, \
                        Text, Label, Labelframe, \
                        Canvas, Toplevel, Entry, \
                        StringVar, Menu
from ttkbootstrap.dialogs.dialogs import Messagebox
from math import atan, cos, sin
from functools import partial


class Node:

    def __init__(self, val, canvasIds=[], scale=1):
        self.val = val
        self.canvasIds = canvasIds  # 2 elements: widget id and its label id
        self.neighbor = []
        self.scale = scale

    def __eq__(self, other):
        return isinstance(other, Node) and self.val == other.val


class GraphMonster:

    def __init__(self):
        self.mainWin = Window()
        self.mainWin.geometry("1550x900+200+50")
        self.mainWin.title("Graph Monster")

        self.NODENEIGHBORTOLERANCE = 5
        self.EMPTY = -1e9
        self.NODEFILLCOLOR = "white"
        self.EDGEFILLCOLOR = "grey"
        self.LINETAGOFFSET = 10
        self.SCALERATIO = 1.3
        self.NODEWIDTH = 2
        self.NODESIZE = 20
        self.LINEWIDTH = 3
        self.curScale = 1
        self.incre_idx = -1
        self.motionStartX = self.motionStartY = None
        self.canvasOffsetX = self.canvasOffsetY = 0
        self.nodeStartCoords = self.startNode = self.adjLines = self.EMPTY
        self.centerX = self.centerY = self.centerNode = self.EMPTY
        self.data = {"Node": {}, "Line": {}}
        """
        self.data = {
            "Node": {
                (x1, y1, x2, y2): Node(Label, neighbor, [canvasIds], scale)
                # the node centered at ((x1 + x2) / 2, (y1 + y2) / 2)
                # has the label "Label" and has been scaled by "scale"
            }
            "Line": {
                (x1, y1, x2, y2): [Node_1, Node_2, weight=1, [canvasIds]]
                # the edge from "node_1" to "node_2" has weight "weight"
            }
        }

        self.adjLines = [ [Line_canvas_id, ] ]
        """

        menubar = Menu(self.mainWin)
        menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="System", menu=menu)
        menu.add_command(label="Guide", command=self.explain)
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

        # # Test
        # from itertools import pairwise
        # self.edgeEntry.insert(1.0, f"{[(i, i + 1, 1) for i in range(50)]}")

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
        self.canvas.bind("<ButtonRelease-1>", self.handleLeftRelease)
        self.canvas.bind("<MouseWheel>", self.handleWheel)
        self.canvas.bind("<B1-Motion>", self.handleMove)
        self.canvas.bind("<Motion>", self.handleMotion)

        self.handleStateChange(self.STATE_NODE)
        self.updateOutPut()
        self.mainWin.mainloop()

    def explain(self):
        msg = """
        Switching to "Node" mode, you can add node to canvas.
        Switching to "Line" mode, you can connect 2 nodes with default weight "1".
        Switching to "Drag" mode, you can scale and move canvas.
        You can right click to remove nodes and edges.
        You can click the middle key (wheel) to edit an edge's weight.
        The nodes and edges are shown in the lower left corner.
        The "Reset Labels" button can reset the labels to make them neater.
        """
        Messagebox.ok(title="Guide", message=msg.replace("  ", ""))

    def resetLabel(self):
        self.incre_idx = -1
        for key in self.data["Node"]:
            node = self.data["Node"][key]
            node.val = self.getNodeIdx()
            oriId = node.canvasIds[-1]
            oriCoords = self.canvas.coords(oriId)
            self.canvas.delete(oriId)
            node.canvasIds[-1] = self.newText(
                *oriCoords,
                mode=0,
                text=str(node.val),
            )
        self.updateOutPut()

    def handleMidClick(self, event):
        coords = tuple(self.canvas.coords("current"))
        if coords and coords in self.data["Line"]:
            self.edgeConfigUI(
                self.data["Line"][coords][3][-1],
                event.x,
                event.y,
            )

    def edgeConfigUI(self, canvasId, x, y):
        setWin = Toplevel(self.mainWin)
        setWin.title("Edge Weight Setting")
        setWin.geometry(f"+{x+550}+{y+230}")

        self.settingStatus = StringVar(value="")
        self.thisTextId = canvasId

        # frame = Labelframe(setWin, text="Edge Setter", width=10, height=10).grid(row=0,
        #                                                     column=0,
        #                                                     sticky="NSWE",)
        Label(
            setWin,
            text="New Edge Weight",
        ).grid(row=0, column=0, padx=5, pady=5, sticky="NWE")
        self.edgeWeightEntry = Entry(setWin)
        self.edgeWeightEntry.grid(
            row=1,
            column=0,
            sticky="NWE",
            padx=5,
            pady=5,
        )
        Button(
            setWin,
            text="Commit",
            command=self.commitWeight,
        ).grid(row=2, column=0, padx=20, pady=5, sticky="NWE")
        Label(
            setWin,
            textvariable=self.settingStatus,
        ).grid(row=3, column=0, padx=5, pady=5, sticky="NWS")

        setWin.mainloop()

    def commitWeight(self):
        try:
            weight = eval(self.edgeWeightEntry.get())
            prevTextCoords = self.canvas.coords(self.thisTextId)
            self.canvas.delete(self.thisTextId)
            for coords, attrs in self.data["Line"].items():
                if attrs[3][-1] == self.thisTextId:
                    key = coords
            self.data["Line"][key][2] = weight
            self.data["Line"][key][-1][1] = self.thisTextId = self.newText(
                *prevTextCoords,
                mode=1,
                text=str(weight),
            )
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
            self.motionStartX, self.motionStartY = event.x, event.y
        else:
            event.x -= self.canvasOffsetX
            event.y -= self.canvasOffsetY
            # if state is node
            if self.curState == self.STATE_NODE:
                # if not holding a node
                if self.nodeStartCoords == self.EMPTY:
                    # if clicked on nothing
                    if not (coord := tuple(self.canvas.coords("current"))):
                        offset = self.NODESIZE * self.curScale
                        key = (
                            event.x - offset,
                            event.y - offset,
                            event.x + offset,
                            event.y + offset,
                        )
                        idx = self.getNodeIdx()
                        self.data["Node"][key] = Node(idx,
                                                      scale=self.curScale,
                                                      canvasIds=[
                                                          self.newNode(*key),
                                                          self.newText(
                                                              key[0] + offset,
                                                              key[1] + offset,
                                                              mode=0,
                                                              text=str(idx),
                                                          )
                                                      ])
                    # if click on a node
                    elif coord in self.data["Node"]:
                        self.startNode = self.data["Node"][coord]
                        self.nodeStartCoords = coord
                        self.lineBtn["state"] = self.dragBtn[
                            "state"] = "disabled"
                # if holding a node
                else:
                    self.startNode = self.nodeStartCoords = self.EMPTY
                    self.lineBtn["state"] = self.dragBtn["state"] = "normal"

            # If state is line, clicked on a node, the node is not the original one (no self-loop)
            elif self.curState == self.STATE_LINE and \
                            (coords := self.canvas.coords("current")):
                if self.centerX != self.EMPTY and coords[0] == \
                            self.centerX - self.NODESIZE * self.centerNode.scale:
                    return
                # Get the current node info (center and label)
                lineEndX, lineEndY, lineEndNode = \
                    (coords[0] + coords[2]) / 2, \
                    (coords[1] + coords[3]) / 2, \
                    self.data["Node"][tuple(coords)]
                # If we choose the end of a line
                if self.centerX != self.EMPTY:
                    key = self.getLineCoords(lineEndX, lineEndY, lineEndNode)
                    if key not in self.data["Line"]:
                        # No replicated edge
                        self.data["Line"][key] = [
                            self.centerNode, lineEndNode, 1,
                            [
                                self.newLine(*key),
                                self.newText(*self.linearComb(*key),
                                             mode=1,
                                             text="1")
                            ]
                        ]
                        self.centerNode.neighbor.append(lineEndNode)
                        # lineEndNode.neighbor.append(self.centerNode)
                        self.centerX = self.centerY = self.centerNode = self.EMPTY
                        self.NodeBtn["state"] = "normal"
                        self.dragBtn["state"] = "normal"
                        self.canvas.config(cursor="")
                        self.canvas.delete("tmp")  # Get rid of assist line
                # If we choose the start of a line
                else:
                    self.centerX, self.centerY, self.centerNode = lineEndX, lineEndY, lineEndNode
                    self.NodeBtn["state"] = "disabled"
                    self.dragBtn["state"] = "disabled"
                    self.canvas.config(cursor="tcross")
        self.updateOutPut()

    def handleLeftRelease(self, event):
        if self.curState == self.STATE_DRAG:
            dx, dy = event.x - self.motionStartX, event.y - self.motionStartY
            self.canvasOffsetX += dx
            self.canvasOffsetY += dy

    def handlerightClick(self, event):
        if self.curState == self.STATE_LINE and not self.canvas.coords(
                "current") and self.centerX != self.EMPTY:
            self.centerX = self.centerY = self.centerNode = self.EMPTY
            self.NodeBtn["state"] = "normal"
            self.dragBtn["state"] = "normal"
            self.canvas.config(cursor="")
            self.canvas.delete("tmp")  # get rid of assist line
        elif (coord := tuple(
                self.canvas.coords("current"))) and self.centerX == self.EMPTY:
            if coord in self.data["Node"]:
                node = self.data["Node"][coord]
                del self.data["Node"][coord]  # delete node in data
                self.canvas.delete(*node.canvasIds)  # delete node from canvas
                newDict = {}
                for key, attrs in self.data["Line"].items():
                    if node in attrs:
                        # delete connected edges from data and canvas
                        # and update neighborhood
                        attrs[0].neighbor.remove(attrs[1])
                        self.canvas.delete(*attrs[3])
                    else:
                        newDict[key] = attrs
                self.data["Line"] = newDict
            elif coord in self.data["Line"]:
                attrs = self.data["Line"][coord]
                attrs[0].neighbor.remove(attrs[1])
                del self.data["Line"][coord]
                self.canvas.delete(*attrs[3])

        self.updateOutPut()

    def handleMotion(self, event):

        event.x -= self.canvasOffsetX
        event.y -= self.canvasOffsetY
        self.canvas.delete("tmp")
        if self.curState == self.STATE_LINE and self.centerX != self.EMPTY:
            self.canvas.create_line(
                self.getLineCoords(
                    event.x,
                    event.y,
                    Node(-1, scale=0),
                ),
                width=self.LINEWIDTH,
                state="disabled",
                arrow="last",
                fill="grey",
                tags="tmp",
                dash=".",
            )
        elif self.curState == self.STATE_NODE and self.nodeStartCoords != self.EMPTY:
            ## Change Node
            self.canvas.delete(*self.startNode.canvasIds)
            offset = self.startNode.scale * self.NODESIZE
            nodeNewCoord = (
                event.x - offset,
                event.y - offset,
                event.x + offset,
                event.y + offset,
            )
            self.startNode.canvasIds = [
                self.newNode(*nodeNewCoord),
                self.newText(event.x, event.y, 0, self.startNode.val)
            ]
            # Slow but no label changed
            self.data["Node"] = {
                (x if x != self.nodeStartCoords else nodeNewCoord): v
                for x, v in self.data["Node"].items()
            }
            # # Fast but label changed
            # self.data["Node"][nodeNewCoord] = \
            #             self.data["Node"].pop(self.nodeStartCoords)

            ## Change adjacent edges
            newDict = {}
            for prevCoord, lineAttrs in self.data["Line"].items():
                if self.startNode in lineAttrs:
                    if lineAttrs[0] == self.startNode:
                        startN = self.startNode
                        endN = lineAttrs[1]
                    elif lineAttrs[1] == self.startNode:
                        startN = lineAttrs[0]
                        endN = self.startNode
                    for nodeCoord, thisNode in self.data["Node"].items():
                        if thisNode == startN:
                            startCoord = nodeCoord
                        if thisNode == endN:
                            endCoord = nodeCoord
                    xs, ys, xt, yt = ((x[i] + x[i + 2]) / 2
                                      for x in (startCoord, endCoord)
                                      for i in range(2))
                    newCoord = self.getLineCoords(
                        xs=xs,
                        ys=ys,
                        xt=xt,
                        yt=yt,
                        node=lineAttrs[1],
                        nodeS=lineAttrs[0],
                    )
                    self.canvas.delete(*self.data["Line"][prevCoord][-1])
                    self.data["Line"][prevCoord][-1] = [
                        self.newLine(*newCoord),
                        self.newText(
                            *self.linearComb(*newCoord),
                            mode=1,
                            text=str(lineAttrs[2]),
                        )
                    ]
                    newDict[newCoord] = self.data["Line"][prevCoord]
                else:
                    newDict[prevCoord] = lineAttrs

            self.data["Line"] = newDict
            self.nodeStartCoords = nodeNewCoord

    def handleWheel(self, event):
        if self.curState == self.STATE_DRAG:
            event.x = self.canvas.canvasx(event.x)
            event.y = self.canvas.canvasx(event.y)
            
            def newScale(node):
                node.scale *= scale
                return node

            tags = self.canvas.find_all()
            prev = list(map(tuple, map(self.canvas.coords, tags)))
            scale = 1 / self.SCALERATIO if event.num == 5 or event.delta == -120 else self.SCALERATIO
            self.curScale *= scale
            self.canvas.scale("all", event.x, event.y, scale, scale)
            now = map(tuple, map(self.canvas.coords, tags))
            # Update coords in data
            mapping = dict(zip(prev, now))
            self.data["Node"] = {
                mapping[k]: newScale(v)
                for k, v in self.data["Node"].items()
            }
            self.data["Line"] = {
                mapping[k]: v
                for k, v in self.data["Line"].items()
            }
            # for key0, key1 in zip(prev, now):
            #     if len(key0) > 2:
            #         if key0 in self.data["Node"]:
            #             self.data["Node"][key1] = self.data["Node"][key0]
            #             self.data["Node"][key1].scale *= scale
            #             del self.data["Node"][key0]
            #         else:
            #             self.data["Line"][key1] = self.data["Line"][key0]
            #             del self.data["Line"][key0]

    def handleMove(self, event):
        if self.curState == self.STATE_DRAG:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            # self.canvas.config(cursor="fleur")
            # self.canvas.xview_scroll((self.motionStartX - event.x), "units")
            # self.canvas.yview_scroll((self.motionStartY - event.y), "units")
            # self.motionStartX, self.motionStartY = event.x, event.y

    def getNodeIdx(self):
        self.incre_idx += 1
        return self.incre_idx

    def getSlope(self, x0, y0, x1, y1):
        return atan((y0 - y1) / (x0 - x1)) if x0 != x1 else self.EMPTY

    def getLineCoords(self, xt, yt, node, xs=None, ys=None, nodeS=None):
        if xs == None:
            xs, ys, nodeS = self.centerX, self.centerY, self.centerNode
        deg = self.getSlope(xs, ys, xt, yt)
        flag = -1 if xs > xt else 1
        dx, dy = cos(deg) * self.NODESIZE, \
                 sin(deg) * self.NODESIZE
        return (
            xs + flag * dx * nodeS.scale,
            ys + flag * dy * nodeS.scale,
            xt - flag * dx * node.scale,
            yt - flag * dy * node.scale,
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
        edges = str([(x.val, y.val, w)
                     for x, y, w, _ in self.data["Line"].values()])
        self.edgeEntry.insert("1.0", edges)
        # print([(y, self.data["Node"][y].neighbor) for y in self.data["Node"]])

    def linearComb(self, x1, y1, x2, y2, ratio=0.7):
        # offset = 0.1 * max(abs(x1 - x2), abs(y1 - y2))
        # offset = -self.LINETAGOFFSET / self.getSlope(x1, y1, x2, y2)
        offset = self.LINETAGOFFSET
        return (
            x1 * ratio + x2 * (1 - ratio) + offset,
            y1 * ratio + y2 * (1 - ratio) + offset,
        )

    def newNode(self, x1, y1, x2, y2):
        return self.canvas.create_oval(x1,
                                       y1,
                                       x2,
                                       y2,
                                       fill=self.NODEFILLCOLOR,
                                       width=self.NODEWIDTH,
                                       activeoutline="red")

    def newLine(self, x1, y1, x2, y2):
        return self.canvas.create_line(x1,
                                       y1,
                                       x2,
                                       y2,
                                       width=self.LINEWIDTH,
                                       fill=self.EDGEFILLCOLOR,
                                       activedash=".",
                                       activefill="blue",
                                       arrow="last")

    def newText(self, x, y, mode, text):
        """ Create a label for:
            mode = 0: Node
            mode = 1: Line
        """
        return self.canvas.create_text(x,
                                       y,
                                       font=("", 12, "bold") +
                                       ("italic", ) * mode,
                                       text=text,
                                       state="disabled")


if __name__ == "__main__":
    GraphMonster()