#define _USE_MATH_DEFINES
#include "color_engine.h"
#include <QImage>
#include <QFile>
#include <QColor>
#include <QVariantMap>
#include <QVariantList>
#include <algorithm>
#include <cmath>

ColorEngine::Style ColorEngine::styleFromVariant(const QString &v) {
    QString s = v.toLower();
    if (s == "vibrant" || s == "expressive" || s == "rainbow") return Vibrant;
    if (s == "neutral" || s == "monochrome" || s == "fidelity") return Muted;
    if (s == "fruitsalad" || s == "content") return Ocean;
    return Harmony;
}

QColor ColorEngine::shade(const QColor &c, float vFactor, float sFactor) {
    qreal h = c.hsvHueF(), s = c.hsvSaturationF(), v = c.valueF();
    if (h < 0) h = 0;
    s = std::clamp(s * sFactor, 0.0, 1.0);
    v = std::clamp(v * vFactor, 0.0, 1.0);
    return QColor::fromHsvF(h, s, v);
}

// ---------------------------------------------------------------- OKLab / OKLCH
namespace {
double toLin(double c) { return c <= 0.04045 ? c / 12.92 : std::pow((c + 0.055) / 1.055, 2.4); }
double fromLin(double c) { return c <= 0.0031308 ? 12.92 * c : 1.055 * std::pow(c, 1 / 2.4) - 0.055; }
double relLum(const QColor &c) { return 0.2126 * toLin(c.redF()) + 0.7152 * toLin(c.greenF()) + 0.0722 * toLin(c.blueF()); }
void rgbToOklab(const QColor &c, double &L, double &a, double &b) {
    double r = toLin(c.redF()), g = toLin(c.greenF()), bl = toLin(c.blueF());
    double l = std::cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * bl);
    double m = std::cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * bl);
    double s = std::cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * bl);
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s;
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s;
    b = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s;
}
bool oklabToRgb(double L, double a, double b, QColor &out) {
    double l = L + 0.3963377774 * a + 0.2158037573 * b;
    double m = L - 0.1055613458 * a - 0.0638541728 * b;
    double s = L - 0.0894841775 * a - 1.2914855480 * b;
    l = l * l * l; m = m * m * m; s = s * s * s;
    double r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s;
    double g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s;
    double bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s;
    bool inGamut = r >= -0.0005 && r <= 1.0005 && g >= -0.0005 && g <= 1.0005 && bl >= -0.0005 && bl <= 1.0005;
    out = QColor::fromRgbF(std::clamp(fromLin(std::clamp(r, 0.0, 1.0)), 0.0, 1.0),
                           std::clamp(fromLin(std::clamp(g, 0.0, 1.0)), 0.0, 1.0),
                           std::clamp(fromLin(std::clamp(bl, 0.0, 1.0)), 0.0, 1.0));
    return inGamut;
}
}

void ColorEngine::toOklch(const QColor &c, double &L, double &C, double &hDeg) {
    double a, b; rgbToOklab(c, L, a, b);
    C = std::sqrt(a * a + b * b);
    hDeg = std::fmod(std::atan2(b, a) * 180.0 / M_PI + 360.0, 360.0);
}

QColor ColorEngine::oklch(double L, double C, double hDeg) {
    double hr = hDeg * M_PI / 180.0;
    QColor out;
    double lo = 0, hi = std::max(0.0, C);
    if (oklabToRgb(L, hi * std::cos(hr), hi * std::sin(hr), out)) return out;
    for (int i = 0; i < 18; ++i) {                 // 二分搜尋：保持明度與色相，降到色域內的最大彩度
        double mid = (lo + hi) / 2;
        if (oklabToRgb(L, mid * std::cos(hr), mid * std::sin(hr), out)) lo = mid; else hi = mid;
    }
    oklabToRgb(L, lo * std::cos(hr), lo * std::sin(hr), out);
    return out;
}

double ColorEngine::contrast(const QColor &a, const QColor &b) {
    double la = relLum(a), lb = relLum(b);
    if (la < lb) std::swap(la, lb);
    return (la + 0.05) / (lb + 0.05);
}

QColor ColorEngine::ensureContrast(const QColor &fg, const QColor &bg, double ratio) {
    if (contrast(fg, bg) >= ratio) return fg;
    double L, C, h; toOklch(fg, L, C, h);
    const bool lighten = relLum(bg) < 0.4;         // 深底往亮調，淺底往暗調
    for (int i = 0; i < 100; ++i) {
        L += lighten ? 0.01 : -0.01;
        L = std::clamp(L, 0.0, 1.0);
        QColor c = oklch(L, C, h);
        if (contrast(c, bg) >= ratio) return c;
        if (L <= 0.0 || L >= 1.0) break;
    }
    return lighten ? QColor("#ffffff") : QColor("#0b0d10");
}

