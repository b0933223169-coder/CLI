import QtQuick
import "."

// KPI 卡片：圖示、標籤、數值、補充說明
Rectangle {
    id: stat
    property string icon: "insights"
    property string label: ""
    property string value: ""
    property string note: ""
    property string trend: ""
    property bool good: true
    property int toneIndex: 0
    property int valueSize: M3.tTitle
    property bool interactive: false
    signal clicked()
    implicitHeight: 122
    radius: M3.rLg
    color: M3.c.surfaceContainer
    border.width: 1
    border.color: M3.alpha(M3.c.outlineVariant, 0.35)
    Behavior on color { ColorAnimation { duration: M3.dMed } }
    scale: hit.pressed ? 0.985 : 1
    Behavior on scale { NumberAnimation { duration: M3.dShort; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }

    Rectangle {
        id: tile
        x: 16; y: 14; width: 38; height: 38; radius: 13
        color: M3.tone(stat.toneIndex)
        Icon { anchors.centerIn: parent; name: stat.icon; size: 19; fill: 1; color: M3.onTone(stat.toneIndex) }
    }

    Text {
        x: 16; y: 58
        text: stat.label; color: M3.c.onSurfaceVariant
        font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
    }
    Text {
        x: 16; y: 76
        width: parent.width - 32
        text: stat.value; color: M3.c.onSurface
        font.pixelSize: stat.valueSize; font.weight: Font.DemiBold
        elide: Text.ElideRight
    }
    Row {
        visible: stat.trend !== ""
        anchors.right: parent.right; anchors.rightMargin: 16
        y: 18
        spacing: 4
        Icon {
            anchors.verticalCenter: parent.verticalCenter
            name: stat.good ? "trending_up" : "trending_down"; size: 15
            color: stat.good ? M3.c.success : M3.c.error
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: stat.trend; color: stat.good ? M3.c.success : M3.c.error
            font.pixelSize: M3.tMicro; font.weight: Font.DemiBold
        }
    }
    Text {
        visible: stat.note !== ""
        x: 16; y: 104
        text: stat.note; color: M3.c.onSurfaceVariant
        font.pixelSize: M3.tMicro
        width: parent.width - 32; elide: Text.ElideRight
    }
    StateLayer {
        id: hit; anchors.fill: parent; radius: stat.radius
        visible: stat.interactive; enabled: stat.interactive
        onClicked: stat.clicked()
    }
}
