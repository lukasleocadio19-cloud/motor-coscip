from __future__ import annotations

from fastapi.testclient import TestClient

from tests.integration.test_drawings import (
    JUST,
    ORIGIN,
    Env,
    _door_reference,
    _find,
    _scene,
)
from tests.integration.test_drawings import (
    env as env,
)
from tests.integration.test_drawings import (
    one_drawing as one_drawing,
)


def ready(e, drawing):
    did = drawing['id']
    r = e.post(f'/v1/drawings/{did}/unit-confirmation',
               {'unit': 'm', **_door_reference(), 'real_length_m': .9, 'justification': JUST})
    assert r.status_code == 201, r.text
    f = e.post(f'/v1/drawings/{did}/floors', {
        'name': 'Térreo', 'clip': {'x0': -1, 'y0': -1, 'x1': 11, 'y1': 7}})
    assert f.status_code == 201, f.text
    return f.json()


def current(e, did):
    return e.get(f'/v1/drawings/{did}').json()['model_snapshot']['id']


def classify_door(e, d, floor):
    _, segs = _scene(e, d['id'])
    row = _find(segs, 2, 0, 2.9, 0)
    result = e.post(f'/v1/drawings/{d["id"]}/entities/{row}/classification', {
        'floor_id': floor['id'], 'expected_snapshot_id': current(e, d['id']),
        'property': 'element_class', 'value': 'DOOR', 'justification': JUST,
        'source_checked': True})
    assert result.status_code == 201, result.text
    return row, result.json()


def test_unit_review_requires_confirmation_and_does_not_accept_new_frame(env, one_drawing):
    _, d, _ = one_drawing
    item = env.get('/v1/unit-reviews').json()['items'][0]
    assert item['status'] == 'UNCONFIRMED'
    body = {'expected_frame_id': d['unit']['frame_id'], 'confirmation_id': 'none',
            'reviewer_name': 'Revisor teste', 'justification': JUST, 'reference_checked': True}
    url = f'/v1/drawings/{d["id"]}/unit-review'
    assert env.post(url, body).status_code == 409
    ready(env, d)
    item = env.get('/v1/unit-reviews').json()['items'][0]
    assert item['status'] == 'PENDING' and item['confirmation']['justification'] == JUST
    body.update(expected_frame_id=item['unit']['frame_id'],
                confirmation_id=item['confirmation']['id'])
    anon = TestClient(env.tc.app, base_url=ORIGIN)
    assert anon.post(url, json=body, headers={'Origin': ORIGIN}).status_code == 401
    assert env.post(url, {**body, 'reference_checked': False}).status_code == 422
    r = env.post(url, body)
    assert r.status_code == 201 and r.json()['status'] == 'ACCEPTED'
    assert env.post(url, body).json()['review']['id'] == r.json()['review']['id']
    env.post(f'/v1/drawings/{d["id"]}/unit-confirmation',
             {'unit': 'm', **_door_reference(), 'real_length_m': .9, 'justification': JUST})
    assert env.get('/v1/unit-reviews').json()['items'][0]['status'] == 'PENDING'
    assert env.post(url, body).status_code == 409


def test_property_confirmation_is_individual_immutable_and_detects_stale_frame(env, one_drawing):
    _, d, _ = one_drawing
    floor = ready(env, d)
    old = current(env, d['id'])
    row, first = classify_door(env, d, floor)
    origin = first['element']['source']
    assert origin['handle'] and len(origin['sha256']) == 64 and origin['instance_path']
    assert set(first['element']['properties']) == {'element_class'}
    assert env.get(f'/v1/models/{old}/elements').json()['items'] == []
    body = {'floor_id': floor['id'], 'expected_snapshot_id': first['model_snapshot_id'],
            'property': 'name', 'value': 'Entrada principal', 'justification': JUST,
            'source_checked': True}
    url = f'/v1/drawings/{d["id"]}/entities/{row}/classification'
    r = env.post(url, body)
    assert r.status_code == 201, r.text
    assert set(r.json()['element']['properties']) == {'element_class', 'name'}
    assert env.post(url, body).status_code == 409
    initial = env.get(f'/v1/models/{first["model_snapshot_id"]}/elements').json()['items'][0]
    assert set(initial['properties']) == {'element_class'}
    env.post(f'/v1/drawings/{d["id"]}/unit-confirmation',
             {'unit': 'm', **_door_reference(), 'real_length_m': .9, 'justification': JUST})
    after = env.get(f'/v1/drawings/{d["id"]}/entities/{row}/classification').json()
    assert after['items'][0]['properties']['element_class']['status'] == 'REVIEW_REQUIRED'


