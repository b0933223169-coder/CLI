import QtQuick

// 放在內層捲動區「下方」（先宣告）：內層捲到頭、不再處理滾輪時，事件會落到這裡被吃掉，
// 不會繼續傳給外層頁面造成整頁跟著捲動。內容短到不需要捲動時自動停用，滾輪仍可捲外層頁面。
// 用法：WheelGuard { target: 內層捲動區的 id }
MouseArea {
    property Flickable target
    anchors.fill: target
    enabled: target !== null && target.contentHeight > target.height + 1
    acceptedButtons: Qt.NoButton
    onWheel: function (wheel) { wheel.accepted = true }
}
