import QtQuick
import "."

// kind: filled | tonal | outlined | text
Rectangle {
    id: btn
    property string text: ""
    property string icon: ""
    property string kind: "filled"
    property bool small: false
    property bool danger: false
    signal clicked()
    readonly property color bg: kind === "filled" ? (danger ? M3.c.error : M3.c.primary)
                              : kind === "tonal" ? (danger ? M3.c.errorContainer : M3.c.secondaryContainer) : "transparent"
    readonly property color fg: kind === "filled" ? (danger ? M3.c.onError : M3.c.onPrimary)
                              : kind === "tonal" ? (danger ? M3.c.onErrorContainer : M3.c.onSecondaryContainer)
                              : (danger ? M3.c.error : M3.c.primary)
    implicitHeight: small ? 32 : 40
    implicitWidth: row.implicitWidth + (small ? 28 : 40)
    opacity: enabled ? 1 : 0.4
    radius: hit.pressed ? M3.rMd : height / 2
    color: bg
    border.width: kind === "outlined" ? 1 : 0
    border.color: M3.c.outline
    Behavior on radius { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
    Behavior on color { ColorAnimation { duration: M3.dShort } }
    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8
        Icon { visible: btn.icon !== ""; name: btn.icon; size: btn.small ? 16 : 18; color: btn.fg; anchors.verticalCenter: parent.verticalCenter }
        Text { text: btn.text; visible: text !== ""; color: btn.fg; font.pixelSize: btn.small ? M3.tLabel : M3.tBody; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
    }
    StateLayer { id: hit; anchors.fill: parent; radius: btn.radius; color: btn.fg; onClicked: if (btn.enabled) btn.clicked() }
}
