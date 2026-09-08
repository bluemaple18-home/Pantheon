"""翻譯 brief 寫入與正式 coordinator 讀取接縫的離線回歸。"""
import copy
from pathlib import Path

import pytest

from scripts import agy_multilingual_pipeline as m
from scripts import agy_gemini_coordinator as c
from test_agy_source_authority_contract import new_brief


@pytest.mark.parametrize('article_id,source_run_id', [
    ('P0-TAROT-89AC8341A6EF', 'content-2eddbf3937-01-7b800e7d-manual-01'),
    ('P0-TAROT-B4DD5B9EA806', 'content-2eddbf3937-03-99b48392'),
])
def test_real_policy_source_enqueue_reaches_exact_cycle(tmp_path, monkeypatch, article_id, source_run_id):
    monkeypatch.delenv('PANTHEON_FORMAL_RUNTIME', raising=False)
    repo = Path(__file__).resolve().parents[1]
    source = m.load_source_article(repo, article_id)
    queue = tmp_path / 'queue'
    record = m.enqueue_article_translations(repo, queue, source_run_id=source_run_id, article_id=article_id, locales=['en'], lane='i18n-new')[0]
    run_dir = Path(record['run_dir'])
    assert (run_dir / 'brief.json').stat().st_size > c.MAX_BRIEF_BYTES
    assert m._load_registered_translation_brief(run_dir)['articles'][0]['source'] == source
    other = m.enqueue_article_translations(repo, queue, source_run_id='offline-unselected-source', article_id=article_id, locales=['en'], lane='i18n-new', source_loader=lambda *_args: source)[0]
    calls = []
    result = c.cycle_once(queue, repo_root=repo, lane_mode=True, exact_run_ids=[record['run_id']], tick=lambda *args: calls.append(args) or {'status': 'OFFLINE_BOUNDARY_REACHED'}, process=lambda *_args, **_kwargs: {'status': 'idle'})
    assert result['status'] == 'ok' and len(calls) == 1
    assert calls[0][0] == run_dir
    assert c.read_run_state(Path(other['run_dir']), queue)['status'] == 'active'


@pytest.mark.parametrize('damage', ['oversize', 'malformed'])
def test_invalid_source_cannot_leave_active_or_brief(tmp_path, damage):
    source = copy.deepcopy(new_brief('en')['articles'][0]['source'])
    if damage == 'oversize':
        source['answer'] = '字' * (m.MAX_TRANSLATION_BRIEF_BYTES // 3 + 1)
    else:
        source['publication_policy']['article_policy']['evidence']['disclosure'] = ''
    with pytest.raises(ValueError):
        m.enqueue_article_translations(tmp_path, tmp_path / 'queue', source_run_id='source-001', article_id=source['article_id'], locales=['en'], lane='i18n-new', source_loader=lambda *_args: source)
    assert not list(tmp_path.rglob('brief.json'))
    assert not list((tmp_path / 'queue/runs').glob('*.json'))


def test_utf8_envelope_exact_limit_and_one_byte_over(tmp_path):
    brief = new_brief('en')
    source = brief['articles'][0]['source']
    size = len(m.pipeline.compact_json_bytes(brief)) + 1
    source['answer'] += 'a' * (m.MAX_TRANSLATION_BRIEF_BYTES - size)
    brief['articles'][0]['source_sha256'] = m.source_sha256(source)
    m.validate_translation_brief(brief)
    m.pipeline.write_json(tmp_path / 'brief.json', brief)
    assert (tmp_path / 'brief.json').stat().st_size == m.MAX_TRANSLATION_BRIEF_BYTES
    assert m.read_translation_brief_payload(tmp_path / 'brief.json') == brief
    source['answer'] += 'a'
    brief['articles'][0]['source_sha256'] = m.source_sha256(source)
    with pytest.raises(ValueError, match='closed size'):
        m.validate_translation_brief(brief)
    with (tmp_path / 'brief.json').open('ab') as handle:
        handle.write(b' ')
    with pytest.raises(ValueError, match='closed size'):
        m.read_translation_brief_payload(tmp_path / 'brief.json')


@pytest.mark.parametrize('mode', ['create', 'rewrite_existing_body'])
def test_other_modes_keep_twelve_kb_cap(tmp_path, mode):
    m.pipeline.write_json(tmp_path / 'brief.json', {'run_id': 'cap-check', 'mode': mode, 'articles': [{'answer': 'a' * c.MAX_BRIEF_BYTES}]})
    with pytest.raises(ValueError, match='12 KB'):
        c.register_run(tmp_path, tmp_path / 'queue')
    assert not list((tmp_path / 'queue/runs').glob('*.json'))


@pytest.mark.parametrize('wrong_hash', [False, True])
def test_direct_registration_validates_before_active_write(tmp_path, monkeypatch, wrong_hash):
    monkeypatch.delenv('PANTHEON_FORMAL_RUNTIME', raising=False)
    brief = new_brief('en')
    brief['lane'] = 'i18n-rewrite'
    source = brief['articles'][0]['source']
    source['answer'] += '字' * 5000
    brief['articles'][0]['source_sha256'] = '0' * 64 if wrong_hash else m.source_sha256(source)
    run_dir = tmp_path / 'queue/translation-runs' / brief['run_id']
    m.pipeline.write_json(run_dir / 'brief.json', brief)
    if wrong_hash:
        with pytest.raises(ValueError, match='source hash'):
            c.register_run(run_dir, tmp_path / 'queue')
        assert not list((tmp_path / 'queue/runs').glob('*.json'))
    else:
        assert c.register_run(run_dir, tmp_path / 'queue')['status'] == 'active'
        assert m._load_registered_translation_brief(run_dir)['articles'][0]['source'] == source
