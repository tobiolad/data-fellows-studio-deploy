"""Shared review workflow regression assertions for the two storage adapters."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from backend.admission_fixture import admit_professional


def assert_review_workflow(case):
    client = case.client
    reviewer = "review-" + uuid4().hex
    headers = {"Authorization": f"Bearer test:{reviewer}:reviewer"}

    def create(path, body):
        response = client.post(path, headers=case.admin, json=body)
        response.raise_for_status()
        return response.json()

    org = create("/api/organizations", {"name": "Review fixture"})
    engagement = create("/api/engagements", {"name": "Reporting", "organization_id": org["id"], "objective": "Review performance"})
    project = create("/api/projects", {"engagement_id": engagement["id"], "name": "Delivery"})
    package = create("/api/work-packages", {"project_id": project["id"], "title": "Weekly report", "acceptance_criteria": ["Include totals"]})
    submission = {"title": "Summary", "content": "Weekly totals", "work_package_id": package["id"]}
    professional = "delivery-" + uuid4().hex
    professional_headers = {"Authorization": f"Bearer test:{professional}:professional"}
    admit_professional(client, professional, case.admin)
    create(f"/api/organizations/{org['id']}/members", {"actor_id": professional, "role": "professional"})
    invitation = create(f"/api/work-packages/{package['id']}/assignments", {"professional_id": professional})
    case.assertEqual(client.post("/api/deliverables", headers=professional_headers, json=submission).status_code, 403)
    client.post(f"/api/assignments/{invitation['id']}/accept", headers=professional_headers).raise_for_status()
    client.delete(f"/api/organizations/{org['id']}/members/{professional}/professional", headers=case.admin).raise_for_status()
    case.assertEqual(client.post("/api/deliverables", headers=professional_headers, json=submission).status_code, 403)
    first = create("/api/deliverables", submission)
    queue = "/api/reviewer/queue"
    case.assertEqual(client.get(queue, headers=headers).json()["items"], [])
    case.assertNotIn(first["id"], [row["id"] for row in client.get(queue, headers=case.admin).json()["items"]])
    create(f"/api/organizations/{org['id']}/members", {"actor_id": reviewer, "role": "reviewer"})
    case.assertEqual(client.get(queue, headers={"Authorization": f"Bearer test:{reviewer}:client"}).status_code, 403)
    items = client.get(queue, headers=headers).json()["items"]
    case.assertEqual([item["id"] for item in items], [first["id"]])
    case.assertEqual(items[0]["acceptance_criteria"], ["Include totals"])
    decision = {"decision": "revision_requested", "comment": "Add a weekly comparison"}
    first_path = f"/api/deliverables/{first['id']}/review"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post(first_path, headers=headers, json=decision).status_code, range(2)))
    case.assertEqual(sorted(results), [200, 409])
    successor = create("/api/deliverables", {**submission, "content": "Weekly totals and comparison"})
    items = client.get(queue, headers=headers).json()["items"]
    case.assertEqual([item["id"] for item in items], [successor["id"]])
    case.assertEqual(items[0]["previous_reviews"], [{"version": 1, **decision}])
    client.delete(f"/api/organizations/{org['id']}/members/{reviewer}/reviewer", headers=case.admin).raise_for_status()
    case.assertEqual(client.get(queue, headers=headers).json()["items"], [])
    case.assertEqual(client.post(f"/api/deliverables/{successor['id']}/review", headers=headers, json=decision).status_code, 403)
