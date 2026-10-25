import assert from 'node:assert/strict'
import test from 'node:test'
import { projectStartupArgs, projectStartupInput } from './terminalProfiles.ts'

test('Windows PowerShell runs cool.py directly in the repo root', () => {
  const profile = {
    id: 'windows-powershell',
    label: 'Windows PowerShell',
    command: 'powershell.exe',
    args: ['-NoLogo', '-NoProfile']
  }
  const args = projectStartupArgs(
    profile,
    'C:\\workspace\\cool app',
    'C:\\workspace\\cool app\\cool.py',
    'C:\\Python\\python.exe',
    [],
    'win32'
  )
  assert.deepEqual(args.slice(0, 3), ['-NoLogo', '-NoProfile', '-NoExit'])
  assert.equal(
    args[4],
    "Set-Location -LiteralPath 'C:\\workspace\\cool app'; & 'C:\\Python\\python.exe' 'C:\\workspace\\cool app\\cool.py'"
  )
})

test('Command Prompt runs cool.py directly', () => {
  const profile = {
    id: 'command-prompt',
    label: 'Command Prompt',
    command: 'cmd.exe',
    args: ['/K']
  }
  assert.deepEqual(
    projectStartupArgs(profile, 'C:\\repo', 'C:\\repo\\cool.py', 'python.exe', [], 'win32'),
    ['/D', '/K']
  )
  assert.equal(
    projectStartupInput(profile, 'C:\\repo\\cool.py', 'python.exe'),
    '"python.exe" "C:\\repo\\cool.py"'
  )
})

test('Visual Studio developer shells retain initialization and then start cool.py', () => {
  const powershell = projectStartupArgs(
    {
      id: 'vs-developer-powershell',
      label: 'Developer PowerShell',
      command: 'powershell.exe',
      args: ['-NoLogo', '-NoExit', '-Command', "& 'C:\\VS\\Launch-VsDevShell.ps1'"]
    },
    'C:\\repo',
    'C:\\repo\\cool.py',
    'py.exe',
    ['-3'],
    'win32'
  )
  assert.match(powershell[3], /Launch-VsDevShell\.ps1/)
  assert.match(powershell[3], /Set-Location -LiteralPath 'C:\\repo'/)
  assert.match(powershell[3], /& 'py\.exe' -3 'C:\\repo\\cool\.py'/)

  const commandPrompt = projectStartupArgs(
    {
      id: 'vs-developer-command',
      label: 'Developer Command Prompt',
      command: 'cmd.exe',
      args: ['/K', 'call "C:\\VS\\VsDevCmd.bat"']
    },
    'C:\\repo',
    'C:\\repo\\cool.py',
    'python.exe',
    [],
    'win32'
  )
  assert.deepEqual(commandPrompt, ['/D', '/K'])
  assert.equal(
    projectStartupInput(
      {
        id: 'vs-developer-command',
        label: 'Developer Command Prompt',
        command: 'cmd.exe',
        args: ['/K', 'call "C:\\VS\\VsDevCmd.bat"']
      },
      'C:\\repo\\cool.py',
      'python.exe'
    ),
    'call "C:\\VS\\VsDevCmd.bat" && "python.exe" "C:\\repo\\cool.py"'
  )
})

test('POSIX profiles run cool.py in the project directory before reopening the shell', () => {
  const args = projectStartupArgs(
    { id: 'bash', label: 'Bash', command: '/bin/bash', args: ['--noprofile', '--norc', '-i'] },
    '/workspace/cool app',
    '/workspace/cool app/cool.py',
    '/usr/bin/python3',
    [],
    'linux'
  )
  assert.equal(
    args[1],
    "'/usr/bin/python3' '/workspace/cool app/cool.py'; exec \"/bin/bash\" --noprofile --norc -i"
  )
})
