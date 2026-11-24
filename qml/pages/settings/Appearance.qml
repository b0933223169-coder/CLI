import QtQuick
import Cool 1.0
import "../../components"

Column {
    id: page
    signal notify(string text)
    width: parent ? parent.width : 0
    spacing: M3.gap

    readonly property var groups: ["暖色", "冷色", "自然", "鮮明"]

    // 主題庫
    Card {
        width: parent.width
        height: body1.height + 44

        Column {
            id: body1
            x: 22; y: 22; width: parent.width - 44; spacing: 14

            SectionTitle {
                width: parent.width
                eyebrow: "THEME LIBRARY"
                title: "24 組主題"
                desc: "與桌面版相同的 24 組高辨識主題；套用時同步更新介面與終端配色"
                Btn {
                    text: Backend.dark ? "暗色" : "亮色"
                    icon: Backend.dark ? "dark_mode" : "light_mode"
                    kind: "tonal"; small: true
                    onClicked: Backend.setScheme(Backend.seed, Backend.variant, !Backend.dark, Backend.contrast)
                }
            }

            Repeater {
                model: page.groups
                delegate: Column {
                    width: parent.width; spacing: 8

                    Row {
                        width: parent.width; height: 18; spacing: 8
                        Text { anchors.verticalCenter: parent.verticalCenter; text: modelData; color: M3.c.onSurface; font.pixelSize: M3.tLabel; font.weight: Font.Bold }
                        Rectangle { width: 26; height: 1; color: M3.alpha(M3.c.outlineVariant, 0.7); anchors.verticalCenter: parent.verticalCenter }
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "6 組"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                    }

                    Row {
                        width: parent.width; spacing: 10
                        Repeater {
                            model: Backend.themes.filter(function (t) { return t.group === modelData })
                            delegate: Item {
                                id: themeCard
                                width: (parent.width - 50) / 6; height: 92

                                Rectangle {
                                    width: parent.width; height: 58
                                    radius: M3.rMd
                                    border.width: Backend.settings.themeId === modelData.id ? 2 : 1
                                    border.color: Backend.settings.themeId === modelData.id ? M3.c.primary : M3.alpha(M3.c.outlineVariant, 0.5)
                                    clip: true
                                    gradient: Gradient {
                                        orientation: Gradient.Horizontal
                                        GradientStop { position: 0; color: modelData.bg }
                                        GradientStop { position: 0.55; color: modelData.surface }
                                        GradientStop { position: 1; color: modelData.seed }
                                    }
                                    Rectangle {
                                        visible: Backend.settings.themeId === modelData.id
                                        anchors.right: parent.right; anchors.rightMargin: 7; anchors.top: parent.top; anchors.topMargin: 7
                                        width: 20; height: 20; radius: 10
                                        color: M3.c.surface
                                        Icon { anchors.centerIn: parent; name: "check"; size: 13; color: M3.c.primary }
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            Backend.applyTheme(modelData.id, modelData.seed, modelData.dark)
                                            page.notify("已套用「" + modelData.name + "」")
                                        }
                                    }
                                }
                                Text {
                                    y: 64; width: parent.width
                                    text: modelData.name; color: M3.c.onSurface
                                    font.pixelSize: M3.tMicro; font.weight: Font.Medium
                                    elide: Text.ElideRight
                                }
                                Text {
                                    y: 79; width: parent.width
                                    text: (modelData.dark ? "深色 · " : "淺色 · ") + modelData.seed; color: M3.c.onSurfaceVariant
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // 種子色與變體
    Card {
        width: parent.width
        height: body2.height + 44
        Column {
            id: body2
            x: 22; y: 22; width: parent.width - 44; spacing: 14

            SectionTitle {
                width: parent.width
                eyebrow: "SEED & VARIANT"
                title: "種子色與配色變體"
                desc: "種子色是演算法的起點；變體決定色調分佈與飽和度"
            }

            Row {
                width: parent.width; spacing: 10
                Repeater {
                    model: Backend.seeds
                    delegate: Item {
                        width: 40; height: 40
                        Rectangle {
                            anchors.fill: parent; radius: 14
                            color: modelData
                            border.width: Backend.seed === modelData ? 3 : 1
                            border.color: Backend.seed === modelData ? M3.c.onSurface : M3.alpha(M3.c.outlineVariant, 0.4)
                            Icon {
                                anchors.centerIn: parent
                                visible: Backend.seed === modelData
                                name: "check"; size: 16; color: "#ffffff"
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    Backend.setScheme(modelData, Backend.variant, Backend.dark, Backend.contrast)
                                    Backend.updateSetting("seed", modelData)
                                }
                            }
                        }
                    }
                }
                FillSpacer {}
                Text { anchors.verticalCenter: parent.verticalCenter; text: Backend.seed; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; font.family: M3.mono }
            }

            Flow {
                width: parent.width; spacing: 8
                Repeater {
                    model: Backend.variants
                    delegate: Rectangle {
                        height: 34; width: vlbl.implicitWidth + 24; radius: 17
                        color: Backend.variant === modelData.key ? M3.c.primary : M3.c.surfaceContainerHighest
                        Behavior on color { ColorAnimation { duration: 120 } }
                        Text {
                            id: vlbl; anchors.centerIn: parent
                            text: modelData.name
                            color: Backend.variant === modelData.key ? M3.c.onPrimary : M3.c.onSurfaceVariant
                            font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                        }
                        StateLayer {
                            anchors.fill: parent; radius: 17
                            onClicked: {
                                Backend.setScheme(Backend.seed, modelData.key, Backend.dark, Backend.contrast)
                                Backend.updateSetting("variant", modelData.key)
                            }
                        }
                    }
                }
            }
        }
    }

    // 介面字級與動態
    Card {
        width: parent.width
        height: body3.height + 44
        Column {
            id: body3
            x: 22; y: 22; width: parent.width - 44; spacing: 8

            SectionTitle {
                width: parent.width
                eyebrow: "TYPOGRAPHY & MOTION"
                title: "介面字級與動態"
                desc: "字級 10–24，預設 14；對比 0–100%"
            }

            Pref {
                width: parent.width
                title: "介面字級"
                desc: "影響所有頁面、選單與對話框的文字"
                icon: "text_fields"
                Slider {
                    width: 260; anchors.verticalCenter: parent.verticalCenter
                    from: 10; to: 24; step: 1; suffix: " pt"
                    value: Backend.settings.fontSize
                    onMoved: function (v) { Backend.updateSetting("fontSize", Math.round(v)) }
                }
            }

            Pref {
                width: parent.width
                title: "介面字體"
                desc: "只影響介面文字；終端機維持等寬字體"
                icon: "font_download"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["系統", "Segoe UI", "Arial", "Consolas"]
                    currentIndex: ({ "system": 0, "segoe": 1, "arial": 2, "consolas": 3 })[Backend.settings.fontFamily || "system"]
                    onPicked: function (i) { Backend.updateSetting("fontFamily", ["system", "segoe", "arial", "consolas"][i]) }
                }
            }

            Pref {
                width: parent.width
                title: "反轉介面文字顏色"
                desc: "文字改用互補色相（自動維持 7:1 以上對比），不改背景、卡片與終端"
                icon: "invert_colors"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.invertText === true
                    onToggled: function (v) { Backend.updateSetting("invertText", v) }
                }
            }

            Pref {
                width: parent.width
                title: "配色對比"
                desc: "提高文字與容器的對比度"
                icon: "contrast"
                Slider {
                    width: 260; anchors.verticalCenter: parent.verticalCenter
                    from: 0; to: 100; step: 10; suffix: " %"
                    value: Backend.contrast * 100
                    onMoved: function (v) { Backend.setScheme(Backend.seed, Backend.variant, Backend.dark, v / 100) }
                }
            }

            Pref {
                width: parent.width
                title: "圓角風格"
                desc: "整體卡片的圓角程度"
                icon: "rounded_corner"
                Seg {
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["方正", "標準", "柔和"]
                    currentIndex: Backend.settings.radiusStyle === "sharp" ? 0 : Backend.settings.radiusStyle === "soft" ? 2 : 1
                    onPicked: function (i) { Backend.updateSetting("radiusStyle", ["sharp", "standard", "soft"][i]) }
                }
            }

            Pref {
                width: parent.width
                title: "減少動態效果"
                desc: "關閉彈簧與轉場動畫（無障礙）"
                icon: "animation"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.reduceMotion === true
                    onToggled: function (v) { Backend.updateSetting("reduceMotion", v) }
                }
            }
        }
    }
}
