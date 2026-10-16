"""The authored audit must cover every retained D05-D28 section."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_authored_audit_matches_all_current_exercise_sections():
    course=json.loads((ROOT/'data/curriculum.json').read_text(encoding='utf-8'))
    bundle=json.loads((ROOT/'scripts/course_readiness_data.json').read_text(encoding='utf-8'))
    expected={section['id'] for task in course['tasks'] if 'D05'<=task['id']<='D28' for section in task['lesson']}
    entries={entry.get('section',entry.get('id')):entry for entry in bundle['coverage']}
    assert len(entries)==len(bundle['coverage'])
    assert set(entries)==expected
    for sid,entry in entries.items():
        assert entry.get('requires',entry.get('required',entry.get('formal'))),sid
        assert entry.get('evidence'),sid
    assert len(expected)==119

def test_new_agent_task_is_separate_from_the_retained_project():
    course=json.loads((ROOT/'data/curriculum.json').read_text(encoding='utf-8'))
    task=next(task for task in course['tasks']if task['id']=='D29')
    assert task['prerequisites']==['D28']
    assert [s['id']for s in task['lesson']]==['D29-tools','D29-loop','D29-delivery']
    assert [s['practice']['project_file']for s in task['lesson']]==['agentlab/tools.py','agentlab/runner.py','tests/test_agentlab.py']
    assert course['curriculum_version']=='3.0.0'
    assert course['meta']['practice_first_revision']==2
