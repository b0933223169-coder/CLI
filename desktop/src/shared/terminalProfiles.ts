import type { TerminalProfile } from './types'

function quotePowerShell(value: string): string {
  return `'${value.replace(/'/g, "''")}'`
}

function quotePosix(value: string): string {
  return `'${value.replace(/'/g, "'\\''")}'`
}

export function projectStartupArgs(
  profile: TerminalProfile,
  projectRoot: string,
  scriptPath: string,
  pythonCommand: string,
  pythonPrefixArgs: string[] = [],
  platform = 'win32'
): string[] {
  const cwd = platform === 'win32' ? projectRoot : projectRoot.replace(/\\/g, '/')
  if (platform === 'win32') {
    if (profile.id === 'command-prompt' || profile.id === 'vs-developer-command') {
      return ['/D', '/K']
    }
    const pythonInvocation = [
      '&',
      quotePowerShell(pythonCommand),
      ...pythonPrefixArgs,
      quotePowerShell(scriptPath)
    ].join(' ')
    const commandIndex = profile.args.indexOf('-Command')
    const developerSetup =
      profile.id === 'vs-developer-powershell' && commandIndex >= 0
        ? profile.args[commandIndex + 1]
        : undefined
    const baseArgs = commandIndex >= 0 ? profile.args.slice(0, commandIndex) : profile.args.slice()
    return [
      ...baseArgs.filter((arg) => arg !== '-NoExit'),
      '-NoExit',
      '-Command',
      [developerSetup, `Set-Location -LiteralPath ${quotePowerShell(cwd)}`, pythonInvocation]
        .filter(Boolean)
        .join('; ')
    ]
  }

  const command = [
    quotePosix(pythonCommand),
    ...pythonPrefixArgs.map(quotePosix),
    quotePosix(scriptPath)
  ].join(' ')
  const shellName = profile.id
  const interactiveArgs =
    shellName === 'bash'
      ? ['--noprofile', '--norc', '-i']
      : shellName === 'zsh'
        ? ['-f', '-i']
        : ['-i']
  return ['-c', `${command}; exec "${profile.command}" ${interactiveArgs.join(' ')}`]
}

export function projectStartupInput(
  profile: TerminalProfile,
  scriptPath: string,
  pythonCommand: string,
  pythonPrefixArgs: string[] = []
): string | undefined {
  if (profile.id !== 'command-prompt' && profile.id !== 'vs-developer-command') return undefined
  const commandPrefix = profile.id === 'vs-developer-command' ? (profile.args[1] ?? '') : ''
  const pythonCommandLine = [`"${pythonCommand}"`, ...pythonPrefixArgs, `"${scriptPath}"`].join(' ')
  return `${commandPrefix ? `${commandPrefix} && ` : ''}${pythonCommandLine}`
}
