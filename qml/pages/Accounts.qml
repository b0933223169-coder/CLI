import QtQuick
import QtQuick.Dialogs
import Cool 1.0
import "../components"

Item {
    id: root
    signal navigate(int page)
    signal notify(string text)

    property string query: ""
    property int filter: 0
    readonly property var filters: ["全部", "有效", "過期", "待檢查"]
    readonly property var filterKeys: ["", "valid", "expired", "unknown"]
    readonly property var shown: {
        var out = []
        var qq = query.trim().toLowerCase()
        var key = filterKeys[filter]
        for (var i = 0; i < Backend.accounts.length; i++) {
            var a = Backend.accounts[i]
            if (key !== "" && a.cookie !== key) continue
            if (qq !== "" && a.name.toLowerCase().indexOf(qq) < 0 && a.email.toLowerCase().indexOf(qq) < 0) continue
            out.push(i)
        }
        return out
    }
    readonly property var acc: Backend.accounts.length > 0 ? Backend.accounts[Backend.selected] : null
    readonly property int validCount: countOf("valid")
    readonly property int expiredCount: countOf("expired")
    readonly property int unknownCount: countOf("unknown")

    function shownEmail(value) {
        var email = String(value || "")
        if (Backend.settings.maskSensitive !== true) return email
        var at = email.indexOf("@")
        return at > 0 ? "••••" + email.substring(at) : "••••"
    }

    function countOf(k) {
        var n = 0
        for (var i = 0; i < Backend.accounts.length; i++) if (Backend.accounts[i].cookie === k) n++
        return n
    }
    function statusText(s) { return s === "valid" ? "登入有效" : s === "expired" ? "已過期" : "待檢查" }
    function statusTone(s) { return s === "valid" ? M3.c.successContainer : s === "expired" ? M3.c.errorContainer : M3.c.warningContainer }
    function statusOn(s) { return s === "valid" ? M3.c.success : s === "expired" ? M3.c.onErrorContainer : M3.c.warning }

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentHeight: col.height + 48
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: col
            x: 28; y: 6; width: scroll.width - 56; spacing: M3.gap

            // 摘要列
            Rectangle {
                width: parent.width; height: 78; radius: M3.rLg
                color: M3.c.surfaceContainer
                border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)

                Repeater {
                    model: [
                        { l: "全部帳號", v: Backend.accounts.length, i: "group", t: 0 },
                        { l: "Cookie 有效", v: root.validCount, i: "check_circle", t: 1 },
                        { l: "已過期", v: root.expiredCount, i: "error", t: 0 },
                        { l: "待檢查", v: root.unknownCount, i: "help", t: 2 },
                        { l: "已加密保存", v: countSaved(), i: "lock", t: 1 }
                    ]
                    delegate: Item {
                        x: index * (parent.width / 5)
                        width: parent.width / 5
                        height: parent.height
                            Rectangle {
                                x: 0; anchors.verticalCenter: parent.verticalCenter
                                width: index === 0 ? 0 : 1; height: 38
                                color: M3.alpha(M3.c.outlineVariant, 0.5)
                            }
                            Rectangle {
                                x: 20; y: 20; width: 38; height: 38; radius: 13
                                color: M3.tone(modelData.t)
                                Icon { anchors.centerIn: parent; name: modelData.i; size: 19; fill: 1; color: M3.onTone(modelData.t) }
                            }
                            Column {
                                x: 68; anchors.verticalCenter: parent.verticalCenter
                                spacing: 0
                                Text { text: modelData.v; color: M3.c.onSurface; font.pixelSize: M3.tTitle; font.weight: Font.DemiBold }
                                Text { text: modelData.l; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                            }
                        }
                    }
            }

            // 工具列
            Item {
                width: parent.width
                height: 44

                Rectangle {
                    id: searchBox
                    x: 0; y: 1; width: 288; height: 42; radius: 21
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
                            text: "搜尋名稱或電子郵件…"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tBody
                        }
                    }
                }

                Seg {
                    id: filterSeg
                    anchors.left: searchBox.right; anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    model: ["全部 " + Backend.accounts.length, "有效 " + root.validCount, "過期 " + root.expiredCount, "待檢查 " + root.unknownCount]
                    currentIndex: root.filter
                    onPicked: function (i) { root.filter = i }
                }

                Btn {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: "全部移除"; icon: "delete_sweep"; kind: "text"; small: true; danger: true
                    onClicked: clearDlg.open()
                }
            }

            // 新增帳號：三個欄位 + 登入方式
            Rectangle {
                width: parent.width; height: 96; radius: M3.rLg
                color: M3.c.surfaceContainer
                border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)

                Row {
                    x: 18; y: 6; spacing: 10
                    Field { id: newEmail; width: 236; label: "Cool English 帳號（Email）" }
                    Field { id: newPass; width: 172; label: "密碼（Windows 系統加密保存）"; password: true }
                    Field { id: newName; width: 158; label: "顯示名稱（選填）" }
                    Item {
                        width: modeSeg.implicitWidth; height: 64
                        Seg {
                            id: modeSeg; y: 24
                            model: ["有頭", "無頭"]
                            currentIndex: Backend.settings.defaultLoginMode === "headless" ? 1 : 0
                        }
                    }
                    Item {
                        width: 118; height: 64
                        Btn {
                            y: 24; width: parent.width
                            text: "連結帳號"; icon: "person_add"; small: true
                            onClicked: {
                                if (newEmail.text.trim() === "") {
                                    root.notify("請先填入 Cool English 帳號"); newEmail.forceActiveFocus(); return
                                }
                                Backend.addAccount(newEmail.text, newPass.text, newName.text,
                                                   modeSeg.currentIndex === 0 ? "headed" : "headless")
                                newEmail.text = ""; newPass.text = ""; newName.text = ""
                            }
                        }
                    }
                }

                Text {
                    x: 22; y: parent.height - 19
                    text: "以 Google OAuth 登入 Cool English（有頭＝可見瀏覽器可處理 MFA／通行密鑰／CAPTCHA，無頭遇到驗證會自動切換為可見）；登入成功並確認 MoodleSession 後才保存，帳號與 CLI 雙向同步。"
                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                }
            }

            // 主體
            Item {
                width: parent.width
                height: 520

                // 清單
                Rectangle {
                    x: 0; y: 0
                    width: parent.width - 356; height: 520
                    radius: M3.rXl
                    color: M3.c.surfaceContainer
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)
                    clip: true

                    Item {
                        id: head
                        x: 18; y: 0; width: parent.width - 36; height: 46
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: M3.alpha(M3.c.outlineVariant, 0.5) }
                        Text { x: 0; anchors.verticalCenter: parent.verticalCenter; text: "帳號"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { x: parent.width * 0.40; anchors.verticalCenter: parent.verticalCenter; text: "狀態"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { x: parent.width * 0.56; anchors.verticalCenter: parent.verticalCenter; text: "到期時間"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { x: parent.width * 0.70; anchors.verticalCenter: parent.verticalCenter; text: "最後登入"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                    }

                    WheelGuard { target: list }
                    ListView {
                        id: list
                        x: 10; y: 46; width: parent.width - 20; height: parent.height - 46
                        clip: true
                        spacing: 4
                        model: root.shown
                        boundsBehavior: Flickable.StopAtBounds
                        delegate: Rectangle {
                            width: list.width; height: 62; radius: 16
                            property var a: Backend.accounts[modelData]
                            color: Backend.selected === modelData ? M3.c.secondaryContainer : (rowHover.containsMouse ? M3.c.surfaceContainerHighest : "transparent")
                            Behavior on color { ColorAnimation { duration: 120 } }

                            // 放在底層：點列選取；右側圖示鈕在上層，仍可點擊
                            MouseArea {
                                id: rowHover
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: Backend.select(modelData)
                            }

                            AvatarView {
                                x: 10; width: 38; height: 38; radius: 19
                                anchors.verticalCenter: parent.verticalCenter
                                source: a ? a.avatar : ""
                                name: a ? a.name : "?"
                                tint: Backend.selected === modelData ? M3.alpha(M3.c.onSecondaryContainer, 0.14) : M3.c.surfaceContainerHighest
                                onTint: Backend.selected === modelData ? M3.c.onSecondaryContainer : M3.c.onSurfaceVariant
                            }
                            Column {
                                x: 58; anchors.verticalCenter: parent.verticalCenter
                                width: parent.width * 0.40 - 70
                                spacing: 1
                                Text {
                                    text: a ? a.name : ""
                                    color: Backend.selected === modelData ? M3.c.onSecondaryContainer : M3.c.onSurface
                                    font.pixelSize: M3.tBody; font.weight: Font.Medium
                                    elide: Text.ElideRight; width: parent.width
                                }
                                Text {
                                    text: a ? root.shownEmail(a.email) : ""
                                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                    elide: Text.ElideRight; width: parent.width
                                }
                            }
                            Chip {
                                x: parent.width * 0.40; anchors.verticalCenter: parent.verticalCenter
                                height: 22
                                text: a ? root.statusText(a.cookie) : ""
                                tone: a ? root.statusTone(a.cookie) : M3.c.surfaceContainerHighest
                                onTone: a ? root.statusOn(a.cookie) : M3.c.onSurfaceVariant
                            }
                            Text {
                                x: parent.width * 0.56; anchors.verticalCenter: parent.verticalCenter
                                text: a && a.expires !== "" ? a.expires : "—"
                                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                width: parent.width * 0.13; elide: Text.ElideRight
                            }
                            Text {
                                x: parent.width * 0.70; anchors.verticalCenter: parent.verticalCenter
                                text: a ? a.last : ""
                                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                width: parent.width - x - 104; elide: Text.ElideRight
                            }
                            Row {
                                anchors.right: parent.right; anchors.rightMargin: 6
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                IconBtn {
                                    icon: "sync"; tip: "重新讀取 Cookie"; size: 30; iconSize: 16
                                    onClicked: Backend.checkCookie(modelData)
                                }
                                IconBtn {
                                    icon: "edit"; tip: "重新命名"; size: 30; iconSize: 16
                                    onClicked: { renameTarget = modelData; renameDlg.open(); renameField.text = Backend.accounts[modelData].name }
                                }
                                IconBtn {
                                    icon: "delete"; tip: "移除帳號"; size: 30; iconSize: 16; danger: true
                                    onClicked: {
                                        if (Backend.settings.confirmDestructive === false) Backend.removeAccount(modelData)
                                        else { removeTarget = modelData; removeDlg.open() }
                                    }
                                }
                            }
                        }
                    }

                    EmptyState {
                        visible: root.shown.length === 0
                        anchors.fill: parent
                        anchors.topMargin: 46
                        icon: "search_off"; title: "沒有符合的帳號"
                        desc: "試試其他關鍵字，或清除篩選條件。"
                        actionText: "清除篩選"
                        onAction: { root.query = ""; searchIn.text = ""; root.filter = 0 }
                    }
                }

                // 詳情
                Rectangle {
                    x: parent.width - 340; y: 0
                    width: 340; height: 520
                    radius: M3.rXl
                    color: M3.c.surfaceContainer
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)
                    clip: true

                    Column {
                        visible: root.acc !== null
                        x: 22; y: 22; width: parent.width - 44; spacing: 8

                        Row {
                            spacing: 12
                            AvatarView {
                                width: 52; height: 52; radius: 18
                                source: root.acc ? root.acc.avatar : ""
                                name: root.acc ? root.acc.name : ""
                                tint: M3.c.primaryContainer
                                onTint: M3.c.onPrimaryContainer
                            }
                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                Text {
                                    text: root.acc ? root.acc.name : ""
                                    color: M3.c.onSurface; font.pixelSize: M3.tTitle; font.weight: Font.Medium
                                    width: 220; elide: Text.ElideRight
                                }
                                Text {
                                    text: root.acc ? root.shownEmail(root.acc.email) : ""
                                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
                                    width: 220; elide: Text.ElideRight
                                }
                            }
                        }

                        Chip {
                            text: root.acc ? root.statusText(root.acc.cookie) : ""
                            icon: root.acc && root.acc.cookie === "valid" ? "check_circle" : "error"
                            tone: root.acc ? root.statusTone(root.acc.cookie) : M3.c.surfaceContainerHighest
                            onTone: root.acc ? root.statusOn(root.acc.cookie) : M3.c.onSurfaceVariant
                        }

                        Rectangle { width: parent.width; height: 1; color: M3.alpha(M3.c.outlineVariant, 0.5) }
                    }

                    WheelGuard { target: metaScroll; visible: root.acc !== null }
                    Flickable {
                        id: metaScroll
                        visible: root.acc !== null
                        x: 22; y: actCol.y + actCol.height + 12; width: parent.width - 44
                        height: parent.height - y - 16
                        contentHeight: meta.height
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: meta
                            width: parent.width; spacing: 2
                            Repeater {
                                model: root.acc ? [
                                    { k: "到期時間", v: root.acc.expires || "—" },
                                    { k: "取得時間", v: root.acc.obtained },
                                    { k: "最後登入", v: root.acc.last },
                                    { k: "密碼保存", v: root.acc.saved ? "已加密" : "未保存" },
                                    { k: "登入方式", v: root.acc.mode === "headed" ? "有頭" : root.acc.mode === "headless" ? "無頭" : "—" },
                                    { k: "Cookie 檔", v: "cookies/" }
                                ] : []
                                delegate: Row {
                                    width: meta.width; height: 24
                                    Text { text: modelData.k; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; width: 88 }
                                    Text {
                                        text: modelData.v; color: M3.c.onSurface
                                        font.pixelSize: M3.tMicro; font.weight: Font.Medium
                                        width: meta.width - 88; elide: Text.ElideMiddle
                                    }
                                }
                            }
                        }
                    }

                    Column {
                        id: actCol
                        visible: root.acc !== null
                        y: 128
                        x: 22; width: parent.width - 44; spacing: 8

                        Row {
                            spacing: 4
                            Btn {
                                text: "取得 Google 頭像"; icon: "account_circle"; kind: "text"; small: true
                                enabled: !Backend.loginBusy
                                onClicked: {
                                    // 有保存密碼就直接重新登入；沒有就先請使用者輸入一次（登入成功後才會保存）
                                    if (root.acc !== null && root.acc.saved) Backend.refreshAvatar(Backend.selected)
                                    else { avPw.text = ""; avPwDlg.open() }
                                }
                            }
                        }
                        Row {
                            spacing: 4
                            Btn {
                                text: "選擇圖片"; icon: "image"; kind: "text"; small: true
                                onClicked: {
                                    if (root.acc === null) return
                                    root.avatarTarget = Backend.selected
                                    avatarDlg.open()
                                }
                            }
                            Btn {
                                visible: root.acc !== null && root.acc.avatar !== ""
                                text: "移除"; icon: "hide_image"; kind: "text"; small: true; danger: true
                                onClicked: Backend.clearAvatar(Backend.selected)
                            }
                        }
                        Text {
                            visible: root.acc !== null && root.acc.avatar === ""
                            width: parent.width
                            text: "登入成功後 cool.py 會順便從 Google 帳戶頁下載頭像並自動同步到這裡。已登入的帳號想補抓頭像，按「取得 Google 頭像」會用已保存的密碼重新登入一次；也可以用「選擇圖片」自行指定。沒有頭像時顯示名稱縮寫。"
                            color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                            wrapMode: Text.WordWrap; lineHeight: 1.25
                        }
                        Rectangle { width: parent.width; height: 1; color: M3.alpha(M3.c.outlineVariant, 0.5) }
                        Text { text: "登入與驗證（Edge / Chrome，直接由本程式驅動）"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Row {
                            spacing: 6
                            Btn { text: "檢查 Cookie"; icon: "sync"; kind: "tonal"; small: true; onClicked: Backend.checkCookie(Backend.selected) }
                            Btn {
                                text: "有頭登入"; icon: "open_in_new"; kind: "outlined"; small: true
                                enabled: !Backend.loginBusy
                                onClicked: Backend.loginAccount(Backend.selected, "headed")
                            }
                        }
                        Btn {
                            text: "無頭登入（背景執行）"; icon: "visibility_off"; kind: "outlined"; small: true
                            width: parent.width
                            enabled: !Backend.loginBusy
                            onClicked: Backend.loginAccount(Backend.selected, "headless")
                        }
                        Text {
                            visible: root.acc !== null && !root.acc.saved
                            width: parent.width
                            text: "此帳號尚未儲存密碼；請在上方輸入 Email 與密碼，按「連結帳號」即可更新並登入。"
                            color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                            wrapMode: Text.WordWrap; lineHeight: 1.3
                        }
                        Item {
                            visible: Backend.loginStatus !== ""
                            width: parent.width
                            height: loginText.implicitHeight + 2
                            Item {
                                visible: Backend.loginBusy
                                width: 16; height: 16
                                anchors.verticalCenter: parent.verticalCenter
                                Icon {
                                    anchors.centerIn: parent
                                    name: "progress_activity"; size: 14; color: M3.c.primary
                                    RotationAnimator on rotation {
                                        from: 0; to: 360; duration: 900
                                        loops: Animation.Infinite; running: Backend.loginBusy
                                    }
                                }
                            }
                            Icon {
                                visible: !Backend.loginBusy
                                x: 1
                                name: Backend.loginStatus.indexOf("成功") >= 0 ? "check_circle" : "error"
                                size: 14; color: M3.c.onSurfaceVariant
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Text {
                                id: loginText
                                x: 24
                                width: parent.width - 24
                                text: Backend.loginStatus
                                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                wrapMode: Text.WordWrap
                            }
                        }
                        Row {
                            spacing: 6
                            Btn {
                                text: "開啟資料夾"; icon: "folder_open"; kind: "text"; small: true
                                onClicked: Backend.openFolder()
                            }
                            Btn {
                                text: "移除"; icon: "delete"; kind: "text"; small: true; danger: true
                                onClicked: { removeTarget = Backend.selected; removeDlg.open() }
                            }
                        }
                    }

                    EmptyState {
                        visible: root.acc === null
                        anchors.fill: parent
                        icon: "person_off"; title: "尚未連結帳號"
                        desc: "在上方填入 Email、密碼與名稱，就會寫入 accounts.json。"
                        actionText: "回到新增欄位"
                        onAction: newEmail.forceActiveFocus()
                    }
                }
            }

            Text {
                text: "帳號、Cookie 與密碼皆以 Windows 系統加密保存；與內嵌終端的 CLI 帳號清單雙向同步（桌面刪除帳號也會移除 CLI 對應紀錄）。"
                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
            }
        }
    }

    // ── 對話框 ──
    FileDialog {
        id: avatarDlg
        title: "選擇大頭貼圖片"
        nameFilters: ["圖片 (*.png *.jpg *.jpeg *.webp *.gif)"]
        onAccepted: Backend.setAvatarFromFile(root.avatarTarget, selectedFile)
    }

    Dialog {
        id: avPwDlg
        title: "登入以取得 Google 頭像"
        subtitle: root.acc ? root.acc.email + " 還沒有保存密碼。頭像只能在登入 Google 當下取得；密碼只用於這次登入，成功後以 Windows 系統加密保存。" : ""
        icon: "account_circle"
        preferredWidth: 520
        Field { id: avPw; label: "Google 密碼"; password: true }
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: avPwDlg.close() }
            FillSpacer {}
            Btn {
                text: "登入並取得頭像"; icon: "login"
                onClicked: {
                    if (avPw.text === "" || root.acc === null) return
                    Backend.startLogin(root.acc.email, avPw.text, root.acc.name, "headless")
                    avPw.text = ""
                    avPwDlg.close()
                }
            }
        }
    }

    Dialog {
        id: clearDlg
        title: "移除全部帳號？"
        subtitle: "會清空使用者資料夾的 accounts.json 並刪除 cookies/ 內對應的 Cookie 檔，CLI 也會同步看到空的清單。"
        icon: "delete_forever"
        preferredWidth: 500
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: clearDlg.close() }
            FillSpacer {}
            Btn {
                text: "全部移除"; icon: "delete_sweep"; danger: true
                onClicked: { Backend.removeAllAccounts(); clearDlg.close() }
            }
        }
    }

    Dialog {
        id: renameDlg
        title: "重新命名帳號"
        subtitle: "只會改變本機顯示名稱，不影響 Cool English 帳號。"
        icon: "edit"
        preferredWidth: 460
        Field { id: renameField; label: "顯示名稱" }
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: renameDlg.close() }
            FillSpacer {}
            Btn {
                text: "儲存"; icon: "check"
                onClicked: { Backend.renameAccount(renameTarget, renameField.text); renameDlg.close() }
            }
        }
    }

    Dialog {
        id: removeDlg
        title: "移除帳號？"
        subtitle: "會從 accounts.json 移除，並刪除 cookies/ 內的 Cookie 檔；這個動作無法復原。"
        icon: "delete_forever"
        preferredWidth: 460
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: removeDlg.close() }
            FillSpacer {}
            Btn {
                text: "移除帳號"; icon: "delete"; kind: "filled"; danger: true
                onClicked: { Backend.removeAccount(removeTarget); removeDlg.close() }
            }
        }
    }

    property int renameTarget: 0
    property int removeTarget: 0
    property int avatarTarget: 0

    function countSaved() {
        var n = 0
        for (var i = 0; i < Backend.accounts.length; i++) if (Backend.accounts[i].saved) n++
        return n
    }
}