def test_classification_candidates_and_boundaries(env, one_drawing):
    _, d, _ = one_drawing
    hints = env.get(f'/v1/drawings/{d["id"]}/classification-candidates').json()
    assert any(c['element_class'] == 'DOOR' for e in hints['items'] for c in e['candidates'])
    floor = ready(env, d)
    _, segs = _scene(env, d['id'])
    row = _find(segs, 2, 0, 2.9, 0)
    small = env.post(f'/v1/drawings/{d["id"]}/floors', {
        'name': 'Outro', 'clip': {'x0': 5, 'y0': 0, 'x1': 10, 'y1': 6}}).json()
    body = {'floor_id': small['id'], 'expected_snapshot_id': current(env, d['id']),
            'property': 'element_class', 'value': 'DOOR', 'justification': JUST,
            'source_checked': True}
    url = f'/v1/drawings/{d["id"]}/entities/{row}/classification'
    assert env.post(url, body).json()['code'] == 'ENTITY_OUTSIDE_FLOOR_CLIP'
    assert env.post(url, {**body, 'floor_id': 'not-this-drawing'}).status_code == 404
    assert env.post(url, {**body, 'floor_id': floor['id'], 'value': 'MADE_UP'}).status_code == 422
    st = env.tc.app.state.coscip
    original = st.tenant_id
    st.tenant_id = 'other-tenant'
    try:
        assert env.get('/v1/unit-reviews').json()['items'] == []
        assert env.get(f'/v1/drawings/{d["id"]}/classification-candidates').status_code == 404
        assert env.post(url, body).status_code == 404
    finally:
        st.tenant_id = original


