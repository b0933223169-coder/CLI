import QtQuick
import Cool 1.0
import "../components"

Item {
    id: root
    signal navigate(int page)
    signal notify(string text)

    property string query: ""
    property string cat: "全部"
    // 各分類的展開狀態：預設全部收合；搜尋時自動展開符合的分類
    property var openCats: ({})
    function isOpen(name) { return query.trim() !== "" || openCats[name] === true }
    function toggleCat(name) {
        var m = {}
        for (var k in openCats) m[k] = openCats[k]
        m[name] = !(openCats[name] === true)
        openCats = m
    }
    function setAll(open) {
        var m = {}
        if (open) for (var i = 0; i < categories.length; i++) m[categories[i]] = true
        openCats = m
    }

    readonly property var categories: {
        var seen = {}, out = []
        for (var i = 0; i < Backend.courses.length; i++) {
            var c = Backend.courses[i].category
            if (!seen[c]) { seen[c] = 0; out.push(c) }
            seen[c]++
        }
        return out
    }
    function countIn(c) {
        var n = 0
        for (var i = 0; i < Backend.courses.length; i++)
            if (Backend.courses[i].category === c) n++
        return n
    }
    readonly property var groups: {
        var map = {}, order = []
        var qq = query.trim().toLowerCase()
        for (var i = 0; i < Backend.courses.length; i++) {
            var c = Backend.courses[i]
            if (cat !== "全部" && c.category !== cat) continue
            if (qq !== "" && c.alias.toLowerCase().indexOf(qq) < 0 && c.url.toLowerCase().indexOf(qq) < 0 && c.category.toLowerCase().indexOf(qq) < 0) continue
            if (!map[c.category]) { map[c.category] = []; order.push(c.category) }
            map[c.category].push({ i: i, c: c })
        }
        return order.map(function (k) { return { name: k, items: map[k] } })
    }
    readonly property int totalOpens: {
        var n = 0
        for (var i = 0; i < Backend.courses.length; i++) n += Backend.courses[i].opens
        return n
    }
    readonly property var selectedAccount: Backend.accounts.length > 0 ? Backend.accounts[Backend.selected] : null

    function urlsOf(cat) {
        var out = []
        for (var i = 0; i < Backend.courses.length; i++)
            if (Backend.courses[i].category === cat) out.push(Backend.courses[i].url)
        return out
    }
    function iconFor(c) {
        return c === "聽力" ? "headphones" : c === "閱讀" ? "auto_stories" : c === "影片" ? "movie" : c === "作業" ? "assignment" : "link"
    }

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentHeight: col.height + 48
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: col
            x: 28; y: 6; width: scroll.width - 56; spacing: M3.gap

            // 使用中的帳號 + 批量操作
            Rectangle {
                width: parent.width; height: 76; radius: M3.rLg
                color: M3.c.surfaceContainer
                border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)

                Row {
                    x: 20; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                    Rectangle {
                        width: 40; height: 40; radius: 14; color: M3.c.primaryContainer
                        Text {
                            anchors.centerIn: parent
                            text: root.selectedAccount ? root.selectedAccount.name.charAt(0) : "?"
                            color: M3.c.onPrimaryContainer; font.pixelSize: 16; font.weight: Font.Bold
                        }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
                        Text { text: "使用中的帳號"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                        Text {
                            text: root.selectedAccount ? root.selectedAccount.name + " · " + root.selectedAccount.email : "尚未連結帳號"
                            color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.Medium
                        }
                    }
                    Chip {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.selectedAccount && root.selectedAccount.cookie === "valid" ? "Cookie 有效" : "需要重新登入"
                        icon: root.selectedAccount && root.selectedAccount.cookie === "valid" ? "check_circle" : "error"
                        tone: root.selectedAccount && root.selectedAccount.cookie === "valid" ? M3.c.successContainer : M3.c.errorContainer
                        onTone: root.selectedAccount && root.selectedAccount.cookie === "valid" ? M3.c.success : M3.c.onErrorContainer
                    }
                }

                Row {
                    anchors.right: parent.right; anchors.rightMargin: 18
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Btn {
                        text: "複製全部網址"; icon: "content_copy"; kind: "tonal"; small: true
                        onClicked: {
                            var out = []
                            for (var i = 0; i < Backend.courses.length; i++) out.push(Backend.courses[i].url)
                            Backend.copyText(out.join("\n"))
                        }
                    }
                    Btn {
                        text: "CLI 課程選單"; icon: "terminal"; kind: "outlined"; small: true
                        onClicked: Backend.openCourseMenu()
                    }
                }
            }

            // 統計
            Row {
                width: parent.width; spacing: 12
                Stat {
                    width: (parent.width - 36) / 4
                    icon: "menu_book"; label: "課程網址"; value: Backend.courses.length + " 個"; note: "與 CLI 共用 urls.txt，即時雙向同步"; toneIndex: 0
                }
                Stat {
                    width: (parent.width - 36) / 4
                    icon: "category"; label: "分類"; value: root.categories.length + " 個"; note: "以 # group 儲存在 urls.txt"; toneIndex: 1
                }
                Stat {
                    width: (parent.width - 36) / 4
                    icon: "leaderboard"; label: "最大分類"; value: root.biggest(); note: "以網址數量計算"; toneIndex: 2
                }
                Stat {
                    width: (parent.width - 36) / 4
                    icon: "account_circle"; label: "使用帳號"
                    valueSize: 17
                    value: root.selectedAccount ? root.selectedAccount.name : "未選擇"
                    note: root.selectedAccount ? (root.selectedAccount.cookie === "valid" ? "Cookie 有效" : "需要重新登入") : "請先到帳號頁選擇"
                    toneIndex: 0
                }
            }

            // 工具列
            Item {
                width: parent.width; height: 44

                Rectangle {
                    x: 0; y: 1; width: 300; height: 42; radius: 21
                    color: M3.c.surfaceContainerHighest
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.4)
                    Icon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: "search"; size: 18; color: M3.c.onSurfaceVariant }
                    TextInput {
                        id: searchIn
                        x: 40; width: parent.width - 54; height: parent.height
                        verticalAlignment: TextInput.AlignVCenter
                        color: M3.c.onSurface; font.pixelSize: M3.tBody
                        clip: true; selectByMouse: true
                        selectionColor: M3.c.primary; selectedTextColor: M3.c.onPrimary
                        onTextChanged: root.query = text
                        Text {
                            visible: searchIn.text === ""
                            anchors.verticalCenter: parent.verticalCenter
                            text: "搜尋課程名稱或網址…"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tBody
                        }
                    }
                }

                Flow {
                    x: 312; y: 5
                    width: parent.width - 312 - 330
                    height: 42
                    spacing: 6
                    Repeater {
                        model: ["全部"].concat(root.categories)
                        delegate: Rectangle {
                            height: 34; width: clbl.implicitWidth + 24; radius: 17
                            color: (modelData === "全部" ? root.cat === "全部" : root.cat === modelData) ? M3.c.primary : M3.c.surfaceContainerHighest
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Text {
                                id: clbl; anchors.centerIn: parent
                                text: modelData === "全部" ? "全部 " + Backend.courses.length : modelData + " " + root.countIn(modelData)
                                color: (modelData === "全部" ? root.cat === "全部" : root.cat === modelData) ? M3.c.onPrimary : M3.c.onSurfaceVariant
                                font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                            }
                            StateLayer { anchors.fill: parent; radius: 17; onClicked: root.cat = modelData }
                        }
                    }
                }

                Row {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6
                    Btn {
                        text: "全部展開"; icon: "unfold_more"; kind: "text"; small: true
                        onClicked: root.setAll(true)
                    }
                    Btn {
                        text: "全部收合"; icon: "unfold_less"; kind: "text"; small: true
                        onClicked: root.setAll(false)
                    }
                    Btn {
                        text: "新增網址"; icon: "add"; small: true
                        onClicked: addDlg.open()
                    }
                }
            }

            // 分類群組
            Repeater {
                model: root.groups
                delegate: Rectangle {
                    width: col.width
                    height: root.isOpen(modelData.name) ? 62 + modelData.items.length * 56 + 10 : 62
                    clip: true
                    Behavior on height { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.standard } }
                    radius: M3.rXl
                    color: M3.c.surfaceContainer
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)

                    MouseArea {
                        x: 0; y: 0; width: parent.width; height: 62
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.toggleCat(modelData.name)
                    }
                    Row {
                        x: 20; y: 14; spacing: 10
                        Rectangle {
                            width: 34; height: 34; radius: 12
                            color: M3.tone(index)
                            Icon { anchors.centerIn: parent; name: root.iconFor(modelData.name); size: 17; fill: 1; color: M3.onTone(index) }
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name
                            color: M3.c.onSurface; font.pixelSize: M3.tBodyLg; font.weight: Font.DemiBold
                        }
                        Chip {
                            anchors.verticalCenter: parent.verticalCenter
                            height: 22
                            text: modelData.items.length + " 個"
                            tone: M3.c.surfaceContainerHighest
                            onTone: M3.c.onSurfaceVariant
                        }
                    }

                    Row {
                        anchors.right: parent.right; anchors.rightMargin: 14
                        y: 14; height: 34
                        spacing: 2
                        IconBtn {
                            icon: root.isOpen(modelData.name) ? "expand_less" : "expand_more"
                            tip: root.isOpen(modelData.name) ? "收合" : "展開"
                            size: 30; iconSize: 20
                            onClicked: root.toggleCat(modelData.name)
                        }
                        Btn {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "全部有頭"; icon: "open_in_new"; kind: "text"; small: true
                            onClicked: Backend.openCourses(root.urlsOf(modelData.name), "headed", "分類「" + modelData.name + "」")
                        }
                        Btn {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "全部無頭"; icon: "visibility_off"; kind: "text"; small: true
                            onClicked: Backend.openCourses(root.urlsOf(modelData.name), "headless", "分類「" + modelData.name + "」")
                        }
                        IconBtn {
                            icon: "edit"; tip: "重新命名分類"; size: 30; iconSize: 16
                            onClicked: {
                                catTarget = modelData.name
                                catRenameField.text = modelData.name
                                renameCatDlg.open()
                            }
                        }
                        IconBtn {
                            icon: "delete"; tip: "刪除整個分類"; size: 30; iconSize: 16; danger: true
                            onClicked: {
                                if (Backend.settings.confirmDestructive === false) Backend.removeCategory(catTarget)
                                else { catTarget = modelData.name; removeCatDlg.open() }
                            }
                        }
                    }

                    Column {
                        visible: root.isOpen(modelData.name)
                        x: 14; y: 54; width: parent.width - 28; spacing: 2
                        Repeater {
                            model: modelData.items
                            delegate: Rectangle {
                                width: parent.width; height: 52; radius: 14
                                color: rowHover.containsMouse ? M3.c.surfaceContainerHighest : "transparent"
                                Behavior on color { ColorAnimation { duration: 120 } }

                                Icon {
                                    x: 12; anchors.verticalCenter: parent.verticalCenter
                                    name: "link"; size: 16; color: M3.c.onSurfaceVariant
                                }
                                Column {
                                    x: 36; anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 500
                                    spacing: 1
                                    Text {
                                        text: modelData.c.alias
                                        color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.Medium
                                        elide: Text.ElideRight; width: parent.width
                                    }
                                    Text {
                                        text: modelData.c.url
                                        color: M3.c.onSurfaceVariant; font.pixelSize: 10
                                        elide: Text.ElideMiddle; width: parent.width
                                    }
                                }
                                Chip {
                                    x: parent.width - 478
                                    anchors.verticalCenter: parent.verticalCenter
                                    height: 22
                                    text: modelData.c.category
                                    tone: M3.c.surfaceContainerHighest
                                    onTone: M3.c.onSurfaceVariant
                                }
                                Text {
                                    x: parent.width - 378
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "開啟 " + modelData.c.opens + " 次"
                                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                    width: 76
                                }
                                Text {
                                    x: parent.width - 296
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.c.opened
                                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                    width: 72
                                }
                                Row {
                                    anchors.right: parent.right; anchors.rightMargin: 6
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2
                                    IconBtn {
                                        icon: "open_in_new"; tip: "有頭瀏覽器開啟（可見視窗）"; size: 30; iconSize: 15
                                        onClicked: Backend.openCourses([modelData.c.url], "headed", "")
                                    }
                                    IconBtn {
                                        icon: "visibility_off"; tip: "無頭開啟（背景執行，可在網路紀錄終止）"; size: 30; iconSize: 15
                                        onClicked: Backend.openCourses([modelData.c.url], "headless", "")
                                    }
                                    IconBtn {
                                        icon: "playlist_play"; tip: "開啟「" + modelData.c.alias + "」連結組全部網址（無頭，單一工作階段）"; size: 30; iconSize: 16
                                        onClicked: Backend.openAlias(modelData.c.alias, "headless")
                                    }
                                    IconBtn {
                                        icon: "content_copy"; tip: "複製網址"; size: 30; iconSize: 15
                                        onClicked: Backend.copyText(modelData.c.url)
                                    }
                                    IconBtn {
                                        icon: "delete"; tip: "移除"; size: 30; iconSize: 15; danger: true
                                onClicked: {
                                    if (Backend.settings.confirmDestructive === false) Backend.removeCourse(modelData.i)
                                    else { removeTarget = modelData.i; removeDlg.open() }
                                }
                                    }
                                }
                                MouseArea { id: rowHover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                            }
                        }
                    }
                }
            }

            EmptyState {
                visible: root.groups.length === 0
                width: parent.width; height: 220
                icon: "menu_book"
                title: Backend.courses.length === 0 ? "還沒有課程網址" : "找不到課程"
                desc: Backend.courses.length === 0
                      ? "用「新增網址」加入，或在終端機執行 cool.py -u 匯入課程；清單會存回 urls.txt。"
                      : "換個關鍵字或分類，或新增一個課程網址。"
                actionText: "新增網址"
                onAction: addDlg.open()
            }

            Text {
                text: "課程網址以目前選取帳號的 Cookie 開啟：有頭＝可見的 Edge/Chrome 視窗，無頭＝背景執行（可在「網路紀錄 › 正在運行」終止）；同一連結組一次開啟會記為單一工作階段。清單與 cool -u / cool -g 即時同步。"
                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
            }
        }
    }

    Dialog {
        id: renameCatDlg
        title: "重新命名分類"
        subtitle: "會把這個分類底下的所有連結一起換到新名稱。"
        icon: "drive_file_rename_outline"
        preferredWidth: 500
        Field { id: catRenameField; label: "分類名稱" }
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: renameCatDlg.close() }
            FillSpacer {}
            Btn {
                text: "儲存"; icon: "check"
                onClicked: {
                    if (catRenameField.text.trim() === "") { root.notify("分類名稱不能空白"); return }
                    Backend.renameCategory(catTarget, catRenameField.text)
                    if (root.cat === catTarget) root.cat = catRenameField.text.trim()
                    renameCatDlg.close()
                }
            }
        }
    }

    Dialog {
        id: removeCatDlg
        title: "刪除分類「" + catTarget + "」？"
        subtitle: "會一次移除這個分類與底下的 " + root.countIn(catTarget) + " 個連結；只影響本機清單。"
        icon: "delete_sweep"
        preferredWidth: 500
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: removeCatDlg.close() }
            FillSpacer {}
            Btn {
                text: "刪除整個分類"; icon: "delete"; danger: true
                onClicked: {
                    Backend.removeCategory(catTarget)
                    if (root.cat === catTarget) root.cat = "全部"
                    removeCatDlg.close()
                }
            }
        }
    }

    Dialog {
        id: addDlg
        objectName: "addCourseDlg"
        title: "新增課程網址"
        subtitle: "貼上課程網址，會加入本機清單；大量匯入可在終端機用 cool -u。"
        icon: "add_link"
        preferredWidth: 560
        Field { id: urlField; label: "課程網址" }
        Field { id: catField; label: "分類（例：聽力、閱讀、影片）" }
        Field { id: aliasField; label: "別名（選填）" }
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: addDlg.close() }
            FillSpacer {}
            Btn {
                text: "儲存網址"; icon: "check"
                onClicked: {
                    Backend.addCourse(urlField.text, catField.text, aliasField.text)
                    addDlg.close(); urlField.text = ""; catField.text = ""; aliasField.text = ""
                }
            }
        }
    }

    Dialog {
        id: removeDlg
        title: "移除課程網址？"
        subtitle: "只會從本機清單移除，不會影響 Cool English 上的課程。"
        icon: "link_off"
        preferredWidth: 460
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: removeDlg.close() }
            FillSpacer {}
            Btn {
                text: "移除"; icon: "delete"; danger: true
                onClicked: { Backend.removeCourse(removeTarget); removeDlg.close() }
            }
        }
    }

    property int removeTarget: 0
    property string catTarget: ""

    function biggest() {
        var best = "—", n = -1
        for (var i = 0; i < categories.length; i++) {
            var c = countIn(categories[i])
            if (c > n) { n = c; best = categories[i] }
        }
        return best
    }
}

