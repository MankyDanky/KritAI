# graph_view.py – live physics with auto-settle & hover-boost
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QDialog,
                             QVBoxLayout, QGraphicsEllipseItem,
                             QGraphicsSimpleTextItem, QGraphicsItemGroup, QGraphicsPixmapItem, QGraphicsTextItem)
from PyQt5.QtGui import QPen, QBrush, QPainter, QColor, QFont
from PyQt5.QtCore import (Qt, QPointF, QLineF, QVariantAnimation,
                          pyqtSignal, QTimer, QEasingCurve )
import math, random, itertools

# ---------- constants -------------------------------------------------------
SPRING_LEN = 100        # natural edge length
SPRING_K   = 0.02       # spring stiffness
CHARGE_K   = 8000       # node repulsion
DAMPING    = 0.85       # velocity damping per step
STEP_MS    = 16         # 60 Hz
SPEED_EPS  = 0.05       # |v| below which we consider graph “at rest”
MIN_STEPS  = 60         # simulate at least this many steps
BOOST_IMP  = 3.0        # velocity impulse on hover
EXTRA_HOVER_MARGIN = 6

# ---------- pastel colour helper -------------------------------------------
def lane_colour(idx: int) -> QColor:
    hue = (idx * 47) % 360
    return QColor.fromHsv(hue, 80, 230)

# ---------- node item -------------------------------------------------------
# ---------- interactive node with preview popup ----------
class NodeItem(QGraphicsEllipseItem):
    EXTRA_HOVER_MARGIN = 6          # bigger hit area
    POP_W, POP_H       = 160, 120   # preview size

    def __init__(self, commit, view, radius=8, colour=QColor("white")):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.radius = radius
        self.commit = commit
        self.view   = view
        self.setBrush(QBrush(colour))
        self.setPen(QPen(Qt.black, 2))
        self.setAcceptHoverEvents(True)
        self.vx = self.vy = 0.0          # physics

        # label on node
        lbl = f"{commit['id'][:8]}  {commit['message']}"
        txt = QGraphicsSimpleTextItem(lbl, self)
        txt.setBrush(Qt.white)
        txt.setFont(QFont("Noto Sans", 9))
        txt.setPos(radius + 4, -radius - 2)

        # tooltip
        self.setToolTip(
            f"{commit['id']}\n{commit['display_time']}\n{commit['message']}"
        )

        # hover-grow anim
        self.anim = QVariantAnimation(startValue=1.0, endValue=1.5,
                                      duration=150,
                                      valueChanged=lambda v: self.setScale(v))
        # popup graphics group (hidden by default)
        self.anim.setEasingCurve(QEasingCurve.OutExpo)
        self._makePopup()

    # ------------------------------------------------------------------ popup
    def _makePopup(self):
        from PyQt5.QtGui import QPixmap

        # 1) create group, parent it, raise it
        self.popup = QGraphicsItemGroup()
        self.popup.setParentItem(self)          # <- correct name
        self.popup.setZValue(10)                # draw above nodes/edges

        # 2) move group so that IMAGE bottom-right sits on the node centre
        self.popup.setPos(-self.POP_W, -self.POP_H)

        # 3) scale around that same bottom-right pivot
        self.popup.setTransformOriginPoint(self.POP_W, self.POP_H)
        self.popup.setScale(0.0)                # start collapsed

        # ---------- preview image ----------
        pix_path = self.commit.get("preview_abs", "")
        pm = QPixmap(pix_path)
        if pm.isNull():                         # fallback placeholder
            pm = QPixmap(self.POP_W, self.POP_H)
            pm.fill(QColor(40, 40, 40))
        pm = pm.scaled(self.POP_W, self.POP_H,
                       Qt.KeepAspectRatio, Qt.SmoothTransformation)

        QGraphicsPixmapItem(pm, self.popup)     # at (0,0) inside group

        # ---------- commit message (ellipsis) ----------
        msg = QGraphicsTextItem(self.popup)
        msg.setPlainText(self.commit["message"])
        msg.setDefaultTextColor(Qt.white)
        msg.setFont(QFont("Noto Sans", 9))
        msg.setTextWidth(self.POP_W)            # enables elide
        msg.setPos(0, self.POP_H + 2)           # just below image

        # ---------- short hash ----------
        hash_item = QGraphicsSimpleTextItem(self.commit["id"][:8], self.popup)
        hash_item.setBrush(QColor(180, 180, 180))
        hash_item.setFont(QFont("Noto Sans", 8))
        hash_item.setPos(0, self.POP_H + 20)

        # ---------- scale / fade animation ----------
        self.popAnim = QVariantAnimation(startValue=0.0, endValue=1.0,
                                         duration=250,
                                         valueChanged=self._popScale)
        self.popAnim.setEasingCurve(QEasingCurve.OutExpo)
        self.popup.hide()


    def _popScale(self, v):
        self.popup.setScale(v)
        self.popup.setOpacity(v)

    # ------------------------------------------------------------------ events
    def hoverEnterEvent(self, _):
        self.anim.setDirection(QVariantAnimation.Forward); self.anim.start()
        self.popup.show(); self.popAnim.setDirection(QVariantAnimation.Forward); self.popAnim.start()
        # kick physics
        self.view.resume_physics()

    def hoverLeaveEvent(self, _):
        self.anim.setDirection(QVariantAnimation.Backward); self.anim.start()
        self.popAnim.setDirection(QVariantAnimation.Backward); self.popAnim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.view.commitClicked.emit(self.commit["id"])
        super().mousePressEvent(e)

    # enlarge hit area
    def shape(self):
        from PyQt5.QtGui import QPainterPath
        r = self.radius + self.EXTRA_HOVER_MARGIN
        path = QPainterPath(); path.addEllipse(-r, -r, r*2, r*2)
        return path

