'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { runCli } = require('../src/client');
const { renderLesson } = require('../src/lesson');

async function main() {
  const [root, pythonPath] = process.argv.slice(2);
  assert.ok(root && pythonPath, '必须明确指定课程根目录和 Python 解释器');
  const curriculum = JSON.parse(await fs.readFile(path.join(root, 'data/curriculum.json'), 'utf8'));
  let count = 0;
  for (const task of curriculum.tasks) {
    const { data } = await runCli({ root, pythonPath, args: ['lesson', task.id] });
    for (const section of data.task.lesson.sections) {
      const html = renderLesson(data, section);
      assert.ok(html.includes('本节作业'), `${section.id} 未生成作业内容`);
      if (section.local_file) assert.ok(html.includes('data-action="check"'));
      else assert.ok(!html.includes('data-action="check"'));
      count += 1;
    }
  }
  console.log(JSON.stringify({ passed: true, tasks: curriculum.tasks.length, sections: count }));
}

main().catch(error => { console.error(error); process.exitCode = 1; });
