"""把 15 MB 的 Material Symbols Rounded 縮成只含專案實際用到的圖示（省約 100+ MB 記憶體）。
用法：python tools_subset_font.py   （需要 fonttools；只在開發機執行，不是執行期相依）"""
import re, glob, os, sys
from fontTools.ttLib import TTFont
from fontTools import subset

root = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(root, 'assets', 'fonts', 'MaterialSymbolsRounded.full.ttf')
dst = os.path.join(root, 'assets', 'fonts', 'MaterialSymbolsRounded.ttf')
if not os.path.exists(src):
    os.replace(dst, src)          # 保留完整原檔

font = TTFont(src, lazy=True)
glyphs = set(font.getGlyphOrder())
tokens = set()
for path in glob.glob(os.path.join(root, 'qml', '**', '*.qml'), recursive=True) + glob.glob(os.path.join(root, '*.cpp')) + glob.glob(os.path.join(root, '*.inc')):
    text = open(path, encoding='utf-8', errors='ignore').read()
    tokens.update(re.findall(r'"([a-z][a-z0-9_]*)"', text))
icons = sorted(t for t in tokens if t in glyphs)
keep = set(icons)
for i in icons:
    if i + '.fill' in glyphs: keep.add(i + '.fill')
# 作為 ligature 元件的字元字形
chars = 'abcdefghijklmnopqrstuvwxyz0123456789_'
cmap = font.getBestCmap()
for ch in chars:
    g = cmap.get(ord(ch))
    if g: keep.add(g)
print('icons kept:', len(icons))
opts = subset.Options()
opts.layout_features = ['*']
opts.glyph_names = True
opts.notdef_outline = True
opts.hinting = False
opts.layout_closure = False
opts.drop_tables += ['STAT']
sub = subset.Subsetter(opts)
sub.populate(glyphs=sorted(keep), unicodes=[ord(c) for c in chars])
f2 = TTFont(src)
sub.subset(f2)
f2.save(dst)
print('size:', os.path.getsize(dst) // 1024, 'KB')
