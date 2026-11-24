#pragma once
#include <QColor>
#include <QVariantMap>
#include <QString>

// 全新色彩風格引擎：純 C++，從一顆 seed 色用 HSV 推導出完整協調配色。
// 不依賴 Material You 的 HCT/Celebi 演算法（那是 scheme.py 做的），
// 而是用 Qt 內建 HSV 做出「色相協調 + 明度階梯」的新風格。
class ColorEngine {
public:
    enum Style { Harmony, Vibrant, Muted, Ocean };

    // 由 variant 字串對應到風格
    static Style styleFromVariant(const QString &variant);

    // 產生完整配色表（QML 的 M3.c.xxx 全部覆蓋）
    static QVariantMap generate(const QString &seedHex, const QString &variant, bool dark);

    // 從圖片取主色：用 Qt 量化（把像素集中在 HSV 直方圖，取最多數的鮮明色）
    static QString seedFromImage(const QString &path);

    // 感知均勻（OKLCH）色彩工具：對比度計算與自動修正
    static double contrast(const QColor &a, const QColor &b);                  // WCAG 對比度
    static QColor ensureContrast(const QColor &fg, const QColor &bg, double ratio);   // 調整 fg 明度直到達標
    static QColor onFor(const QColor &bg, const QColor &tintSource = QColor());       // bg 上最清楚的文字色
    static QColor oklch(double L, double C, double hDeg);                       // 超出色域時自動降彩度
    static void toOklch(const QColor &c, double &L, double &C, double &hDeg);

    // 依對比等級（0~1）調整整套配色：文字、邊框、主色往極端拉開；0 = 原樣，因此拉回 0 就完全還原
    static void applyContrast(QVariantMap &m, double level, bool dark);

    // 預覽用的 5 個代表色
    static QVariantList preview(const QString &seedHex, const QString &variant, bool dark);

private:
    struct Palette {
        QColor primary, onPrimary, primaryContainer, onPrimaryContainer;
        QColor secondary, onSecondary, secondaryContainer, onSecondaryContainer;
        QColor tertiary, onTertiary, tertiaryContainer, onTertiaryContainer;
        QColor surface, onSurface, surfaceVariant, onSurfaceVariant;
        QColor outline, outlineVariant;
        QColor error, onError, errorContainer, onErrorContainer;
        QColor success, onSuccess, successContainer, onSuccessContainer;
        QColor warning, onWarning, warningContainer;
        QColor inverseSurface, inverseOnSurface, inversePrimary;
    };
    static Palette build(const QString &seedHex, Style style, bool dark);
    static QColor shade(const QColor &c, float vFactor, float sFactor = 1.0f);
    static QString onColor(const QColor &bg);
};
