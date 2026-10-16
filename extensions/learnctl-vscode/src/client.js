'use strict';

const childProcess = require('node:child_process');
const path = require('node:path');

function resolvePython(root, configured = '', platform = process.platform) {
  const paths = platform === 'win32' ? path.win32 : path.posix;
  if (configured !== '') {
    return paths.isAbsolute(configured) ? configured : paths.resolve(root, configured);
  }
  const executable = platform === 'win32' ? 'Scripts/python.exe' : 'bin/python';
  return paths.resolve(root, '.venv', executable);
}

function resolveLocalPath(root, relative) {
  if (typeof relative !== 'string' || relative.length === 0
      || path.isAbsolute(relative) || path.win32.parse(relative).root !== '') {
    throw new Error('作业文件必须使用项目内的相对路径');
  }
  const absolute = path.resolve(root, relative);
  const contained = path.relative(path.resolve(root), absolute);
  if (contained === '..' || contained.startsWith(`..${path.sep}`) || path.isAbsolute(contained)) {
    throw new Error('作业文件路径不得越出项目目录');
  }
  return absolute;
}

function runCli({root, pythonPath, args, json = true, input, signal, spawn = childProcess.spawn}) {
  return new Promise((resolve, reject) => {
    const commandArgs = ['-m', 'learnctl', ...args];
    if (json) commandArgs.push('--json');
    const child = spawn(pythonPath, commandArgs, {
      cwd: root,
      shell: false,
      windowsHide: true,
      env: {...process.env, PYTHONUTF8: '1'},
      ...(signal ? {signal} : {}),
    });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.on('error', reject);
    // 密钥和问题只经 UTF-8 stdin 传入 Python，不放入进程参数或临时文件。
    if (input !== undefined) {
      child.stdin.on('error', reject);
      child.stdin.end(JSON.stringify(input), 'utf8');
    }
    child.on('close', exitCode => {
      try {
        const result = {exitCode, stdout, stderr};
        if (json) {
          try {
            result.data = JSON.parse(stdout);
          } catch (error) {
            if (exitCode !== 0) throw new Error(stdout + stderr);
            throw error;
          }
          if (result.data.ok === false) throw new Error(result.data.error);
        }
        // 验收失败是可展示的正常结果；其他命令失败继续使用后端原文。
        const failedCheck = json && exitCode === 1 && args[0] === 'practice'
          && args[1] === 'check' && result.data.passed === false;
        if (exitCode !== 0 && !failedCheck) throw new Error(stdout + stderr);
        if (!json) result.text = stdout;
        resolve(result);
      } catch (error) {
        reject(error);
      }
    });
  });
}

module.exports = {resolvePython, resolveLocalPath, runCli};