# ---------- commit graph view ----------------------------------------------
class CommitGraphView(QGraphicsView):
    commitClicked = pyqtSignal(str)

    def __init__(self, commits, parent=None):
        super().__init__(parent)
        self.setRenderHints(self.renderHints() | QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.scene = QGraphicsScene(self); self.setScene(self.scene)

        self._nodes = {}          # id -> NodeItem
        self._edges = []          # (nodeA, nodeB, QGraphicsLineItem)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._physics_step)
        self._build_graph(commits)
        self.resume_physics(force_steps=MIN_STEPS)   # initial settle

    # wheel zoom -------------------------------------------------------------
    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.resetTransform(); return
        s = 1.25 if e.angleDelta().y() > 0 else 0.8
        self.scale(s, s)

    # build ------------------------------------------------------------------
    def _build_graph(self, commits):
        r0 = 200
        for idx, c in enumerate(commits):
            ang = 2 * math.pi * idx / len(commits)
            node = NodeItem(c, self, colour=lane_colour(idx))
            node.setPos(math.cos(ang) * r0, math.sin(ang) * r0)
            self.scene.addItem(node)
            self._nodes[c["id"]] = node

        for c in commits:
            p = c.get("parent")
            if p and p in self._nodes:
                a, b = self._nodes[c["id"]], self._nodes[p]
                line = self.scene.addLine(QLineF(a.pos(), b.pos()),
                                          QPen(Qt.gray, 2))
                line.setZValue(-10) 
                self._edges.append((a, b, line))

        self.setSceneRect(self.scene.itemsBoundingRect())

    # public: resume physics -------------------------------------------------
    def resume_physics(self, force_steps=MIN_STEPS):
        """Start (or keep) simulating until motion < SPEED_EPS."""
        self._steps_left = max(getattr(self, "_steps_left", 0), force_steps)
        if not self._timer.isActive():
            self._timer.start(STEP_MS)

    # physics step -----------------------------------------------------------
    def _physics_step(self):
        # Coulomb repulsion
        for a, b in itertools.combinations(self._nodes.values(), 2):
            dx, dy = a.x() - b.x(), a.y() - b.y()
            dist2 = dx*dx + dy*dy or 0.01
            force = CHARGE_K / dist2
            fx = force * dx / math.sqrt(dist2)
            fy = force * dy / math.sqrt(dist2)
            a.vx += fx; a.vy += fy
            b.vx -= fx; b.vy -= fy
        # springs
        for a, b, _ in self._edges:
            dx, dy = a.x() - b.x(), a.y() - b.y()
            dist = math.hypot(dx, dy) or 0.01
            force = SPRING_K * (dist - SPRING_LEN)
            fx = force * dx / dist; fy = force * dy / dist
            a.vx -= fx; a.vy -= fy
            b.vx += fx; b.vy += fy
        # integrate + damping
        max_speed = 0.0
        for n in self._nodes.values():
            n.vx *= DAMPING; n.vy *= DAMPING
            n.setPos(n.x() + n.vx, n.y() + n.vy)
            max_speed = max(max_speed, abs(n.vx), abs(n.vy))
        # update edges graphics
        for a, b, line in self._edges:
            line.setLine(QLineF(a.pos(), b.pos()))
        # manage lifecycle
        self._steps_left -= 1
        if self._steps_left <= 0 and max_speed < SPEED_EPS:
            self._timer.stop()
            self.setSceneRect(self.scene.itemsBoundingRect())

# ---------- dialog wrapper --------------------------------------------------
class GraphDialog(QDialog):
    def __init__(self, commits, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ArtGit – Commit Graph")
        lay = QVBoxLayout(self)
        view = CommitGraphView(commits, self)
        lay.addWidget(view)
        self.resize(900, 700)
