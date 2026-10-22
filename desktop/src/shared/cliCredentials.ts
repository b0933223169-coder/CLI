import { createHash } from 'node:crypto'
import { hostname, networkInterfaces } from 'node:os'
import { readFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'

export function decryptCliPassword(
  encrypted: string,
  passwordLength: number | undefined,
  machineIds: readonly string[]
): string {
  if (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encrypted)) {
    throw new Error('終端儲存的密碼格式不正確。')
  }
  const cipherText = Buffer.from(encrypted, 'base64')
  for (const machineId of machineIds) {
    const key = createHash('sha256').update(`${machineId}cool_salt_v1`).digest()
    const plainText = Buffer.from(cipherText)
    for (let index = 0; index < plainText.length; index += 1) {
      plainText[index] ^= key[index % key.length]
    }
    let password: string
    try {
      password = new TextDecoder('utf-8', { fatal: true }).decode(plainText)
    } catch {
      continue
    }
    if (
      !password ||
      Array.from(password).length > 512 ||
      Array.from(password).some((character) => {
        const codePoint = character.codePointAt(0) ?? 0
        return codePoint <= 31 || codePoint === 127
      }) ||
      (passwordLength !== undefined && Array.from(password).length !== passwordLength)
    ) {
      continue
    }
    return password
  }
  throw new Error('無法解密終端帳號密碼；請在桌面帳號頁重新登入一次，讓密碼以系統加密方式保存。')
}

export async function cliPasswordMachineIds(): Promise<string[]> {
  for (const path of ['/etc/machine-id', '/var/lib/dbus/machine-id']) {
    try {
      const machineId = (await readFile(path, 'utf8')).trim()
      if (machineId) return [machineId]
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
    }
  }

  const addresses = new Set<string>()
  if (process.platform === 'win32') {
    try {
      const adapters = execFileSync('getmac.exe', ['/fo', 'csv', '/nh'], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore']
      })
      for (const match of adapters.matchAll(/(?:[0-9a-f]{2}-){5}[0-9a-f]{2}/gi)) {
        addresses.add(match[0].replaceAll('-', '').toLowerCase())
      }
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
    }
  }
  for (const interfaces of Object.values(networkInterfaces())) {
    for (const networkInterface of interfaces ?? []) {
      if (
        networkInterface.internal ||
        !/^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$/i.test(networkInterface.mac)
      ) {
        continue
      }
      addresses.add(networkInterface.mac.replaceAll(':', '').toLowerCase())
    }
  }
  const macIds = [...addresses].sort((left, right) => {
    const leftLocal = (parseInt(left.slice(0, 2), 16) & 2) !== 0
    const rightLocal = (parseInt(right.slice(0, 2), 16) & 2) !== 0
    return Number(leftLocal) - Number(rightLocal)
  })
  if (!macIds.length) {
    throw new Error('無法讀取本機網路介面，無法匯入終端儲存的密碼。')
  }
  return macIds.map((mac) => `${hostname()}-${BigInt(`0x${mac}`).toString()}`)
}
