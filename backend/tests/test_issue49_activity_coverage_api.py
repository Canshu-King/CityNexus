from test_issue47_private_reads import stack  # noqa: F401
from test_issue47_simulation import sim  # noqa: F401

from app.db.models import Activity, Journey


def test_signed_progress_separates_inherited_completion_from_current_run(sim):
    client, ids, _, factory, headers, url, post = sim
    generator = factory()
    session = next(generator)
    journey = session.get(Journey, ids["journey"])
    journey.end_at = "2026-12-04T21:00:00+08:00"
    session.get(Activity, ids["activities"][0]).status = "COMPLETED"
    journey.current_activity_id = ids["activities"][1]
    session.commit()
    generator.close()

    started = post(url, {"seed": 49})
    assert started.status_code == 201
    response = client.get(url + "/" + started.json()["run_id"] + "/progress", headers=headers)
    assert response.status_code == 200
    coverage = response.json()["activity_coverage"]
    assert coverage["plan_version_id"] == ids["plan"]
    assert coverage["target_kind"] == "CLASSROOM_DISPLAY_ONLY"
    days = coverage["days"]
    assert [day["date"] for day in days] == ["2026-12-03", "2026-12-04"]
    assert [day["distinct_place_count"] for day in days] == [1, 1]
    assert [day["missing_for_target"] for day in days] == [1, 1]
    assert days[0]["inherited_completed_activity_ids"] == [ids["activities"][0]]
    assert all(day["run_completed_place_count"] == 0 for day in days)
