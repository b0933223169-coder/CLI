import QtQuick
import "."

Text {
    property string name: ""
    property int size: 24
    property real fill: 0
    text: name
    color: M3.c.onSurface
    font.family: "Material Symbols Rounded"
    font.pixelSize: size
    font.variableAxes: ({ "FILL": fill, "wght": 400, "GRAD": 0, "opsz": 24 })
    verticalAlignment: Text.AlignVCenter
    horizontalAlignment: Text.AlignHCenter
    renderType: Text.NativeRendering
    Behavior on fill { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.standard } }
}