QColor ColorEngine::onFor(const QColor &bg, const QColor &tintSource) {
    double L, C, h = 0;
    if (tintSource.isValid()) toOklch(tintSource, L, C, h); else toOklch(bg, L, C, h);
    QColor light = oklch(0.985, 0.012, h), dark = oklch(0.17, 0.02, h);
    return contrast(light, bg) >= contrast(dark, bg) ? light : dark;
}

QString ColorEngine::onColor(const QColor &bg) { return onFor(bg).name(); }

ColorEngine::Palette ColorEngine::build(const QString &seedHex, Style style, bool dark) {
    QColor seed(seedHex);
    if (!seed.isValid()) seed = QColor("#6750a4");
    double sL, sC, sh; toOklch(seed, sL, sC, sh);

    // 風格：彩度倍率 + 三個色相的相對角度
    double mult = 1.0, h2 = 28, h3 = 72;
    switch (style) {
    case Muted:   mult = 0.35; h2 = 0;   h3 = 0;   break;
    case Vibrant: mult = 1.25; h2 = 40;  h3 = 125; break;
    case Ocean:   mult = 0.9;  h2 = 150; h3 = 210; break;
    default: break;
    }
    const double cP = std::clamp(sC * mult, 0.05, 0.21);
    const double hP = sh, hS = std::fmod(sh + h2, 360.0), hT = std::fmod(sh + h3, 360.0);
    const double cS = cP * 0.45, cT = cP * 0.7;

    // 色調（OKLCH 明度）：主色 / on / 容器 / on 容器；固定的明度階梯保證各色相的對比度一致
    const double mainL = dark ? 0.80 : 0.49, onL = dark ? 0.27 : 0.99, contL = dark ? 0.37 : 0.91, onContL = dark ? 0.91 : 0.27;
    auto tone = [&](double hue, double chroma, double L) { return oklch(L, chroma, hue); };
    Palette p;
    p.primary = tone(hP, cP, mainL);   p.onPrimary = tone(hP, cP * 0.25, onL);
    p.primaryContainer = tone(hP, cP * (dark ? 0.75 : 0.45), contL); p.onPrimaryContainer = tone(hP, cP * 0.3, onContL);
    p.secondary = tone(hS, cS, mainL); p.onSecondary = tone(hS, cS * 0.25, onL);
    p.secondaryContainer = tone(hS, cS * (dark ? 0.9 : 0.6), contL); p.onSecondaryContainer = tone(hS, cS * 0.35, onContL);
    p.tertiary = tone(hT, cT, mainL);  p.onTertiary = tone(hT, cT * 0.25, onL);
    p.tertiaryContainer = tone(hT, cT * (dark ? 0.8 : 0.5), contL); p.onTertiaryContainer = tone(hT, cT * 0.3, onContL);

    // 中性色：帶一點主色相的低彩度灰（避免死灰，也避免過度染色）
    if (dark) {
        p.surface = tone(hP, 0.016, 0.185);         p.surfaceVariant = tone(hP, 0.022, 0.26);
        p.onSurface = tone(hP, 0.010, 0.93);        p.onSurfaceVariant = tone(hP, 0.016, 0.79);
        p.outline = tone(hP, 0.020, 0.62);          p.outlineVariant = tone(hP, 0.016, 0.38);
        p.inverseSurface = tone(hP, 0.010, 0.91);   p.inverseOnSurface = tone(hP, 0.012, 0.23);
        p.inversePrimary = tone(hP, cP, 0.49);
    } else {
        p.surface = tone(hP, 0.006, 0.985);         p.surfaceVariant = tone(hP, 0.012, 0.935);
        p.onSurface = tone(hP, 0.016, 0.22);        p.onSurfaceVariant = tone(hP, 0.016, 0.42);
        p.outline = tone(hP, 0.016, 0.62);          p.outlineVariant = tone(hP, 0.010, 0.86);
        p.inverseSurface = tone(hP, 0.012, 0.27);   p.inverseOnSurface = tone(hP, 0.008, 0.96);
        p.inversePrimary = tone(hP, cP, 0.80);
    }

    // 語意色（錯誤／成功／警告）：固定色相但「向主色相和諧偏移」最多 ±14°，避免在各主題上突兀
    auto harmonize = [&](double base) {
        double d = std::fmod(sh - base + 540.0, 360.0) - 180.0;
        return std::fmod(base + std::clamp(d * 0.2, -14.0, 14.0) + 360.0, 360.0);
    };
    const double hE = harmonize(27), hG = harmonize(150), hW = harmonize(80);
    const double sMain = dark ? 0.80 : 0.50, sCont = dark ? 0.36 : 0.92, sOnCont = dark ? 0.92 : 0.30, sOn = dark ? 0.27 : 0.99;
    p.error = tone(hE, dark ? 0.13 : 0.17, sMain);  p.onError = tone(hE, 0.03, sOn);
    p.errorContainer = tone(hE, dark ? 0.10 : 0.05, sCont); p.onErrorContainer = tone(hE, dark ? 0.04 : 0.09, sOnCont);
    p.success = tone(hG, dark ? 0.12 : 0.12, dark ? 0.82 : 0.50); p.onSuccess = tone(hG, 0.03, sOn);
    p.successContainer = tone(hG, dark ? 0.08 : 0.05, sCont); p.onSuccessContainer = tone(hG, dark ? 0.04 : 0.08, sOnCont);
    p.warning = tone(hW, dark ? 0.12 : 0.13, dark ? 0.84 : 0.52); p.onWarning = tone(hW, 0.04, sOn);
    p.warningContainer = tone(hW, dark ? 0.07 : 0.06, dark ? 0.37 : 0.93);

    // 保險：所有「on」色與其底色至少 4.5:1（文字）
    auto fix = [](QColor &on, const QColor &bg) { on = ensureContrast(on, bg, 4.5); };
    fix(p.onPrimary, p.primary); fix(p.onSecondary, p.secondary); fix(p.onTertiary, p.tertiary);
    fix(p.onPrimaryContainer, p.primaryContainer); fix(p.onSecondaryContainer, p.secondaryContainer);
    fix(p.onTertiaryContainer, p.tertiaryContainer); fix(p.onError, p.error); fix(p.onErrorContainer, p.errorContainer);
    fix(p.onSuccess, p.success); fix(p.onSuccessContainer, p.successContainer); fix(p.onWarning, p.warning);
    fix(p.onSurface, p.surface); fix(p.onSurfaceVariant, p.surface);
    return p;
}

