"""Signed API / SQLite integration. Provider facts here are TEST_FIXTURE."""
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main
from app.db.models import JourneyIntent, RealPlaceCandidate, PlanVersion
from app.db.session import SessionLocal
from app.planning.travel_brief import preference_items
from app.execution import bootstrap_place_facts as facts
from test_bootstrap_place_facts import enabled_settings, signed_place


def test_atomic_signed_trip_brief_and_fresh_client_restore(enabled_settings):
    with TestClient(main.app) as client:
        owner = client.post('/api/v1/travelers', json={'display_name':'TEST_FIXTURE trip owner','timezone':'Asia/Shanghai'}).json()
        headers = {'Authorization': 'Bearer ' + owner['access_token']}
        payload = {'traveler_id':owner['id'],'title':'TEST_FIXTURE three days','city_code':uuid4().hex,
            'timezone':'Asia/Shanghai','start_at':'2026-11-01T09:00:00+08:00','end_at':'2026-11-03T20:00:00+08:00',
            'budget':{'amount_minor':200000,'currency':'CNY'},'party_size':2,
            'planning_intent':{'goal':'美食、海边、少走路，睡到中午，下雨才去室内','interests':['cafe'],'energy':'easy'}}
        assert client.post('/api/v1/journeys', json=payload).status_code == 401
        response = client.post('/api/v1/journeys', headers=headers,json=payload)
        assert response.status_code == 201,response.text
        path = '/api/v1/journeys/' + response.json()['id'] + '/planning-intent'
        value=client.get(path,headers=headers)
        assert value.status_code == 200,value.text
        assert 'no-store' in value.headers['cache-control']
        result=value.json()
        assert len(result['trip']['dates'])==3
        assert result['trip']['party_size']==2
        assert result['trip']['budget']['amount_minor']==200000
        assert result['intent']['goal']==payload['planning_intent']['goal']
        assert result['intent']['free_text_status']=='PRESERVED_NOT_FULLY_COMPILED'
        with SessionLocal() as session:
            prefs={item.preference_key:json.loads(item.value_json) for item in preference_items(session,owner['id'],response.json()['id'])}
            assert prefs['food'] is True and prefs['low_walking'] is True
            assert prefs['day_rhythm']['wake_minute']==720
            assert 'indoor' not in prefs  # Conditional rain is not live weather.
    with TestClient(main.app) as second_device:
        assert second_device.get(path,headers=headers).json()['intent']['id']==result['intent']['id']


def test_saved_brief_is_owner_scoped_and_updated_without_new_intents(signed_place):
    client,headers,outsider,journey_id,*_=signed_place
    path=f'/api/v1/journeys/{journey_id}/planning-intent'
    body={'goal':'海边、美食','interests':['cafe'],'energy':'easy'}
    assert client.put(path,json=body).status_code==401
    assert client.put(path,json=body,headers=outsider).status_code==403
    first=client.put(path,json=body,headers=headers)
    assert first.status_code==200,first.text
    second=client.put(path,json={**body,'goal':'博物馆'},headers=headers)
    assert second.status_code==200,second.text
    assert second.json()['intent']['id']==first.json()['intent']['id']
    assert client.get(path,headers=outsider).status_code==403
    assert client.get(path,headers=headers).json()['intent']['goal']=='博物馆'
    with SessionLocal() as session:
        rows=session.scalars(select(JourneyIntent).where(JourneyIntent.journey_id==journey_id)).all()
        assert len(rows)==1


def test_two_private_candidates_feed_native_generator_without_inventing_facts(monkeypatch,signed_place):
    client,headers,outsider,journey_id,first_id,receipt,*_=signed_place
    base=f'/api/v1/journeys/{journey_id}'
    second_id=str(uuid4())
    with SessionLocal() as session:
        first=session.get(RealPlaceCandidate,first_id)
        first.external_id='photon:way/' + str(uuid4().int % 1000000000 + 1000000000)
        session.add(RealPlaceCandidate(id=second_id,journey_id=journey_id,provider_key='photon',external_id='photon:way/' + str(uuid4().int % 1000000000 + 2000000000),
            city_code=first.city_code,name='TEST_FIXTURE second park',category='park',latitude=31.201,longitude=121.401,
            captured_at=first.captured_at,expires_at=first.expires_at,evidence_json=first.evidence_json,status='BOOTSTRAP_PRIVATE'))
        session.commit()
    brief=client.put(base+'/planning-intent',headers=headers,json={'goal':'少走路，睡到中午','interests':['park/garden'],'energy':'easy'})
    assert brief.status_code==200,brief.text
    assert len(brief.json()['candidates'])==2
    assert brief.json()['plan_version_id'] is None
    ids=[first_id,second_id]
    body={'candidate_count':1,'bootstrap_candidate_ids':ids}
    refused=client.post(base+'/plans/generate',headers=headers,json=body)
    assert refused.status_code==422,refused.text
    assert client.get(base+'/plans',headers=headers).json()==[]
    monkeypatch.setattr(facts,'read_osm_tags',lambda *_:{'opening_hours':'24/7','fee':'no'})
    for candidate_id in ids:
        response=client.post(base+'/bootstrap-discovery/facts',headers=headers,json={
            'receipt_id':receipt,'candidate_id':candidate_id,'provider_consent':True})
        assert response.status_code==200,response.text
    assert client.post(base+'/plans/generate',headers=outsider,json=body).status_code==403
    key=str(uuid4())
    generated=client.post(base+'/plans/generate',headers={**headers,'Idempotency-Key':key},json=body)
    assert generated.status_code==201,generated.text
    assert len({a['place_id'] for a in generated.json()[0]['activities'] if a.get('place_id')})>=2
    assert all(int(a['start_at'][11:13]) >= 12 for a in generated.json()[0]['activities'])
    replay=client.post(base+'/plans/generate',headers={**headers,'Idempotency-Key':key},json=body)
    assert replay.status_code==201,replay.text
    assert replay.json()[0]['id']==generated.json()[0]['id']
    again=client.post(base+'/plans/generate',headers={**headers,'Idempotency-Key':str(uuid4())},json=body)
    assert again.status_code==201,again.text
    assert again.json()[0]['id'] != generated.json()[0]['id']
    with SessionLocal() as session:
        plan=session.get(PlanVersion,generated.json()[0]['id'])
        intent=json.loads(plan.explanation_json)['travel_brief']
        assert intent['intent_id']==brief.json()['intent']['id']
        assert 'goal' not in intent and 'preferences' not in intent


def test_persisted_food_preference_changes_native_provider_ranking(signed_place):
    from app.services import _strategy_place_score
    from app.db.models import Place, Journey
    from app.execution.traveler_twin import planning_preference_items
    client,headers,_,journey_id,*_=signed_place
    assert client.put(f'/api/v1/journeys/{journey_id}/planning-intent',headers=headers,
        json={'goal':'想吃美食','interests':['cafe'],'energy':'steady'}).status_code==200
    with SessionLocal() as session:
        journey=session.get(Journey,journey_id)
        prefs=planning_preference_items(session,journey.traveler_id,journey_id)
        cafe=Place(id='TEST_FIXTURE_CAFE',name='cafe',category='cafe',tags_json='[]',opening_hours_json='{}',metadata_json='{}')
        park=Place(id='TEST_FIXTURE_PARK',name='park',category='park',tags_json='[]',opening_hours_json='{}',metadata_json='{}')
        assert _strategy_place_score(cafe,'balanced',prefs)[0] > _strategy_place_score(park,'balanced',prefs)[0]
