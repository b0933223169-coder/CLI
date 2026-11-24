import QtQuick
import Cool 1.0
import "../../components"

Column {
    id: page
    signal notify(string text)
    width: parent ? parent.width : 0
    spacing: M3.gap

    readonly property var current: Backend.reports.length > 0 ? Backend.reports[Backend.reports.length - 1] : null

    // 門檻
    Card {
        width: parent.width
        height: b1.height + 44
        Column {
            id: b1
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "THRESHOLD"
                title: "學習門檻與警示"
                desc: "低於門檻的月份會在報表與 CLI 預覽中標示"
            }

            Pref {
                width: parent.width
                title: "每月學習門檻"
                desc: "預設 720 分鐘（12 小時）"
                icon: "flag"
                Slider {
                    width: 280; anchors.verticalCenter: parent.verticalCenter
                    from: 4; to: 20; step: 0.5; decimals: 1; suffix: " h"
                    value: Backend.settings.reportThreshold / 60
                    onMoved: function (v) { Backend.updateSetting("reportThreshold", Math.round(v * 60)) }
                }
            }

            Pref {
                width: parent.width
                title: "警示顏色"
                desc: "未達門檻的列與門檻線"
                icon: "palette"
                Row {
                    spacing: 8
                    Repeater {
                        model: ["#ff583d", "#ff9f1c", "#e5b800", "#c04cfd", "#4a78e8", "#00b894"]
                        delegate: Rectangle {
                            width: 26; height: 26; radius: 9
                            anchors.verticalCenter: parent.verticalCenter
                            color: modelData
                            border.width: Backend.settings.reportWarning === modelData ? 2 : 1
                            border.color: Backend.settings.reportWarning === modelData ? M3.c.primary : M3.c.outlineVariant
                            StateLayer { anchors.fill: parent; radius: 9; onClicked: Backend.updateSetting("reportWarning", modelData) }
                        }
                    }
                }
            }

            // 門檻預覽
            Rectangle {
                width: parent.width; height: 78
                radius: M3.rLg
                color: M3.c.surfaceContainerHighest
                Column {
                    x: 16; y: 14; width: parent.width - 32; spacing: 8
                    Row {
                        width: parent.width
                        Text {
                            text: page.current
                                  ? page.current.month + " · " + ((page.current.platform + page.current.video) / 60).toFixed(1) + " h"
                                  : "尚無報表資料"
                            color: M3.c.onSurface; font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                        }
                        FillSpacer {}
                        Chip {
                            height: 22
                            text: page.current ? (page.current.platform + page.current.video >= Backend.settings.reportThreshold ? "已達標" : "未達標") : "未取得"
                            tone: page.current && page.current.platform + page.current.video >= Backend.settings.reportThreshold ? M3.c.successContainer : M3.c.warningContainer
                            onTone: page.current && page.current.platform + page.current.video >= Backend.settings.reportThreshold ? M3.c.success : M3.c.warning
                        }
                    }
                    Rectangle {
                        width: parent.width; height: 8; radius: 4
                        color: M3.alpha(M3.c.onSurface, 0.08)
                        Rectangle {
                            width: parent.width * (page.current
                                ? Math.min(1, (page.current.platform + page.current.video) / (Backend.settings.reportThreshold * 1.6))
                                : 0)
                            height: parent.height; radius: 4; color: M3.c.success
                        }
                        Rectangle {
                            x: parent.width * Math.min(1, 1 / 1.6)
                            width: 2; height: 14; y: -3
                            color: Backend.settings.reportWarning ? Backend.settings.reportWarning : M3.c.error
                        }
                    }
                    Text {
                        text: "門檻線 " + (Backend.settings.reportThreshold / 60).toFixed(1) + " h · 本月 " +
                              (page.current ? ((page.current.platform + page.current.video) / 60).toFixed(1) : "—") + " h"
                        color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                    }
                }
            }
        }
    }

    // 更新與匯出
    Card {
        width: parent.width
        height: b2.height + 44
        Column {
            id: b2
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "FETCH & EXPORT"
                title: "更新與匯出"
                desc: "自動取得報表與預設匯出格式"
            }

            Pref {
                width: parent.width
                title: "自動更新報表"
                desc: "依更新間隔在背景取得目前帳號的報表"
                icon: "autorenew"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.reportAutoRefresh === true
                    onToggled: function (v) { Backend.updateSetting("reportAutoRefresh", v) }
                }
            }
            Pref {
                width: parent.width
                title: "更新間隔"
                desc: "自動更新的最短間隔"
                icon: "timer"
                Slider {
                    width: 240; anchors.verticalCenter: parent.verticalCenter
                    from: 5; to: 120; step: 5; suffix: " 分"
                    value: Backend.settings.reportInterval ? Backend.settings.reportInterval : 60
                    onMoved: function (v) { Backend.updateSetting("reportInterval", Math.round(v)) }
                }
            }
            Pref {
                width: parent.width
                title: "預設匯出格式"
                desc: "報表頁「匯出」按鈕的預設值"
                icon: "download"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["CLI", "JSON", "CSV"]
                    currentIndex: Backend.settings.exportFormat === "json" ? 1 : Backend.settings.exportFormat === "csv" ? 2 : 0
                    onPicked: function (i) { Backend.updateSetting("exportFormat", ["cli", "json", "csv"][i]) }
                }
            }
            Pref {
                width: parent.width
                title: "匯出時包含影片"
                desc: "影片時間會計入合計"
                icon: "movie"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.reportIncludeVideo !== false
                    onToggled: function (v) { Backend.updateSetting("reportIncludeVideo", v) }
                }
            }
        }
    }

    // 顯示
    Card {
        width: parent.width
        height: b3.height + 44
        Column {
            id: b3
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "DISPLAY"
                title: "報表顯示"
                desc: "表格與圖表的細節"
            }

            Pref {
                width: parent.width
                title: "顯示練習時數"
                desc: "平台時數減去影片時數"
                icon: "calculate"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.showPractice !== false
                    onToggled: function (v) { Backend.updateSetting("showPractice", v) }
                }
            }
            Pref {
                width: parent.width
                title: "顯示門檻線"
                desc: "在 12 個月圖表上畫出警示線"
                icon: "show_chart"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.showThreshold !== false
                    onToggled: function (v) { Backend.updateSetting("showThreshold", v) }
                }
            }
            Pref {
                width: parent.width
                title: "月份排列順序"
                desc: "套用到報表表格與 CLI 預覽；圖表仍由舊到新"
                icon: "sort"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["最新在前", "最早在前"]
                    currentIndex: Backend.settings.reportSort === "oldest" ? 1 : 0
                    onPicked: function (i) { Backend.updateSetting("reportSort", ["newest", "oldest"][i]) }
                }
            }
            Pref {
                width: parent.width
                title: "預設帳號"
                desc: "開啟報表頁時自動選取"
                icon: "person"
                Row {
                    spacing: 6
                    Repeater {
                        model: Backend.accounts
                        delegate: Rectangle {
                            height: 30; width: dlbl.implicitWidth + 20; radius: 9
                            color: Backend.settings.defaultAccount === modelData.email ? M3.c.primary : M3.c.surfaceContainerHighest
                            Text {
                                id: dlbl; anchors.centerIn: parent; text: modelData.name
                                color: Backend.settings.defaultAccount === modelData.email ? M3.c.onPrimary : M3.c.onSurfaceVariant
                                font.pixelSize: M3.tMicro; font.weight: Font.DemiBold
                            }
                            StateLayer {
                                anchors.fill: parent; radius: 9
                                onClicked: { Backend.updateSetting("defaultAccount", modelData.email); page.notify("預設帳號設為 " + modelData.name) }
                            }
                        }
                    }
                }
            }
            Pref {
                width: parent.width
                title: "重新整理全部報表"
                desc: "依序向所有帳號取得最新資料"
                icon: "refresh"
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "用 CLI 更新"; icon: "refresh"; kind: "outlined"; small: true
                    onClicked: Backend.openReportCli()
                }
            }
        }
    }
}
