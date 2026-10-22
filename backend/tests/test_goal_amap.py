from __future__ import annotations
from dataclasses import replace
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.agent import goal_amap, goal_tasks
from app.db.models import ProviderCall
from test_goal_tasks import goal_scope

class Client:
    calls=[]
    def close(self): pass
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
    def district(self,q):
        self.calls.append(('district',q))
        return {'status':'ok','http_status':200,'districts':[{'name':'连城县','adcode':'350825','level':'district'}]}
    def search(self,q,**kw):
        self.calls.append(('search',kw))
        return {'status':'ok','http_status':200,'places':[
          {'external_id':'amap:B00001','name':'冠豸山','latitude':25.7,'longitude':116.7,'adcode':'350825'},
          {'external_id':'amap:B00002','name':'石门湖','latitude':25.71,'longitude':116.71,'adcode':'350825'},
          {'external_id':'amap:B00003','name':'异地','latitude':26,'longitude':119,'adcode':'350923'}]}
    def walking(self,a,b):
        self.calls.append(('walk',(a,b)))
        return {'status':'ok','http_status':200,'route':{'distance_m':900,'duration_seconds':700}}

def test_amap_goal_receipt_region_and_route(goal_scope,monkeypatch):
    session,journey,member=goal_scope
    monkeypatch.setattr(goal_amap,'settings',replace(goal_amap.settings,amap_web_key='TEST_FIXTURE'))
    monkeypatch.setattr(goal_amap,'_client',Client)
    monkeypatch.setattr('app.agent.goal_artifacts.public_city_label',lambda *a:'连城县')
    Client.calls=[]; task={}
    result=goal_amap.discover_amap_goal_places(session,journey,task,query='景点')
    assert result['status']=='RESULTS' and result['provider_provenance']=='LIVE_PROVIDER'
    assert [p['region_status'] for p in result['places']]==['MATCHED','MATCHED','CONFLICT']
    assert result['places'][0]['coordinate_system']=='GCJ02'
    route=goal_amap.route_public_places(session,journey,task,from_place_id='amap:B00001',to_place_id='amap:B00002')
    assert route['route']['duration_seconds']==700
    assert goal_amap.route_public_places(session,journey,task,from_place_id='amap:B00001',to_place_id='amap:B00002')['cached']
    assert len(Client.calls)==3
    with pytest.raises(HTTPException):
        goal_amap.route_public_places(session,journey,task,from_place_id='amap:B00001',to_place_id='amap:B00003')
    with pytest.raises(HTTPException):
        goal_amap.route_public_places(session,journey,task,from_place_id='OTHER_TASK',to_place_id='amap:B00002')
    session.flush()
    rows=session.scalars(select(ProviderCall)).all()
    assert len(rows)==3 and all(r.status=='SUCCESS' for r in rows)
    assert all('TEST_FIXTURE' not in r.request_json+r.response_json for r in rows)
    assert goal_tasks._safe_args('discover_places',{'source':'amap','query':'公园'},task)['source']=='amap'
    assert 'route_public_places' in goal_tasks._ALLOWED_TOOLS
    assert goal_tasks._safe_tool_result('route_public_places',route)['route']['distance_m']==900


def test_amap_error_is_not_live_receipt(goal_scope,monkeypatch):
    session,journey,_=goal_scope
    result=goal_amap._receipt(session,'test',{}, {'status':'error','reason_code':'AMAP_KEY_INVALID','http_status':200})
    session.flush()
    assert result['status']=='PROVIDER_UNAVAILABLE'
    assert session.scalar(select(ProviderCall)).status=='FAILURE'


class OpeningClient(Client):
    """The same POI answers, some with AMap's own opening sentence and some without a clock at all."""

    def search(self, q, **kw):
        rows = super().search(q, **kw)["places"]
        rows[0]["opening_hours_text"] = "周一至周日 06:30-22:00 最晚进入21:00"
        rows[1]["opening_hours_text"] = "营业时间以官方通知为准"
        return {"status": "ok", "http_status": 200, "places": rows}


def test_a_provider_opening_sentence_reaches_the_place_row(goal_scope, monkeypatch):
    """The departure door asks for opening hours; this is the leg that carries them home.

    Measured live 2026-10-23 (trial/results/20261022_v3_human_chrome/amap-opentime-values-1.txt): AMap
    answers 天坛公园 with a weekday sentence and other POIs with prose that contains no clock.  The first
    has to land in the place row as provider evidence -- it used to be dropped at the client projection,
    which is why every researched place entered the door as 「营业时间 · 待核实」.  The second has to stay
    unresolved: an unreadable sentence must never be read as "open all day".
    """
    import json
    from app.db.models import Place
    from app.services import _place_has_unresolved_opening

    session, journey, member = goal_scope
    monkeypatch.setattr(goal_amap, 'settings', replace(goal_amap.settings, amap_web_key='TEST_FIXTURE'))
    monkeypatch.setattr(goal_amap, '_client', OpeningClient)
    monkeypatch.setattr('app.agent.goal_artifacts.public_city_label', lambda *a: '连城县')
    task = {}
    result = goal_amap.discover_amap_goal_places(session, journey, task, query='景点')
    grounded, unparsable = result['places'][0], result['places'][1]
    assert grounded['opening_status'] == 'VERIFIED_PROVIDER', grounded
    assert grounded['opening_hours']['intervals'][0]['open'] == '06:30'
    assert grounded['opening_hours']['raw'].startswith('周一至周日')
    assert grounded['opening_hours']['weekday_coverage'] == 'UNRESOLVED'
    assert unparsable['opening_status'] == 'RAW_UNPARSED', unparsable
    assert unparsable['opening_hours']['intervals'] == []
    session.flush()
    rows = {row.external_id: row for row in session.scalars(select(Place)).all()}
    assert json.loads(rows['amap:B00001'].opening_hours_json)['status'] == 'VERIFIED_PROVIDER'
    assert json.loads(rows['amap:B00002'].opening_hours_json)['status'] == 'RAW_UNPARSED'
    assert _place_has_unresolved_opening(rows['amap:B00001']) is False
    assert _place_has_unresolved_opening(rows['amap:B00002']) is True
