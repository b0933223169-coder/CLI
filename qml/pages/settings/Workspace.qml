import QtQuick
import Cool 1.0
import "../../components"

Column {
    id: page
    signal notify(string text)
    width: parent ? parent.width : 0
    spacing: M3.gap

    // 導覽與側邊欄
    Card {
        width: parent.width
        height: b1.height + 44
        Column {
            id: b1
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "NAVIGATION"
                title: "側邊欄與導覽"
                desc: "Caelestia 風格的圖示列；原型固定在左側"
            }

            Pref {
                width: parent.width
                title: "側邊欄展開方式"
                desc: "「滑過」會展開側邊欄並顯示頁面名稱"
                icon: "view_sidebar"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["固定圖示", "滑過展開"]
                    currentIndex: Backend.settings.sidebarMode === "hover" ? 1 : 0
                    onPicked: function (i) { Backend.updateSetting("sidebarMode", ["click", "hover"][i]) }
                }
            }
            Pref {
                width: parent.width
                title: "顯示頁面名稱"
                desc: "滑過展開側邊欄時，在圖示旁顯示名稱"
                icon: "label"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.showNavLabels !== false
                    onToggled: function (v) { Backend.updateSetting("showNavLabels", v) }
                }
            }
            Pref {
                width: parent.width
                title: "底部狀態列"
                desc: "顯示目前帳號、主題與時間"
                icon: "dock_to_bottom"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.showStatusBar !== false
                    onToggled: function (v) { Backend.updateSetting("showStatusBar", v) }
                }
            }
            Pref {
                width: parent.width
                title: "介面密度"
                desc: "調整頁面區塊之間的垂直間距"
                icon: "density_medium"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["緊湊", "標準", "寬鬆"]
                    currentIndex: Backend.settings.density === "compact" ? 0 : Backend.settings.density === "wide" ? 2 : 1
                    onPicked: function (i) { Backend.updateSetting("density", ["compact", "standard", "wide"][i]) }
                }
            }
        }
    }

    // 啟動行為
    Card {
        width: parent.width
        height: b2.height + 44
        Column {
            id: b2
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "STARTUP"
                title: "啟動與預設行為"
                desc: "開啟應用程式時要做的事"
            }

            Pref {
                width: parent.width
                title: "啟動頁面"
                desc: "下次開啟時直接前往"
                icon: "rocket_launch"
                Row {
                    spacing: 6
                    Repeater {
                        model: ["工作台", "帳號", "課程", "報表", "網路"]
                        delegate: Rectangle {
                            height: 30; width: slbl.implicitWidth + 20; radius: 9
                            color: (Backend.settings.startPage || 0) === index ? M3.c.primary : M3.c.surfaceContainerHighest
                            Text {
                                id: slbl; anchors.centerIn: parent; text: modelData
                                color: (Backend.settings.startPage || 0) === index ? M3.c.onPrimary : M3.c.onSurfaceVariant
                                font.pixelSize: M3.tMicro; font.weight: Font.DemiBold
                            }
                            StateLayer { anchors.fill: parent; radius: 9; onClicked: { Backend.updateSetting("startPage", index); page.notify("啟動頁面設為「" + modelData + "」") } }
                        }
                    }
                }
            }
            Pref {
                width: parent.width
                title: "還原上次工作階段"
                desc: "啟動時回到上次使用的頁面"
                icon: "restore_page"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.restoreSession !== false
                    onToggled: function (v) { Backend.updateSetting("restoreSession", v) }
                }
            }
            Pref {
                width: parent.width
                title: "預設登入模式"
                desc: "新增帳號或開啟課程時使用"
                icon: "login"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["有頭", "無頭"]
                    currentIndex: Backend.settings.defaultLoginMode === "headless" ? 1 : 0
                    onPicked: function (i) { Backend.updateSetting("defaultLoginMode", ["headed", "headless"][i]) }
                }
            }
            Pref {
                width: parent.width
                title: "課程開啟後自動關閉"
                desc: "開啟連結組時帶上 cool -g > /timer，時間到 cool.py 自動關閉瀏覽器"
                icon: "timer"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    readonly property var vals: ["", "30:00", "1:00:00", "2:00:00", "3:00:00"]
                    model: ["不限", "30 分", "1 小時", "2 小時", "3 小時"]
                    currentIndex: Math.max(0, vals.indexOf(Backend.settings.launchTimer || ""))
                    onPicked: function (i) { Backend.updateSetting("launchTimer", vals[i]) }
                }
            }
            Pref {
                width: parent.width
                title: "延遲開始"
                desc: "開啟連結組時帶上 cool -g > /delay，等一段時間才開始"
                icon: "schedule"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    readonly property var vals: ["", "5:00", "10:00", "30:00"]
                    model: ["立即", "5 分", "10 分", "30 分"]
                    currentIndex: Math.max(0, vals.indexOf(Backend.settings.launchDelay || ""))
                    onPicked: function (i) { Backend.updateSetting("launchDelay", vals[i]) }
                }
            }
            Pref {
                width: parent.width
                title: "cool.py 來源"
                desc: Backend.cliInfo
                icon: "terminal"
            }
            Pref {
                width: parent.width
                title: "啟動時開啟終端機"
                desc: "與終端機頁面的設定同步"
                icon: "terminal"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.terminalAutoOpen === true
                    onToggled: function (v) { Backend.updateSetting("terminalAutoOpen", v) }
                }
            }
            Pref {
                width: parent.width
                title: "破壞性操作需確認"
                desc: "刪除帳號、課程與紀錄前顯示對話框"
                icon: "warning"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.confirmDestructive !== false
                    onToggled: function (v) { Backend.updateSetting("confirmDestructive", v) }
                }
            }
        }
    }

    // 視窗
    Card {
        width: parent.width
        height: b3.height + 44
        Column {
            id: b3
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "WINDOW"
                title: "視窗與縮放"
                desc: "還原上次的視窗大小與位置；最小 1060×700"
            }

            Pref {
                width: parent.width
                title: "介面縮放"
                desc: "額外縮放整個視窗（80–120%）"
                icon: "zoom_in"
                Slider {
                    width: 260; anchors.verticalCenter: parent.verticalCenter
                    from: 80; to: 120; step: 5; suffix: " %"
                    value: Backend.settings.uiScale ? Backend.settings.uiScale : 100
                    onMoved: function (v) {
                        Backend.updateSetting("uiScale", Math.round(v))
                        page.notify("介面縮放已設為 " + Math.round(v) + "%")
                    }
                }
            }
            Pref {
                width: parent.width
                title: "記住視窗大小"
                desc: "下次開啟時還原視窗尺寸與位置"
                icon: "aspect_ratio"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.rememberWindow !== false
                    onToggled: function (v) { Backend.updateSetting("rememberWindow", v) }
                }
            }
            Pref {
                width: parent.width
                title: "最小化到系統匣"
                desc: "關閉視窗時不結束程式"
                icon: "minimize"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.trayOnClose === true
                    onToggled: function (v) { Backend.updateSetting("trayOnClose", v) }
                }
            }
        }
    }

    // 語言與捷徑
    Row {
        width: parent.width; spacing: 14
        Card {
            width: (parent.width - 14) / 2
            height: 320
            Column {
                id: b4
                x: 22; y: 22; width: parent.width - 44; spacing: 4
                SectionTitle {
                    width: parent.width
                    eyebrow: "LOCALE"
                    title: "語言與格式"
                    desc: "影響日期、時間與數字顯示"
                }
                Pref {
                    width: parent.width
                    title: "介面語言"
                    desc: "目前版本只提供繁體中文"
                    icon: "language"
                    Chip {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "繁體中文"
                        tone: M3.c.secondaryContainer
                        onTone: M3.c.onSecondaryContainer
                    }
                }
                Pref {
                    width: parent.width
                    title: "日期格式"
                    icon: "calendar_month"
                    Seg {
                        anchors.verticalCenter: parent.verticalCenter
                        model: ["2026-11-13", "11/13"]
                        currentIndex: Backend.settings.dateFormat === "short" ? 1 : 0
                        onPicked: function (i) { Backend.updateSetting("dateFormat", ["long", "short"][i]) }
                    }
                }
                Pref {
                    width: parent.width
                    title: "24 小時制"
                    icon: "schedule"
                    Toggle {
                        anchors.verticalCenter: parent.verticalCenter
                        checked: Backend.settings.hour24 !== false
                        onToggled: function (v) { Backend.updateSetting("hour24", v) }
                    }
                }
            }
        }
        Card {
            width: (parent.width - 14) / 2
            height: 320
            Column {
                x: 22; y: 22; width: parent.width - 44; spacing: 8
                SectionTitle {
                    width: parent.width
                    eyebrow: "SHORTCUTS"
                    title: "鍵盤捷徑"
                    desc: "隨時可用"
                }
                Repeater {
                    model: [
                        { k: "Ctrl K", t: "開啟指令面板" },
                        { k: "Ctrl `", t: "開關終端機" },
                        { k: "Esc", t: "關閉面板或對話框" },
                        { k: "Enter", t: "執行選取的指令" },
                        { k: "↑ ↓", t: "在指令面板中移動" }
                    ]
                    delegate: Item {
                        width: parent.width; height: 32
                        Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.t; color: M3.c.onSurface; font.pixelSize: M3.tLabel }
                        Rectangle {
                            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                            height: 24; width: klbl.implicitWidth + 18; radius: 7
                            color: M3.c.surfaceContainerHighest
                            border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.5)
                            Text { id: klbl; anchors.centerIn: parent; text: modelData.k; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.DemiBold; font.family: M3.mono }
                        }
                    }
                }
            }
        }
    }
}