QVariantMap ColorEngine::generate(const QString &seedHex, const QString &variant, bool dark) {
    Palette p = build(seedHex, styleFromVariant(variant), dark);
    QVariantMap m;
    m["primary"]=p.primary.name(); m["onPrimary"]=p.onPrimary.name();
    m["primaryContainer"]=p.primaryContainer.name(); m["onPrimaryContainer"]=p.onPrimaryContainer.name();
    m["secondary"]=p.secondary.name(); m["onSecondary"]=p.onSecondary.name();
    m["secondaryContainer"]=p.secondaryContainer.name(); m["onSecondaryContainer"]=p.onSecondaryContainer.name();
    m["tertiary"]=p.tertiary.name(); m["onTertiary"]=p.onTertiary.name();
    m["tertiaryContainer"]=p.tertiaryContainer.name(); m["onTertiaryContainer"]=p.onTertiaryContainer.name();
    m["surface"]=p.surface.name(); m["onSurface"]=p.onSurface.name();
    m["surfaceVariant"]=p.surfaceVariant.name(); m["onSurfaceVariant"]=p.onSurfaceVariant.name();
    m["outline"]=p.outline.name(); m["outlineVariant"]=p.outlineVariant.name();
    m["error"]=p.error.name(); m["onError"]=p.onError.name();
    m["errorContainer"]=p.errorContainer.name(); m["onErrorContainer"]=p.onErrorContainer.name();
    m["success"]=p.success.name(); m["onSuccess"]=p.onSuccess.name();
    m["successContainer"]=p.successContainer.name(); m["onSuccessContainer"]=p.onSuccessContainer.name();
    m["warning"]=p.warning.name(); m["onWarning"]=p.onWarning.name(); m["warningContainer"]=p.warningContainer.name();
    m["inverseSurface"]=p.inverseSurface.name(); m["inverseOnSurface"]=p.inverseOnSurface.name();
    m["inversePrimary"]=p.inversePrimary.name();
    // 表面容器階梯（OKLCH 明度等距，跨色相一致）
    {
        double L, C, hh; toOklch(p.surface, L, C, hh);
        auto step = [&](double dL) { return oklch(std::clamp(L + dL, 0.0, 1.0), C * (dark ? 1.15 : 1.5), hh).name(); };
        const double s = dark ? 1.0 : -1.0;       // 深色：往亮；淺色：往暗
        m["surfaceContainerLowest"] = step(-s * 0.035);
        m["surfaceContainerLow"]    = step(s * 0.018);
        m["surfaceContainer"]       = step(s * 0.036);
        m["surfaceContainerHigh"]   = step(s * 0.060);
        m["surfaceContainerHighest"]= step(s * 0.085);
        m["surfaceBright"] = step(s * 0.11);
        m["surfaceDim"]    = step(dark ? -0.03 : -0.07);
    }
    m["background"]=p.surface.name(); m["onBackground"]=p.onSurface.name();
    m["surfaceTint"]=p.primary.name();
    m["shadow"]="#000000"; m["scrim"]="#000000";
    // QML 可能讀 QColor 型別，這裡給字串（QML 會自動轉 QColor）
    return m;
}

