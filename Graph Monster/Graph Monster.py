from ttkbootstrap import Window, Frame, Button, \
                        Text, Label, Labelframe, \
                        Canvas, Toplevel, Entry, \
                        StringVar, Menu
from ttkbootstrap.dialogs.dialogs import Messagebox
from functools import partial
from math import atan, cos, sin


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
        self.outputPanel = Labelframe(self.functionPanel,
                                      text="Graph Outputs",
                                      padding=10)
        self.btnPanel.grid(row=0, column=0, sticky="NWE")
        self.outputPanel.grid(row=1, column=0, sticky="NWE", pady=20)

        self.STATE_NODE = 10001
        self.STATE_LINE = 10002
        self.STATE_DRAG = 10003
        self.NodeBtn = Button(self.btnPanel,
                              text="O (Node)",
                              command=partial(self.handleStateChange,
                                              self.STATE_NODE),
                              width=25)
        self.lineBtn = Button(self.btnPanel,
                              text="→   (Line)",
                              command=partial(self.handleStateChange,
                                              self.STATE_LINE),
                              width=25)
        self.dragBtn = Button(self.btnPanel,
                              text="🤏 (Drag)",
                              command=partial(self.handleStateChange,
                                              self.STATE_DRAG),
                              state="disabled",
                              width=25)
        self.NodeBtn.grid(row=0, column=0, sticky="NWE")
        self.lineBtn.grid(row=1, column=0, sticky="NWE")
        self.dragBtn.grid(row=2, column=0, sticky="NWE")
        self.stateToWidget = {
            self.STATE_NODE: self.NodeBtn,
            self.STATE_LINE: self.lineBtn,
            self.STATE_DRAG: self.dragBtn
        }

        self.nodeEntry = Text(self.outputPanel, width=21, height=4)
        self.edgeEntry = Text(self.outputPanel, width=21, height=23)
        Label(self.outputPanel, text="Nodes [Label]").grid(row=0,
                                                           column=0,
                                                           sticky="NW")
        Button(self.outputPanel,
               text="Reset Labels",
               width=8,
               command=self.resetLabel).grid(row=0, column=1, sticky="NWE")
        self.nodeEntry.grid(row=1, column=0, columnspan=2, sticky="NWE")
        Label(self.outputPanel,
              text="Edges [(node_1, node_2, weight)]").grid(row=2,
                                                            column=0,
                                                            columnspan=2,
                                                            sticky="NWE",
                                                            pady=(10, 0))
        self.edgeEntry.grid(row=3, column=0, columnspan=2, sticky="NWE")

        # # Test
        # from itertools import pairwise
        # self.edgeEntry.insert(1.0, f"{[(i, i + 1, 1) for i in range(50)]}")

        self.canvas = Canvas(self.canvasPanel,
                             width=1150,
                             height=790,
                             bg="red")
        self.canvas.grid(row=0, column=0, sticky="SNWE")
        self.canvas.bind("<ButtonPress-1>", self.handleLeftClick)
        self.canvas.bind("<ButtonPress-2>", self.handleMidClick)
        self.canvas.bind("<ButtonPress-3>", self.handlerightClick)
        self.canvas.bind("<ButtonRelease-1>", self.handleLeftRelease)
        self.canvas.bind("<MouseWheel>", self.handleWheel)
        self.canvas.bind("<B1-Motion>", self.handleMove)
        self.canvas.bind("<Motion>", self.handleMotion)
        # self.canvas.configure(xscrollincrement=1, yscrollincrement=1)

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
        for node in self.data["Node"].values():
            node.val = self.getNodeIdx()
            oriId = node.canvasIds[-1]
            oriCoords = self.canvas.coords(oriId)
            self.canvas.delete(oriId)
            y = self.canvas.create_text(*oriCoords,
                                        text=str(node.val),
                                        font=("", 12, "bold"),
                                        state="disabled")
            node.canvasIds[-1] = y
        self.updateOutPut()

    def handleMidClick(self, event):
        coords = tuple(self.canvas.coords("current"))
        if coords and coords in self.data["Line"]:
            self.edgeConfigUI(self.data["Line"][coords][3][-1], event.x,
                              event.y)

    def edgeConfigUI(self, canvasId, x, y):
        setWin = Toplevel(self.mainWin)
        setWin.title("Edge Weight Setting")
        setWin.geometry(f"+{x+550}+{y+230}")

        self.settingStatus = StringVar(value="")
        self.thisTextId = canvasId

        # frame = Labelframe(setWin, text="Edge Setter", width=10, height=10).grid(row=0,
        #                                                     column=0,
        #                                                     sticky="NSWE",)
        Label(setWin, text="New Edge Weight").grid(row=0,
                                                   column=0,
                                                   padx=5,
                                                   pady=5,
                                                   sticky="NWE")
        self.edgeWeightEntry = Entry(setWin)
        self.edgeWeightEntry.grid(
            row=1,
            column=0,
            sticky="NWE",
            padx=5,
            pady=5,
        )
        Button(setWin, text="Commit",
               command=self.commitWeight).grid(row=2,
                                               column=0,
                                               padx=20,
                                               pady=5,
                                               sticky="NWE")
        Label(setWin, textvariable=self.settingStatus).grid(row=3,
                                                            column=0,
                                                            padx=5,
                                                            pady=5,
                                                            sticky="NWS")

        setWin.mainloop()

    def commitWeight(self):
        try:
            weight = eval(self.edgeWeightEntry.get())
            prevTextCoords = self.canvas.coords(self.thisTextId)
            for coords, attrs in self.data["Line"].items():
                if attrs[3][-1] == self.thisTextId:
                    key = coords
            self.canvas.delete(self.thisTextId)
            y = self.canvas.create_text(
                prevTextCoords,
                font=("", 12, "italic", "bold"),
                text=str(weight),
                state="disabled")  # will not block line
            self.data["Line"][key][2] = weight
            self.data["Line"][key][-1][1] = self.thisTextId = y
            self.settingStatus.set(f"Successfully set to {weight}")
            self.updateOutPut()
        except:
            self.settingStatus.set("Invalid Input")

    def handleStateChange(self, toState):
        self.curState = toState
        for state, widget in self.stateToWidget.items():
            widget[
                "state"] = "disabled" if state == self.curState else "normal"
        self.canvas[
            "cursor"] = "" if self.curState != self.STATE_DRAG else "fleur"

    def handleLeftClick(self, event):
        if self.curState == self.STATE_DRAG:
            self.canvas.scan_mark(event.x, event.y)
            self.motionStartX, self.motionStartY = event.x, event.y
        else:
            # if state is node, clicked on a node
            event.x -= self.canvasOffsetX
            event.y -= self.canvasOffsetY
            if self.curState == self.STATE_NODE and not self.canvas.coords(
                    "current"):
                offset = self.NODESIZE * self.curScale
                key = (
                    event.x - offset,
                    event.y - offset,
                    event.x + offset,
                    event.y + offset,
                )
                idx = self.getNodeIdx()
                x = self.canvas.create_oval(key,
                                            fill=self.NODEFILLCOLOR,
                                            width=self.NODEWIDTH,
                                            activeoutline="red")
                y = self.canvas.create_text(key[0] + offset,
                                            key[1] + offset,
                                            text=str(idx),
                                            font=("", 12, "bold"),
                                            state="disabled")
                self.data["Node"][key] = Node(idx,
                                              scale=self.curScale,
                                              canvasIds=[x, y])
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
                        x = self.canvas.create_line(key,
                                                    width=self.LINEWIDTH,
                                                    fill=self.EDGEFILLCOLOR,
                                                    activedash=".",
                                                    activefill="blue",
                                                    arrow="last",
                                                    tags=[str(key)])
                        # offset = -self.LINETAGOFFSET / self.getSlope(*key)
                        # self.centerX += self.centerNode.scale
                        # self.centerY += self.centerNode.scale
                        y = self.canvas.create_text(
                            self.linearComb(*key),
                            font=("", 12, "italic", "bold"),
                            text="1",
                            state="disabled")  # will not block line
                        # No replicated edge
                        self.data["Line"][key] = \
                                [self.centerNode, lineEndNode, 1, [x, y]]
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
            self.canvas.delete("tmp")  # Get rid of assist line
        elif (coord := tuple(
                self.canvas.coords("current"))) and self.centerX == self.EMPTY:
            if coord in self.data["Node"]:
                node = self.data["Node"][coord]
                del self.data["Node"][coord]
                self.canvas.delete(*node.canvasIds)
                newDict = {}
                for key, attrs in self.data["Line"].items():
                    if node in attrs:
                        attrs[0].neighbor.remove(attrs[1])
                        # attrs[1].neighbor.remove(attrs[0])
                        self.canvas.delete(*attrs[3])
                    else:
                        newDict[key] = attrs
                self.data["Line"] = newDict
            elif coord in self.data["Line"]:
                attrs = self.data["Line"][coord]
                attrs[0].neighbor.remove(attrs[1])
                # attrs[1].neighbor.remove(attrs[0])
                del self.data["Line"][coord]
                self.canvas.delete(*attrs[3])

        self.updateOutPut()

    def handleMotion(self, event):
        if self.curState == self.STATE_LINE and self.centerX != self.EMPTY:
            event.x -= self.canvasOffsetX
            event.y -= self.canvasOffsetY
            self.canvas.delete("tmp")
            self.canvas.create_line(self.getLineCoords(event.x, event.y,
                                                       Node(-1, scale=0)),
                                    width=self.LINEWIDTH,
                                    state="disabled",
                                    arrow="last",
                                    fill="grey",
                                    tags="tmp",
                                    dash=".")

    def handleWheel(self, event):
        if self.curState == self.STATE_DRAG:
            tags = self.canvas.find_all()
            prev = list(map(tuple, map(self.canvas.coords, tags)))
            scale = 1 / self.SCALERATIO if event.num == 5 or event.delta == -120 else self.SCALERATIO
            self.curScale *= scale
            self.canvas.scale("all", event.x, event.y, scale, scale)
            now = list(map(tuple, map(self.canvas.coords, tags)))
            # Update coords in data
            for key0, key1 in zip(prev, now):
                if len(key0) > 2:
                    self.canvas.addtag_withtag(key1, key0)
                    if key0 in self.data["Node"]:
                        self.data["Node"][key1] = self.data["Node"][key0]
                        self.data["Node"][key1].scale *= scale
                        del self.data["Node"][key0]
                    else:
                        self.data["Line"][key1] = self.data["Line"][key0]
                        del self.data["Line"][key0]

    def handleMove(self, event):
        if self.curState == self.STATE_DRAG:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self.canvas.config(cursor="fleur")
            # self.canvas.xview_scroll((self.motionStartX - event.x), "units")
            # self.canvas.yview_scroll((self.motionStartY - event.y), "units")
            # self.motionStartX, self.motionStartY = event.x, event.y

    def getNodeIdx(self):
        self.incre_idx += 1
        return self.incre_idx

    def getSlope(self, x0, y0, x1, y1):
        return atan((y0 - y1) / (x0 - x1)) if x0 != x1 else self.EMPTY

    def getLineCoords(self, xt, yt, node):
        deg = self.getSlope(self.centerX, self.centerY, xt, yt)
        flag = -1 if self.centerX > xt else 1
        dx, dy = cos(deg) * self.NODESIZE, \
                 sin(deg) * self.NODESIZE
        return (
            self.centerX + flag * dx * self.centerNode.scale,
            self.centerY + flag * dy * self.centerNode.scale,
            xt - flag * dx * node.scale,
            yt - flag * dy * node.scale,
        )

    def updateOutPut(self):
        self.nodeEntry.delete("1.0", "end")
        self.edgeEntry.delete("1.0", "end")
        self.nodeEntry.insert(
            "1.0", str(list(map(lambda x: x.val, self.data["Node"].values()))))
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