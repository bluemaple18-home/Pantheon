"""Flash明確路由的相容性與拒絕邊界，不呼叫外部API。"""
import json
from pathlib import Path
import pytest
from scripts import agy_seo_copy_pipeline as p


def route_file(tmp_path, writer, reviewer):
    path=tmp_path/'route.json'
    path.write_text(json.dumps({'schema_version':1,'routes':{'writer':writer,'reviewer':reviewer}}))
    return path


@pytest.mark.parametrize('model',['gemini-3.5-flash-lite','gemini-3.5-flash'])
def test_explicit_writer_reaches_api_client(tmp_path,monkeypatch,model):
    path=route_file(tmp_path,[model],['gemini-3.1-flash-lite'])
    route=p.load_model_route_config(path)
    monkeypatch.setenv('AGY_GEMINI_MODEL_ROUTE_CONFIG',str(path))
    monkeypatch.setenv('AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST',route.digest)
    monkeypatch.setenv('AGY_GEMINI_TRANSPORT','api')
    monkeypatch.setenv('AGY_WRITER_MODEL',model)
    monkeypatch.setenv('AGY_REVIEWER_MODEL','gemini-3.1-flash-lite')
    monkeypatch.setenv('PANTHEON_FORMAL_RUNTIME','1')
    monkeypatch.setattr(p,'_load_api_key',lambda:'offline-only')
    client=p.GeminiClient.from_environment()
    assert client.writer_model==model
    assert client.reviewer_model=='gemini-3.1-flash-lite'
    assert p.validate_gemini_api_model_capabilities(route)['writer_model']==model


@pytest.mark.parametrize('writer,reviewer',[
    (['unknown-model'],['gemini-3.1-flash-lite']),
    (['gemini-3.5-flash','gemini-3.5-flash-lite'],['gemini-3.1-flash-lite']),
    (['gemini-3.5-flash'],['gemini-3.1-pro']),
])
def test_unapproved_routes_stay_blocked(tmp_path,writer,reviewer):
    route=p.load_model_route_config(route_file(tmp_path,writer,reviewer))
    with pytest.raises(ValueError):p.validate_gemini_api_model_capabilities(route)
