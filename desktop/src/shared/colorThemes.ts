import type { AppSettings } from './types'

export interface ColorThemePreset {
  id: string
  name: string
  group: '暖色' | '冷色' | '自然' | '鮮明'
  theme: AppSettings['theme']
  interfaceBackgroundColor: string
  interfaceSurfaceColor: string
  accentColor: string
  textColor: string
  terminalCursorColor: string
  terminalTextColor: string
  terminalBackgroundColor: string
}

export const colorThemePresets: readonly ColorThemePreset[] = [
  {
    id: 'ember',
    name: '熔岩赤焰',
    group: '暖色',
    theme: 'dark',
    interfaceBackgroundColor: '#24100f',
    interfaceSurfaceColor: '#51231b',
    accentColor: '#ff583d',
    textColor: '#fff0e8',
    terminalCursorColor: '#ff795b',
    terminalTextColor: '#ffe5dc',
    terminalBackgroundColor: '#2b100e'
  },
  {
    id: 'terracotta',
    name: '陶土夕陽',
    group: '暖色',
    theme: 'light',
    interfaceBackgroundColor: '#f2d0c2',
    interfaceSurfaceColor: '#fbe8df',
    accentColor: '#b74421',
    textColor: '#37170d',
    terminalCursorColor: '#ff906b',
    terminalTextColor: '#fff0e8',
    terminalBackgroundColor: '#32150f'
  },
  {
    id: 'honey',
    name: '金箔蜂蜜',
    group: '暖色',
    theme: 'dark',
    interfaceBackgroundColor: '#241d0b',
    interfaceSurfaceColor: '#51400f',
    accentColor: '#ffc928',
    textColor: '#fff7d6',
    terminalCursorColor: '#ffdc58',
    terminalTextColor: '#fff3c4',
    terminalBackgroundColor: '#241b08'
  },
  {
    id: 'rosewood',
    name: '莓紅酒窖',
    group: '暖色',
    theme: 'light',
    interfaceBackgroundColor: '#f0cad8',
    interfaceSurfaceColor: '#f9e2eb',
    accentColor: '#b51f55',
    textColor: '#35101e',
    terminalCursorColor: '#ff6b9a',
    terminalTextColor: '#ffe7ee',
    terminalBackgroundColor: '#2b101c'
  },
  {
    id: 'saffron',
    name: '藏紅花金',
    group: '暖色',
    theme: 'dark',
    interfaceBackgroundColor: '#261a08',
    interfaceSurfaceColor: '#503008',
    accentColor: '#ff9e00',
    textColor: '#fff0d1',
    terminalCursorColor: '#ffc04d',
    terminalTextColor: '#fff0cf',
    terminalBackgroundColor: '#241605'
  },
  {
    id: 'peach',
    name: '珊瑚蜜桃',
    group: '暖色',
    theme: 'light',
    interfaceBackgroundColor: '#ffd8cf',
    interfaceSurfaceColor: '#ffebe6',
    accentColor: '#e84b78',
    textColor: '#3b1020',
    terminalCursorColor: '#ff89a9',
    terminalTextColor: '#fff0f4',
    terminalBackgroundColor: '#2c101a'
  },
  {
    id: 'ocean',
    name: '深洋藍',
    group: '冷色',
    theme: 'dark',
    interfaceBackgroundColor: '#071b2a',
    interfaceSurfaceColor: '#123f5b',
    accentColor: '#20b8f0',
    textColor: '#e5f8ff',
    terminalCursorColor: '#64d5ff',
    terminalTextColor: '#dff7ff',
    terminalBackgroundColor: '#071b2a'
  },
  {
    id: 'arctic',
    name: '冰川青',
    group: '冷色',
    theme: 'light',
    interfaceBackgroundColor: '#c5e8ed',
    interfaceSurfaceColor: '#e2f4f5',
    accentColor: '#007f91',
    textColor: '#082b31',
    terminalCursorColor: '#27d3df',
    terminalTextColor: '#ddffff',
    terminalBackgroundColor: '#082328'
  },
  {
    id: 'lavender',
    name: '紫水晶',
    group: '冷色',
    theme: 'dark',
    interfaceBackgroundColor: '#1a1030',
    interfaceSurfaceColor: '#39265d',
    accentColor: '#b88cff',
    textColor: '#f4eaff',
    terminalCursorColor: '#d0afff',
    terminalTextColor: '#f2e8ff',
    terminalBackgroundColor: '#1a1030'
  },
  {
    id: 'indigo',
    name: '靛藍電波',
    group: '冷色',
    theme: 'light',
    interfaceBackgroundColor: '#cdd5ff',
    interfaceSurfaceColor: '#e7eaff',
    accentColor: '#354fce',
    textColor: '#111c4a',
    terminalCursorColor: '#8297ff',
    terminalTextColor: '#e9edff',
    terminalBackgroundColor: '#111936'
  },
  {
    id: 'silverblue',
    name: '鋼鐵銀藍',
    group: '冷色',
    theme: 'dark',
    interfaceBackgroundColor: '#101a27',
    interfaceSurfaceColor: '#2b4665',
    accentColor: '#a9c8e8',
    textColor: '#e9f2fb',
    terminalCursorColor: '#c4e0ff',
    terminalTextColor: '#e5f0ff',
    terminalBackgroundColor: '#101a27'
  },
  {
    id: 'glacier',
    name: '薄荷極光',
    group: '冷色',
    theme: 'light',
    interfaceBackgroundColor: '#c5eee2',
    interfaceSurfaceColor: '#e1f7ef',
    accentColor: '#00a982',
    textColor: '#07352b',
    terminalCursorColor: '#50f0bd',
    terminalTextColor: '#ddfff1',
    terminalBackgroundColor: '#09271f'
  },
  {
    id: 'forest',
    name: '松林深處',
    group: '自然',
    theme: 'dark',
    interfaceBackgroundColor: '#0b2113',
    interfaceSurfaceColor: '#1c4b2d',
    accentColor: '#47c76f',
    textColor: '#e6ffe9',
    terminalCursorColor: '#7bea91',
    terminalTextColor: '#e4ffe8',
    terminalBackgroundColor: '#0d2113'
  },
  {
    id: 'sage',
    name: '鼠尾草灰綠',
    group: '自然',
    theme: 'light',
    interfaceBackgroundColor: '#dfe8c8',
    interfaceSurfaceColor: '#eff4df',
    accentColor: '#627d35',
    textColor: '#202d12',
    terminalCursorColor: '#badb71',
    terminalTextColor: '#f0f7dc',
    terminalBackgroundColor: '#202719'
  },
  {
    id: 'moss',
    name: '青苔螢光',
    group: '自然',
    theme: 'dark',
    interfaceBackgroundColor: '#1c2409',
    interfaceSurfaceColor: '#40520e',
    accentColor: '#b5d92b',
    textColor: '#f5ffd9',
    terminalCursorColor: '#d5f56b',
    terminalTextColor: '#f1ffd1',
    terminalBackgroundColor: '#1a2108'
  },
  {
    id: 'bamboo',
    name: '竹影墨青',
    group: '自然',
    theme: 'light',
    interfaceBackgroundColor: '#c5e9dc',
    interfaceSurfaceColor: '#e2f5ec',
    accentColor: '#007d63',
    textColor: '#082c25',
    terminalCursorColor: '#47d6aa',
    terminalTextColor: '#dffff3',
    terminalBackgroundColor: '#09251e'
  },
  {
    id: 'wildflower',
    name: '野花紫羅蘭',
    group: '自然',
    theme: 'dark',
    interfaceBackgroundColor: '#28102d',
    interfaceSurfaceColor: '#56245d',
    accentColor: '#df70e8',
    textColor: '#ffebff',
    terminalCursorColor: '#f2a3f4',
    terminalTextColor: '#ffebff',
    terminalBackgroundColor: '#28112b'
  },
  {
    id: 'earth',
    name: '赤陶大地',
    group: '自然',
    theme: 'light',
    interfaceBackgroundColor: '#e9d2b6',
    interfaceSurfaceColor: '#f6e8d5',
    accentColor: '#80552f',
    textColor: '#30200f',
    terminalCursorColor: '#d7a667',
    terminalTextColor: '#fff0d8',
    terminalBackgroundColor: '#2b2016'
  },
  {
    id: 'candy',
    name: '糖果霓彩',
    group: '鮮明',
    theme: 'dark',
    interfaceBackgroundColor: '#2d0b28',
    interfaceSurfaceColor: '#5b1950',
    accentColor: '#ff36bd',
    textColor: '#ffe9fa',
    terminalCursorColor: '#ff78d6',
    terminalTextColor: '#ffe8f8',
    terminalBackgroundColor: '#2a0c27'
  },
  {
    id: 'coral',
    name: '亮珊瑚',
    group: '鮮明',
    theme: 'light',
    interfaceBackgroundColor: '#ffd2cb',
    interfaceSurfaceColor: '#ffebe7',
    accentColor: '#ed382e',
    textColor: '#3d0d0b',
    terminalCursorColor: '#ff8276',
    terminalTextColor: '#fff0eb',
    terminalBackgroundColor: '#2c100f'
  },
  {
    id: 'citrus',
    name: '青檸氣泡',
    group: '鮮明',
    theme: 'dark',
    interfaceBackgroundColor: '#1b2306',
    interfaceSurfaceColor: '#48560b',
    accentColor: '#9de600',
    textColor: '#f4ffd9',
    terminalCursorColor: '#c9ff53',
    terminalTextColor: '#f0ffd7',
    terminalBackgroundColor: '#182005'
  },
  {
    id: 'electric',
    name: '電光藍紫',
    group: '鮮明',
    theme: 'light',
    interfaceBackgroundColor: '#d8ccff',
    interfaceSurfaceColor: '#ede7ff',
    accentColor: '#6e36e8',
    textColor: '#1e1044',
    terminalCursorColor: '#aa83ff',
    terminalTextColor: '#f0e8ff',
    terminalBackgroundColor: '#1b1035'
  },
  {
    id: 'neon',
    name: '霓虹街景',
    group: '鮮明',
    theme: 'dark',
    interfaceBackgroundColor: '#06231f',
    interfaceSurfaceColor: '#0f5145',
    accentColor: '#00e6c3',
    textColor: '#ddfff8',
    terminalCursorColor: '#52ffe1',
    terminalTextColor: '#ddfff8',
    terminalBackgroundColor: '#06231f'
  },
  {
    id: 'monochrome',
    name: '黑白鉻影',
    group: '鮮明',
    theme: 'light',
    interfaceBackgroundColor: '#d9dee4',
    interfaceSurfaceColor: '#eef0f3',
    accentColor: '#313943',
    textColor: '#171b20',
    terminalCursorColor: '#e1e8f0',
    terminalTextColor: '#f1f4f8',
    terminalBackgroundColor: '#171b20'
  }
]

export function getColorThemePreset(id: string): ColorThemePreset | undefined {
  return colorThemePresets.find((preset) => preset.id === id)
}

export function isColorThemePresetId(value: unknown): value is string {
  return typeof value === 'string' && colorThemePresets.some((preset) => preset.id === value)
}