def test_polygon_clip_rejects_crossing_and_invalid_polygon(env, one_drawing):
    _, d, _ = one_drawing
    ready(env, d)
    url = f'/v1/drawings/{d["id"]}/floors'
    bad = env.post(url, {'name': 'Inválido', 'clip': {
        'type': 'POLYGON', 'points': [[0, 0], [2, 2], [0, 2], [2, 0]]}})
    assert bad.status_code == 422
    f = env.post(url, {'name': 'Em L', 'clip': {
        'type': 'POLYGON', 'points': [[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]}})
    assert f.status_code == 201, f.text
    measure = f'/v1/drawings/{d["id"]}/measure'
    crossing = env.post(measure, {'floor_id': f.json()['id'],
                                  'a': {'x': .5, 'y': 3}, 'b': {'x': 3, 'y': .5}})
    assert crossing.status_code == 422
    assert crossing.json()['code'] == 'MEASUREMENT_OUTSIDE_FLOOR_CLIP'
    assert env.post(measure, {'floor_id': f.json()['id'],
                              'a': {'x': 0, 'y': 0}, 'b': {'x': 4, 'y': 0}}).status_code == 200


def test_area_and_door_dimensions_have_separate_history(env, one_drawing):
    _, d, _ = one_drawing
    floor = ready(env, d)
    url = f'/v1/drawings/{d["id"]}'
    body = {'floor_id': floor['id'], 'expected_snapshot_id': current(env, d['id']),
            'name': 'Sala', 'points': [{'x': 0, 'y': 0}, {'x': 10, 'y': 0},
                                     {'x': 10, 'y': 6}, {'x': 0, 'y': 6}],
            'justification': JUST}
    c = env.post(url + '/contours', body)
    assert c.status_code == 201, c.text
    assert c.json()['item']['area_m2'] == 60
    assert c.json()['item']['uncertainty_m2'] > 0
    assert env.post(url + '/contours', body).status_code == 409
    _, classified = classify_door(env, d, floor)
    element = classified['element']['id']
    for kind, value in [('OPENING', 1), ('LEAF', .9), ('CLEAR', .8)]:
        r = env.post(url + '/door-widths', {'floor_id': floor['id'],
            'expected_snapshot_id': current(env, d['id']), 'element_id': element,
            'kind': kind, 'a': {'x': 2, 'y': 0}, 'b': {'x': 2 + value, 'y': 0},
            'justification': JUST})
        assert r.status_code == 201, r.text
        assert abs(r.json()['item']['value_m'] - value) < 1e-9
    state = env.get(url + '/preparation').json()
    assert len(state['analytical_contours']) == 1 and len(state['door_widths']) == 3
    revised = env.post(url + '/contours', {**body,
        'expected_snapshot_id': current(env, d['id']), 'replaces_id': c.json()['item']['id'],
        'points': [{'x': 0, 'y': 0}, {'x': 5, 'y': 0}, {'x': 5, 'y': 6}, {'x': 0, 'y': 6}]})
    assert revised.status_code == 201 and revised.json()['item']['area_m2'] == 30
    assert env.get(url + '/preparation').json()['door_widths'] == state['door_widths']


def test_review_and_properties_survive_reopen(tmp_path, floor_dxf):
    e = Env(tmp_path / 'persistent', 't1')
    rev, _ = e.import_revision([floor_dxf])
    d = e.get(f'/v1/revisions/{rev}/drawings').json()['items'][0]
    f = ready(e, d)
    _, item = classify_door(e, d, f)
    c = e.get('/v1/unit-reviews').json()['items'][0]
    e.post(f'/v1/drawings/{d["id"]}/unit-review', {
        'expected_frame_id': c['unit']['frame_id'], 'confirmation_id': c['confirmation']['id'],
        'reviewer_name': 'Revisor teste', 'justification': JUST, 'reference_checked': True})
    e.close()
    again = Env(tmp_path / 'persistent', 't2')
    try:
        assert again.get('/v1/unit-reviews').json()['items'][0]['status'] == 'ACCEPTED'
        state = again.get(f'/v1/drawings/{d["id"]}/preparation').json()
        assert state['semantic_elements'][0]['id'] == item['element']['id']
    finally:
        again.close()


def test_extinguisher_curve_can_be_classified_with_recorded_approximation(env, one_drawing):
    _, d, _ = one_drawing
    f = ready(env, d)
    hints = env.get(f'/v1/drawings/{d["id"]}/classification-candidates').json()['items']
    ext = next(e for e in hints if e['type'] == 'CIRCLE'
               and any(c['element_class'] == 'EXTINGUISHER'
                                      for c in e['candidates']))
    r = env.post(f'/v1/drawings/{d["id"]}/entities/{ext["row"]}/classification', {
        'floor_id': f['id'], 'expected_snapshot_id': current(env, d['id']),
        'property': 'element_class', 'value': 'EXTINGUISHER', 'justification': JUST,
        'source_checked': True})
    assert r.status_code == 201, r.text
    assert r.json()['element']['source']['placement_method'] == 'conservative-scene-bounds'


def test_report_is_hashed_escaped_immutable_and_tenant_scoped(env, one_drawing):
    import hashlib

    _, d, _ = one_drawing
    floor = ready(env, d)
    row, _ = classify_door(env, d, floor)
    hostile = '<script>alert(1)</script>'
    env.post(f'/v1/drawings/{d["id"]}/entities/{row}/classification', {
        'floor_id': floor['id'], 'expected_snapshot_id': current(env, d['id']),
        'property': 'name', 'value': hostile, 'justification': JUST, 'source_checked': True})
    url = f'/v1/models/{current(env, d["id"])}/preparation-report'
    r = env.post(url)
    assert r.status_code == 201, r.text
    result = r.json()
    content = env.get(result['content_url']).content
    assert hashlib.sha256(content).hexdigest() == result['sha256']
    assert hostile.encode() not in content and b'&lt;script&gt;' in content
    assert b'Sem avalia' in content
    other = env.post(url).json()
    assert other['id'] != result['id'] and other['artifact_id'] != result['artifact_id']
    assert env.get(result['content_url']).content == content
    st = env.tc.app.state.coscip
    original = st.tenant_id
    st.tenant_id = 'another-tenant'
    try:
        assert env.post(url).status_code == 404
        assert env.get(result['content_url']).status_code == 404
    finally:
        st.tenant_id = original


def test_contour_rejects_crossing_outside_and_door_width_without_class(env, one_drawing):
    _, d, _ = one_drawing
    floor = ready(env, d)
    base = {'floor_id': floor['id'], 'expected_snapshot_id': current(env, d['id']),
            'justification': JUST, 'name': 'Sala'}
    url = f'/v1/drawings/{d["id"]}'
    for points, code in [([(0, 0), (5, 5), (0, 5), (5, 0)], 'INVALID_CONTOUR'),
                         ([(0, 0), (20, 0), (20, 6), (0, 6)], 'CONTOUR_OUTSIDE_FLOOR_CLIP')]:
        r = env.post(url + '/contours', {**base,
            'points': [{'x': x, 'y': y} for x, y in points]})
        assert r.status_code == 422 and r.json()['code'] == code
    r = env.post(url + '/door-widths', {**base, 'element_id': 'unknown', 'kind': 'CLEAR',
                                       'a': {'x': 2, 'y': 0}, 'b': {'x': 2.9, 'y': 0}})
    assert r.status_code == 409
