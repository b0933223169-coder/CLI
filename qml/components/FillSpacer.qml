import QtQuick

// 把同一個 Row 裡「其他可見元素」佔掉的寬度扣掉，剩下的全部給自己：
// 右側的按鈕因此永遠貼齊最右邊，不用再猜左邊內容有多寬（寫死 parent.width - 520 這類數字會在文字變長時跑位）。
Item {
    height: 1
    width: {
        var p = parent
        if (!p) return 0
        var used = 0, n = 0
        for (var i = 0; i < p.children.length; i++) {
            var c = p.children[i]
            if (c === this || !c.visible) continue
            used += c.width
            n++
        }
        return Math.max(0, p.width - used - (p.spacing || 0) * n)
    }
}
