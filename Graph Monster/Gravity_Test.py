from math import atan, atan2, cos, sin
from tkinter import *
from time import sleep, time

window = Tk()
window.geometry("+200+100")
window.title("Test windows")


class Node:

    def __init__(self, canvasId, m, start):
        self.tol = 1e-4
        self.canvasId = canvasId
        self.damping = .1
        self.m = m
        self.v = [0, 0]
        self.a = [0, 0]

    def setNodeAcc(self, fx, fy):
        ax, ay = fx / self.m, fy / self.m
        self.a[0] = ax
        self.a[1] = ay

    def move(self):
        vt = node.v
        vt[0] += node.a[0]
        vt[1] += node.a[1]
        vt[0] *= (1 - self.damping)
        vt[1] *= (1 - self.damping)
        if max(vt) < self.tol and max(node.a) < self.tol:
            self.v = [0, 0]
            self.a = [0, 0]
        return vt


def moveBall(event):
    mycanvas.coords(node.canvasId, [
        event.x - size,
        event.y - size,
        event.x + size,
        event.y + size,
    ])
    node.a = [0, 0]
    node.v = [0.1, 0]


def getForce2(startCoord, endCoord):
    (x1, y1), (x2, y2) = startCoord, endCoord
    d = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
    f = k * (d - l)
    deg = atan((y1 - y2) / (x2 - x1))
    ratio_x, ratio_y = abs(cos(deg)), abs(sin(deg))
    sign_x = (-1)**(x1 > x2)
    sign_y = (-1)**(y1 > y2)
    return f * ratio_x * sign_x, f * ratio_y * sign_y


def getForce1(startCoord, endCoord):
    (x1, y1), (x2, y2) = startCoord, endCoord
    d = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
    f = k * (d - l)
    deg = atan2((y2 - y1), (x1 - x2))
    return -f * cos(deg), f * sin(deg)


def getCenter(coord):
    return (coord[0] + coord[2]) / 2, (coord[1] + coord[3]) / 2


def activate(event=None):
    while 1:
        t = time()
        now = getCenter(mycanvas.coords(node.canvasId))
        fx = fy = 0
        for coord in (a, b):
            dfx, dfy = getForce2(now, coord)
            fx += dfx
            fy += dfy

        node.setNodeAcc(fx, fy)
        dt = time() - t
        mycanvas.move(node.canvasId, *node.move())
        mycanvas.update()
        print(node.a, node.v)
        # if not (any(node.a) and any(node.v)):
        #     break
        sleep(canvasUpdateGap)


canvasUpdateGap = 1 / 120  # time interval
l = 200  # natural lenghth
k = 1  # elastic coefficient
m = 3  # mass
a = (100, 100)  # nail 1
b = (400, 400)  # nail 2
c = (500, 400)  # node
size = 10  # node size

mycanvas = Canvas(window, width=1000, height=500)
mycanvas.pack()
node = Node(
    mycanvas.create_oval(
        c[0] - size,
        c[1] - size,
        c[0] + size,
        c[1] + size,
        fill="grey",
    ),
    m,
    c,
)
mycanvas.create_oval(
    a[0] - size,
    a[1] - size,
    a[0] + size,
    a[1] + size,
    fill="grey",
),
mycanvas.create_oval(
    b[0] - size,
    b[1] - size,
    b[0] + size,
    b[1] + size,
    fill="grey",
)
mycanvas.bind("<Button-1>", moveBall)
Button(window, text="Move", command=activate).pack()
window.mainloop()