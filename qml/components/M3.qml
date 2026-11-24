pragma Singleton
import QtQuick
import Cool 1.0

// 設計權杖：間距沿用原型的 4 的倍數，色彩交給 Python 的 Material 演算法
QtObject {
    readonly property var c: Backend.colors

    // 圓角（設定頁可切換風格）
    readonly property real radiusScale: Backend.settings.radiusStyle === "sharp" ? 0.45
                                     : Backend.settings.radiusStyle === "soft" ? 1.3 : 1
    readonly property int rXs: Math.round(8 * radiusScale)
    readonly property int rSm: Math.round(12 * radiusScale)
    readonly property int rMd: Math.round(16 * radiusScale)
    readonly property int rLg: Math.round(20 * radiusScale)
    readonly property int rXl: Math.round(28 * radiusScale)
    readonly property int rXxl: Math.round(36 * radiusScale)

    // 縮放：設定頁的「介面字級」直接影響下列字級權杖
    // 密度：緊湊／標準／寬鬆會調整頁面區塊之間的垂直間距
    readonly property real densityFactor: Backend.settings.density === "compact" ? 0.65
                                       : Backend.settings.density === "wide" ? 1.45 : 1
    readonly property int gap: Math.max(6, Math.round(14 * densityFactor))
    readonly property int gapLg: Math.max(8, Math.round(16 * densityFactor))

    // 動態：標準 / 強調 / 彈簧（Caelestia 的 expressive spatial）
    readonly property var standard: [0.2, 0, 0, 1, 1, 1]
    readonly property var emphasized: [0.05, 0.7, 0.1, 1, 1, 1]
    readonly property var spring: [0.38, 1.21, 0.22, 1, 1, 1]
    readonly property bool calm: Backend.settings.reduceMotion === true
    readonly property int dShort: calm ? 0 : 150
    readonly property int dMed: calm ? 0 : 300
    readonly property int dLong: calm ? 0 : 500

    // 字級：跟著設定頁的介面字級調整
    // 介面縮放（80–120%）套用在文字大小上，與「介面字級」相乘
    readonly property real uiScale: Math.max(0.8, Math.min(1.2, (Backend.settings.uiScale ? Backend.settings.uiScale : 100) / 100))
    readonly property int fontBase: Math.round((Backend.settings.fontSize ? Backend.settings.fontSize : 14) * uiScale)
    readonly property int tMicro: Math.max(9, fontBase - 3)
    readonly property int tLabel: Math.max(10, fontBase - 2)
    readonly property int tBody: fontBase
    readonly property int tBodyLg: fontBase + 2
    readonly property int tTitle: fontBase + 6
    readonly property int tHeadline: fontBase + 14
    readonly property int tDisplay: fontBase + 26

    readonly property string mono: Backend.settings.terminalFont ? Backend.settings.terminalFont : "Cascadia Mono"

    function tone(i) { var k = i % 3; return k === 0 ? c.primaryContainer : (k === 1 ? c.secondaryContainer : c.tertiaryContainer) }
    function onTone(i) { var k = i % 3; return k === 0 ? c.onPrimaryContainer : (k === 1 ? c.onSecondaryContainer : c.onTertiaryContainer) }
    function solid(i) { var k = i % 3; return k === 0 ? c.primary : (k === 1 ? c.secondary : c.tertiary) }
    function alpha(color, a) { var k = Qt.color(color); return Qt.rgba(k.r, k.g, k.b, a) }
    function hours(min) { return (min / 60).toFixed(1) + "h" }
    function clock(min) { var h = Math.floor(min / 60); var m = Math.round(min % 60); return h + "h " + (m < 10 ? "0" : "") + m + "m" }
}
