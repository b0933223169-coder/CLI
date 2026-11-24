import QtQuick
import Cool 1.0
import "../../components"

Column {
    id: page
    signal notify(string text)
    width: parent ? parent.width : 0
    spacing: M3.gap

    // 預覽
    Card {
        width: parent.width
        height: body0.height + 44
        Column {
            id: body0
            x: 22; y: 22; width: parent.width - 44; spacing: 12

            SectionTitle {
                width: parent.width
                eyebrow: "TERMINAL PREVIEW"
                title: "終端機預覽"
                desc: "顏色會同步到 CLI 的 colors.json 與下方預覽"
                Btn {
                    text: "開啟終端機"; icon: "terminal"; kind: "tonal"; small: true
                    onClicked: Backend.launchTerminal(Backend.defaultTerminal)
                }
            }

            Rectangle {
                width: parent.width; height: 138
                radius: M3.rLg
                color: Backend.settings.terminalBg
                border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)
                clip: true

                Column {
                    x: 16; y: 12; spacing: 4
                    Text {
                        text: "cool 終端機 · " + M3.mono
                        color: Backend.settings.terminalText; opacity: 0.7
                        font.family: M3.mono; font.pixelSize: Backend.settings.terminalFontSize
                    }
                    Text {
                        text: "❯ cool -l"
                        color: Backend.settings.terminalCursor
                        font.family: M3.mono; font.pixelSize: Backend.settings.terminalFontSize; font.weight: Font.Bold
                    }
                    Text {
                        text: "在抽屜內的內嵌終端機執行 cool.py（不開外部視窗）"
                        color: Backend.settings.terminalText
                        font.family: M3.mono; font.pixelSize: Backend.settings.terminalFontSize - 1
                    }
                    Text {
                        text: "登入、課程與學習時間都在同一個內嵌終端完成"
                        color: Backend.settings.terminalText; opacity: 0.85
                        font.family: M3.mono; font.pixelSize: Backend.settings.terminalFontSize - 1
                    }
                    Text {
                        text: "❯ "
                        color: Backend.settings.terminalCursor
                        font.family: M3.mono; font.pixelSize: Backend.settings.terminalFontSize
                        Rectangle {
                            x: parent.width + 2; y: 3; width: 7; height: parent.height - 6
                            color: Backend.settings.terminalCursor
                        }
                    }
                }
                Text {
                    anchors.right: parent.right; anchors.rightMargin: 14; anchors.bottom: parent.bottom; anchors.bottomMargin: 10
                    text: "字級 " + Backend.settings.terminalFontSize + " · " + M3.mono
                    color: Backend.settings.terminalText; opacity: 0.5
                    font.pixelSize: 9
                }
            }
        }
    }

    // 字型
    Card {
        width: parent.width
        height: body1.height + 44
        Column {
            id: body1
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "FONT"
                title: "預覽字型與字級"
                desc: "下方預覽與抽屜裡的內嵌終端機共用同一組字型"
            }

            Pref {
                width: parent.width
                title: "終端字級"
                desc: "11–18 pt，預設 13"
                icon: "format_size"
                Slider {
                    width: 260; anchors.verticalCenter: parent.verticalCenter
                    from: 11; to: 18; step: 1; suffix: " pt"
                    value: Backend.settings.terminalFontSize
                    onMoved: function (v) { Backend.updateSetting("terminalFontSize", Math.round(v)) }
                }
            }

            Pref {
                width: parent.width
                title: "字型家族"
                desc: "預覽與內嵌終端機使用的等寬字型，缺少時會退回系統預設"
                icon: "font_download"
                Row {
                    spacing: 6
                    Repeater {
                        model: ["Cascadia Mono", "Consolas", "JetBrains Mono", "Courier New"]
                        delegate: Rectangle {
                            height: 32; width: flbl.implicitWidth + 22; radius: 10
                            color: Backend.settings.terminalFont === modelData ? M3.c.primary : M3.c.surfaceContainerHighest
                            Text {
                                id: flbl; anchors.centerIn: parent; text: modelData
                                color: Backend.settings.terminalFont === modelData ? M3.c.onPrimary : M3.c.onSurfaceVariant
                                font.pixelSize: M3.tMicro; font.family: modelData; font.weight: Font.DemiBold
                            }
                            StateLayer { anchors.fill: parent; radius: 10; onClicked: Backend.updateSetting("terminalFont", modelData) }
                        }
                    }
                }
            }

            Pref {
                width: parent.width
                title: "終端機位置"
                desc: "上下排列或左右排列，拖曳抽屜邊緣可調整大小"
                icon: "view_sidebar"
                Row {
                    spacing: 6
                    Repeater {
                        model: [{ id: "bottom", label: "下方", icon: "bottom_panel_open" }, { id: "right", label: "右側", icon: "right_panel_open" }]
                        delegate: Rectangle {
                            readonly property bool on: (Backend.settings.terminalDock || "bottom") === modelData.id
                            height: 32; width: dlbl.implicitWidth + 44; radius: 10
                            color: on ? M3.c.primary : M3.c.surfaceContainerHighest
                            Row {
                                anchors.centerIn: parent; spacing: 6
                                Icon { name: modelData.icon; size: 16; color: on ? M3.c.onPrimary : M3.c.onSurfaceVariant; anchors.verticalCenter: parent.verticalCenter }
                                Text {
                                    id: dlbl; text: modelData.label
                                    color: on ? M3.c.onPrimary : M3.c.onSurfaceVariant
                                    font.pixelSize: M3.tMicro; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                            StateLayer { anchors.fill: parent; radius: 10; onClicked: Backend.updateSetting("terminalDock", modelData.id) }
                        }
                    }
                }
            }

            Pref {
                width: parent.width
                title: "啟動的終端"
                desc: "「＋」會列出這台電腦真的有的終端機（PowerShell 7／Windows PowerShell／cmd／Visual Studio 開發者 shell／Git Bash／WSL），每個開啟後都自動執行 cool.py"
                icon: "code"
                Chip {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Backend.defaultTerminalProfile
                    tone: M3.c.surfaceContainerHighest
                    onTone: M3.c.onSurfaceVariant
                }
            }
        }
    }

    // 配色
    Card {
        width: parent.width
        height: body2.height + 44
        Column {
            id: body2
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "COLORS"
                title: "終端機配色"
                desc: "游標、文字與背景色"
            }

            Pref {
                width: parent.width
                title: "游標顏色"
                icon: "border_color"
                Row {
                    spacing: 8
                    Repeater {
                        model: ["#ff795b", "#ffc928", "#69db7c", "#4dd0e1", "#74a8ff", "#ff6ad5", "#f4f7fb"]
                        delegate: Rectangle {
                            width: 26; height: 26; radius: 9
                            anchors.verticalCenter: parent.verticalCenter
                            color: modelData
                            border.width: Backend.settings.terminalCursor === modelData ? 2 : 1
                            border.color: Backend.settings.terminalCursor === modelData ? M3.c.primary : M3.c.outlineVariant
                            StateLayer { anchors.fill: parent; radius: 9; onClicked: Backend.updateSetting("terminalCursor", modelData) }
                        }
                    }
                }
            }
            Pref {
                width: parent.width
                title: "文字顏色"
                icon: "text_fields"
                Row {
                    spacing: 8
                    Repeater {
                        model: ["#ffe5dc", "#f4f7fb", "#c7f2e3", "#e6d6ff", "#d7dde5", "#ffe066"]
                        delegate: Rectangle {
                            width: 26; height: 26; radius: 9
                            anchors.verticalCenter: parent.verticalCenter
                            color: modelData
                            border.width: Backend.settings.terminalText === modelData ? 2 : 1
                            border.color: Backend.settings.terminalText === modelData ? M3.c.primary : M3.c.outlineVariant
                            StateLayer { anchors.fill: parent; radius: 9; onClicked: Backend.updateSetting("terminalText", modelData) }
                        }
                    }
                }
            }
            Pref {
                width: parent.width
                title: "背景顏色"
                icon: "format_color_fill"
                Row {
                    spacing: 8
                    Repeater {
                        model: ["#2b100e", "#12161c", "#101a16", "#161022", "#1d2024", "#0d1117"]
                        delegate: Rectangle {
                            width: 26; height: 26; radius: 9
                            anchors.verticalCenter: parent.verticalCenter
                            color: modelData
                            border.width: Backend.settings.terminalBg === modelData ? 2 : 1
                            border.color: Backend.settings.terminalBg === modelData ? M3.c.primary : M3.c.outlineVariant
                            StateLayer { anchors.fill: parent; radius: 9; onClicked: Backend.updateSetting("terminalBg", modelData) }
                        }
                    }
                }
            }
        }
    }

    // 畫面
    Card {
        width: parent.width
        height: body3.height + 44
        Column {
            id: body3
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "SCREEN"
                title: "終端機畫面"
                desc: "真正 ConPTY 終端，最多回顧 2000 行歷史（滑鼠滾輪）"
            }

            Pref {
                width: parent.width
                title: "清除畫面"
                desc: "只清除抽屜裡的畫面，不會停止執行中的 shell"
                icon: "delete_sweep"
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "清除"; icon: "delete_sweep"; kind: "outlined"; small: true; danger: true
                    onClicked: Backend.clearTerminal()
                }
            }

            Pref {
                width: parent.width
                title: "選取與複製"
                desc: "在終端機裡拖曳選取文字，按 Ctrl+C 或 Ctrl+Shift+C 複製；雙擊可選一個詞"
                icon: "content_copy"
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "複製畫面"; icon: "content_copy"; kind: "outlined"; small: true
                    onClicked: Backend.copyTerminalSelection(Backend.activeTerminalId)
                }
            }

            Pref {
                width: parent.width
                title: "貼上"
                desc: "Ctrl+Shift+V 或 Shift+Insert；沒有選取時 Ctrl+C 才送出中斷訊號給程式"
                icon: "content_paste"
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "貼上"; icon: "content_paste"; kind: "outlined"; small: true
                    onClicked: Backend.pasteTerminal(Backend.activeTerminalId)
                }
            }
        }
    }
}
