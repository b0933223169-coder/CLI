import QtQuick
import "."

// Material 風格滑桿：拖曳、點擊軌道、可選刻度
Item {
    id: s
    property real value: 0
    property real from: 0
    property real to: 1
    property real step: 0
    property string suffix: ""
    property int decimals: 0
    property bool showValue: true
    signal moved(real v)
    implicitHeight: 48
    implicitWidth: 220

    // 拖曳中的暫存值：不直接改 value，才不會把使用者綁定的 value（例如 Backend 設定）弄斷；
    // 放開後恢復跟隨外部值，所以主題切換或其他地方改了設定，滑桿一定會同步。
    property real dragValue: NaN
    readonly property real current: isNaN(dragValue) ? value : dragValue
    readonly property real ratio: Math.max(0, Math.min(1, (current - from) / Math.max(0.000001, to - from)))
    readonly property string shown: Number(current).toFixed(decimals) + suffix

    function apply(px) {
        var t = Math.max(0, Math.min(1, px / Math.max(1, track.width)))
        var v = from + t * (to - from)
        if (step > 0) v = Math.round(v / step) * step
        v = Math.max(from, Math.min(to, v))
        if (v !== s.current) { s.dragValue = v; s.moved(v) }
    }

    Text {
        visible: s.showValue
        anchors.right: parent.right
        y: -2
        text: s.shown; color: M3.c.primary
        font.pixelSize: M3.tLabel; font.weight: Font.Bold
    }

    Rectangle {
        id: track
        anchors.left: parent.left
        anchors.right: parent.right
        y: 24; height: 6; radius: 3
        color: M3.c.surfaceContainerHighest
        Rectangle {
            width: track.width * s.ratio; height: parent.height; radius: 3
            color: M3.c.primary
            Behavior on width { NumberAnimation { duration: M3.dShort } }
        }
    }
    Rectangle {
        id: knob
        x: track.width * s.ratio - width / 2
        y: 27 - height / 2
        width: hit.pressed || hit.containsMouse ? 22 : 18
        height: width; radius: width / 2
        color: M3.c.primary
        border.width: 2; border.color: M3.c.surface
        Behavior on width { NumberAnimation { duration: M3.dShort; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
        Behavior on x { NumberAnimation { duration: M3.dShort } }
    }
    MouseArea {
        id: hit
        anchors.fill: parent
        anchors.topMargin: 10
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        preventStealing: true
        onPressed: (m) => s.apply(m.x)
        onPositionChanged: (m) => { if (pressed) s.apply(m.x) }
        onReleased: s.dragValue = NaN
        onCanceled: s.dragValue = NaN
    }
}
