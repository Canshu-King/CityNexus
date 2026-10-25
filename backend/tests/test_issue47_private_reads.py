from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main, traveler_principal, demo_access
from app.db.models import Base, Journey, JourneyMember, JourneyRoleCapability, Traveler
from app.db.session import get_session


@pytest.fixture
def stack(tmp_path, monkeypatch):
    path = tmp_path / 'classroom.db'
    engine = create_engine('sqlite:///' + path.as_posix(), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    ids = {key: str(uuid4()) for key in ('owner', 'member', 'stranger', 'removed', 'expired', 'no_read', 'journey')}
    with factory() as s:
        for who in ('owner', 'member', 'stranger', 'removed', 'expired', 'no_read'):
            s.add(Traveler(id=ids[who], display_name=who, locale='zh-CN', timezone='Asia/Shanghai', created_at=stamp, updated_at=stamp))
        s.add(Journey(id=ids['journey'], traveler_id=ids['owner'], title='Private classroom', city_code='CN-BJ', timezone='Asia/Shanghai', start_at=stamp, end_at=(now+timedelta(days=2)).isoformat(), budget_currency='CNY', budget_amount_minor=30000, status='DRAFT', created_at=stamp, updated_at=stamp))
        for who in ('owner', 'member', 'removed', 'expired', 'no_read'):
            role = 'NO_READ' if who == 'no_read' else 'OWNER' if who == 'owner' else 'COLLABORATOR'
            s.add(JourneyMember(id=str(uuid4()), journey_id=ids['journey'], traveler_id=ids[who], role=role, invited_by=ids['owner'], created_at=stamp, updated_at=stamp, joined_at=stamp, removed_at=stamp if who=='removed' else None, expires_at=(now-timedelta(days=1)).isoformat() if who=='expired' else None))
        for role in ('OWNER', 'COLLABORATOR'):
            s.add(JourneyRoleCapability(role=role, capability='JOURNEY_READ', scope_message_key='test', created_at=stamp))
        s.commit()
    configured = replace(main.settings, traveler_auth_secret=uuid4().hex+uuid4().hex, demo_mode=True)
    for mod in (main, traveler_principal, demo_access):
        monkeypatch.setattr(mod, 'settings', configured)
    app = FastAPI()
    for route in main.app.routes:
        if getattr(route, 'path', '') in ['/api/v1/journeys/{journey_id}', '/api/v1/journeys/{journey_id}/events', '/api/v1/journeys/{journey_id}/twin', '/api/v1/journeys/{journey_id}/experience', '/api/v1/demo/session', '/api/v1/demo/scene', '/api/v1/journeys', '/api/v1/recycle-bin/journeys']:
            app.add_api_route(route.path, route.endpoint, methods=list(route.methods), response_model=route.response_model)
    def db():
        with factory() as s:
            yield s
    app.dependency_overrides[get_session] = db
    app.add_exception_handler(main.StarletteHTTPException, main.http_error) if hasattr(main,'StarletteHTTPException') else None
    yield TestClient(app), ids, path
    engine.dispose()


@pytest.mark.parametrize('suffix', ['', '/events', '/twin', '/experience'])
@pytest.mark.parametrize('caller,status', [('anonymous',401),('invalid',401),('expired_token',401),('stranger',403),('removed',403),('expired',403),('no_read',403),('owner',200),('member',200)])
def test_private_read_matrix(stack, suffix, caller, status):
    client, ids, _ = stack
    headers = {}
    if caller == 'invalid':
        headers['Authorization'] = 'Bearer not.a.signature'
    elif caller == 'expired_token':
        token = traveler_principal.issue_traveler_token(ids['owner'], now=1)
        headers['Authorization'] = 'Bearer '+token
    elif caller != 'anonymous':
        headers['Authorization'] = 'Bearer '+traveler_principal.issue_traveler_token(ids[caller])
    response = client.get('/api/v1/journeys/'+ids['journey']+suffix, headers=headers)
    assert response.status_code == status, response.text
    if status == 200:
        assert 'no-store' in response.headers['Cache-Control']
    else:
        assert 'Private classroom' not in response.text


def test_demo_session_requires_database_and_presenter(stack, monkeypatch):
    client, _, path = stack
    assert client.get('/api/v1/demo/session').status_code == 503
    monkeypatch.setenv('CITYNEXUS_DEMO_DATABASE_PATH', str(path.resolve()))
    assert client.get('/api/v1/demo/session').status_code == 403
    monkeypatch.setenv('CITYNEXUS_DEMO_PRESENTER_KEY', uuid4().hex+uuid4().hex)
    import os
    response = client.get('/api/v1/demo/session', headers={'X-CityNexus-Presenter-Key': os.environ['CITYNEXUS_DEMO_PRESENTER_KEY']})
    assert response.status_code == 200
    assert 'no-store' in response.headers['Cache-Control']
    monkeypatch.setenv('CITYNEXUS_DEMO_DATABASE_PATH', str(path.parent/'other.db'))
    assert client.get('/api/v1/demo/session').status_code == 503


def test_loopback_does_not_trust_forwarded_headers_or_foreign_origin(stack, monkeypatch):
    client, _, path = stack
    monkeypatch.setenv('CITYNEXUS_DEMO_DATABASE_PATH', str(path.resolve()))
    assert client.get('/api/v1/demo/session', headers={'X-Forwarded-For':'127.0.0.1'}).status_code == 403
    local = TestClient(client.app, client=('127.0.0.1', 30000))
    assert local.get('/api/v1/demo/session').status_code == 403
    assert local.get('/api/v1/demo/session', headers={'Origin':'https://other.example'}).status_code == 403