QVariantList ColorEngine::preview(const QString &seedHex, const QString &variant, bool dark) {
    QVariantMap m = generate(seedHex, variant, dark);
    return QVariantList{ m["primary"], m["secondary"], m["tertiary"],
                         m["primaryContainer"], m["surfaceContainerHigh"] };
}

QString ColorEngine::seedFromImage(const QString &path) {
    QImage img(path);
    if (img.isNull()) return QString();
    img = img.convertToFormat(QImage::Format_RGB32);
    if (img.width() > 128 || img.height() > 128) img = img.scaled(128,128,Qt::KeepAspectRatio,Qt::SmoothTransformation);
    // HSV 直方圖量化：色相 24 格、飽和 4 格、明度 4 格，選分數最高的鮮明色
    int hist[24][4][4] = {};
    for (int y=0; y<img.height(); ++y) {
        const QRgb *row = (const QRgb*)img.constScanLine(y);
        for (int x=0; x<img.width(); ++x) {
            QColor c(row[x]);
            qreal s=c.hsvSaturationF(), v=c.valueF();
            if (v<0.12 || v>0.98 || s<0.12) continue; // 略過太暗/太亮/太灰
            int hi=(int)(c.hsvHueF()*24)%24;
            int si=qMin(3,(int)(s*4));
            int vi=qMin(3,(int)(v*4));
            hist[hi][si][vi] += 1 + (int)(s*10); // 鮮明色加權
        }
    }
    int bestH=-1,bestS=1,bestV=2,best=0;
    for(int hi=0;hi<24;++hi)for(int si=0;si<4;++si)for(int vi=0;vi<4;++vi)
        if(hist[hi][si][vi]>best){best=hist[hi][si][vi];bestH=hi;bestS=si;bestV=vi;}
    if(bestH<0) return QString();
    qreal h=(bestH+0.5)/24.0, s=(bestS+0.5)/4.0, v=0.55+0.13*bestV;
    return QColor::fromHsvF(h, qMin(s,1.0), qMin(v,1.0)).name();
}

void ColorEngine::applyContrast(QVariantMap &m, double level, bool dark) {
    const double k = std::clamp(level, 0.0, 1.0);
    if (k <= 0.001) return;
    const QColor ext = dark ? QColor("#ffffff") : QColor("#000000");
    auto mix = [](const QColor &a, const QColor &b, double t) {
        return QColor::fromRgbF(a.redF() * (1 - t) + b.redF() * t, a.greenF() * (1 - t) + b.greenF() * t, a.blueF() * (1 - t) + b.blueF() * t);
    };
    auto get = [&](const char *key) { return QColor(m.value(QString::fromLatin1(key)).toString()); };
    auto set = [&](const char *key, const QColor &c) { m[QString::fromLatin1(key)] = c.name(); };
    // 文字與邊框：往最亮／最暗拉
    for (const char *key : { "onSurface", "onBackground", "inverseSurface" }) set(key, mix(get(key), ext, 0.85 * k));
    set("onSurfaceVariant", mix(get("onSurfaceVariant"), ext, 0.7 * k));
    set("outline", mix(get("outline"), ext, 0.65 * k));
    set("outlineVariant", mix(get("outlineVariant"), ext, 0.5 * k));
    // 主色相關：與底色的對比提高到 3 → 7
    const QColor surface = get("surface");
    for (const char *key : { "primary", "secondary", "tertiary", "error", "success", "warning" })
        set(key, ensureContrast(get(key), surface, 3.0 + 4.0 * k));
    // 放在色塊上的文字：4.5 → 9
    const char *pairs[][2] = { { "onPrimary", "primary" }, { "onSecondary", "secondary" }, { "onTertiary", "tertiary" },
                               { "onError", "error" }, { "onSuccess", "success" }, { "onWarning", "warning" },
                               { "onPrimaryContainer", "primaryContainer" }, { "onSecondaryContainer", "secondaryContainer" },
                               { "onTertiaryContainer", "tertiaryContainer" }, { "onErrorContainer", "errorContainer" },
                               { "onSuccessContainer", "successContainer" } };
    for (auto &p : pairs) set(p[0], ensureContrast(get(p[0]), get(p[1]), 4.5 + 4.5 * k));
    // 容器與背景拉開一點層次
    for (const char *key : { "surfaceContainerLow", "surfaceContainer", "surfaceContainerHigh", "surfaceContainerHighest" })
        set(key, mix(get(key), ext, 0.06 * k));
}
