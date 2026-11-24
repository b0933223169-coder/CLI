import QtQuick
import "."

// 分段控制：選取的膠囊以彈簧曲線滑動
Rectangle {
    id: seg
    property var model: []
    property int currentIndex: 0
    property var xs: []
    property var ws: []
    signal picked(int index)
    function reg(i, x, w) { var a = xs.slice(), b = ws.slice(); a[i] = x; b[i] = w; xs = a; ws = b }
    implicitHeight: 40
    implicitWidth: row.implicitWidth + 8
    radius: height / 2
    color: M3.c.surfaceContainerHighest
    Rectangle {
        id: ind
        y: 4; height: parent.height - 8
        x: 4 + (seg.xs[seg.currentIndex] !== undefined ? seg.xs[seg.currentIndex] : 0)
        width: seg.ws[seg.currentIndex] !== undefined ? seg.ws[seg.currentIndex] : 0
        radius: height / 2
        color: M3.c.primary
        Behavior on x { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
        Behavior on width { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
    }
    Row {
        id: row
        x: 4; y: 4; height: parent.height - 8
        Repeater {
            model: seg.model
            delegate: Item {
                width: lbl.implicitWidth + 32; height: row.height
                onXChanged: seg.reg(index, x, width)
                onWidthChanged: seg.reg(index, x, width)
                Component.onCompleted: seg.reg(index, x, width)
                Text { id: lbl; anchors.centerIn: parent; text: modelData; font.pixelSize: M3.tBody; font.weight: Font.DemiBold
                    color: index === seg.currentIndex ? M3.c.onPrimary : M3.c.onSurfaceVariant
                    Behavior on color { ColorAnimation { duration: M3.dShort } } }
                StateLayer { anchors.fill: parent; radius: height / 2; onClicked: { seg.currentIndex = index; seg.picked(index) } }
            }
        }
    }
}
