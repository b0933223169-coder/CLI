import QtQuick
import Cool 1.0
import "../../components"

Column {
    id: page
    signal notify(string text)
    width: parent ? parent.width : 0
    spacing: M3.gap

    property bool confirmClear: false

    // 保留策略
    Card {
        id: retCard
        width: parent.width
        height: b1.height + 44
        property int retMin: Math.max(1, Backend.settings.retention || 1440)
        property int unitMul: retMin % 1440 === 0 ? 1440 : (retMin % 60 === 0 ? 60 : 1)
        Column {
            id: b1
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "RETENTION"
                title: "保留策略"
                desc: "網路紀錄不設工作階段或事件筆數上限；可永久保留、停用，或在工作階段結束後自動刪除整筆舊紀錄"
            }

            Pref {
                width: parent.width
                title: "紀錄方式"
                desc: "停用時開啟課程仍會執行，進度直接顯示在「正在運行」，不保存為網路事件"
                icon: "policy"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["永久保留", "自動刪除", "停用新紀錄"]
                    currentIndex: Backend.settings.networkMode === "expire" ? 1 : Backend.settings.networkMode === "disabled" ? 2 : 0
                    onPicked: function (i) { Backend.updateSetting("networkMode", ["keep", "expire", "disabled"][i]) }
                }
            }
            Pref {
                width: parent.width
                visible: Backend.settings.networkMode === "expire"
                title: "保留時間"
                desc: "工作階段結束後超過這段時間，整筆紀錄會自動刪除"
                icon: "event_repeat"
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12
                    Slider {
                        width: 200; anchors.verticalCenter: parent.verticalCenter
                        from: 1; to: 90; step: 1
                        suffix: retCard.unitMul === 1440 ? " 天" : retCard.unitMul === 60 ? " 小時" : " 分鐘"
                        value: Math.max(1, Math.round(retCard.retMin / retCard.unitMul))
                        onMoved: function (v) { Backend.updateSetting("retention", Math.round(v) * retCard.unitMul) }
                    }
                    Seg {
                        anchors.verticalCenter: parent.verticalCenter
                        model: ["分鐘", "小時", "天"]
                        currentIndex: retCard.unitMul === 1440 ? 2 : retCard.unitMul === 60 ? 1 : 0
                        onPicked: function (i) {
                            var cur = Math.max(1, Math.round(retCard.retMin / retCard.unitMul))
                            Backend.updateSetting("retention", cur * [1, 60, 1440][i])
                        }
                    }
                }
            }
        }
    }

    // 擷取
    Card {
        width: parent.width
        height: b2.height + 44
        Column {
            id: b2
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "CAPTURE"
                title: "擷取內容"
                desc: "原始數據越多，佔用的空間越大"
            }

            Pref {
                width: parent.width
                title: "保留原始數據"
                desc: "以原始位元組、不遮蔽、不截斷、不加密寫入本機；本文可能含密碼、Cookie 與權杖，請自行保護。不追溯既有紀錄"
                icon: "data_object"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.captureRaw === true
                    onToggled: function (v) { Backend.updateSetting("captureRaw", v) }
                }
            }
            Pref {
                width: parent.width
                title: "只記錄失敗請求"
                desc: "降低容量，適合長期觀察"
                icon: "report"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.onlyFailures === true
                    onToggled: function (v) { Backend.updateSetting("onlyFailures", v) }
                }
            }
        }
    }

    // 儲存
    Card {
        width: parent.width
        height: b3.height + 44
        Column {
            id: b3
            x: 22; y: 22; width: parent.width - 44; spacing: 12

            SectionTitle {
                width: parent.width
                eyebrow: "STORAGE"
                title: "儲存與清除"
                desc: "所有紀錄都保存在本機"
                Btn {
                    text: "匯出全部"; icon: "download"; kind: "outlined"; small: true
                    onClicked: Backend.exportSessions()
                }
            }

            Row {
                width: parent.width; spacing: 16
                Column {
                    width: parent.width - 280; spacing: 6
                    Row {
                        width: parent.width
                        Text { text: "目前使用量"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                        FillSpacer {}
                        Text { text: page.usage() + " / 50 MB"; color: M3.c.onSurface; font.pixelSize: M3.tMicro; font.weight: Font.Bold }
                    }
                    ProgressBar {
                        width: parent.width; thickness: 8
                        value: Math.min(1, page.usageMb() / 50)
                        tone: page.usageMb() > 40 ? M3.c.error : M3.c.primary
                    }
                    Text {
                        text: Backend.sessions.length + " 筆工作階段 · " + page.eventCount() + " 個事件 · 保留 " +
                              Math.max(1, Math.round((Backend.settings.retention || 1440) / 1440)) + " 天"
                        color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                    }
                }
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "清除全部紀錄"; icon: "delete_sweep"; kind: "filled"; small: true; danger: true
                    onClicked: page.confirmClear = true
                }
            }

            Rectangle {
                visible: page.confirmClear
                width: parent.width; height: 56; radius: M3.rMd
                color: M3.c.errorContainer
                Row {
                    x: 16; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                    Icon { anchors.verticalCenter: parent.verticalCenter; name: "warning"; size: 18; fill: 1; color: M3.c.onErrorContainer }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "確定要清除全部 " + Backend.sessions.length + " 筆紀錄嗎？"
                        color: M3.c.onErrorContainer; font.pixelSize: M3.tLabel
                    }
                }
                Row {
                    anchors.right: parent.right; anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6
                    Btn { text: "取消"; kind: "text"; small: true; onClicked: page.confirmClear = false }
                    Btn {
                        text: "確認清除"; icon: "delete_sweep"; danger: true; small: true
                        onClicked: { Backend.clearSessions(); page.confirmClear = false }
                    }
                }
            }

            Text {
                text: "路徑：" + Backend.exportDir
                color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.family: M3.mono
            }
        }
    }

    function usageMb() {
        var bytes = 0
        for (var i = 0; i < Backend.sessions.length; i++) bytes += Backend.sessions[i].bytes || 0
        return bytes / 1048576
    }
    function usage() { return usageMb().toFixed(1) + " MB" }
    function eventCount() {
        var n = 0
        for (var i = 0; i < Backend.sessions.length; i++) n += Backend.sessions[i].events.length
        return n
    }
}
