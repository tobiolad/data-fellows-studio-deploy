"""Synthetic admission fixture shared by storage-mode tests."""


def admit_professional(client, professional_id, reviewer):
    path = f"/api/professionals/{professional_id}"
    owner = {"Authorization": f"Bearer test:{professional_id}:professional"}
    if client.get(path + "/application", headers=owner).status_code == 404:
        client.post(path + "/application", headers=owner).raise_for_status()
    existing = client.get(path + "/profile", headers=owner)
    profile = existing.json() if existing.is_success else {"display_name": "Synthetic applicant"}
    profile.update(skills=["Delivery"], evidence_references=[{"label": "Work sample", "reference": "private://synthetic/sample"}])
    saved = client.put(path + "/profile", headers=owner, json=profile)
    saved.raise_for_status()
    client.post(path + "/review", headers=reviewer, json={"status": "under_review"}).raise_for_status()
    response = client.post(path + "/review", headers=reviewer, json={
        "status": "approved", "reason": "Reviewed the synthetic work sample against the delivery criteria",
        "reviewed_profile_version": saved.json()["version"],
    })
    response.raise_for_status()
    return response

def assert_admission_gates(case, candidate):
    """Exercise the same denial contract through each storage adapter."""
    owner = {"Authorization": f"Bearer test:{candidate}:professional"}
    path = f"/api/professionals/{candidate}"
    client = case.client
    client.post(path + "/application", headers=owner).raise_for_status()
    for endpoint in ("/approve", "/decision"):
        case.assertEqual(client.post(path + endpoint, headers=case.admin, json={"decision": "approved"}).status_code, 410)
    review = {"status": "approved", "reason": "Synthetic work sample examined", "reviewed_profile_version": 1}
    check = lambda: client.post(path + "/review", headers=case.admin, json=review).status_code
    case.assertEqual(check(), 409)
    client.post(path + "/review", headers=case.admin, json={"status": "under_review"}).raise_for_status()
    case.assertEqual(check(), 409)
    profile = {"display_name": "Synthetic applicant", "skills": ["Analytics"], "evidence_references": [
        {"label": "Sample", "reference": "quarantine://synthetic/sample", "status": "verified"}]}
    saved = client.put(path + "/profile", headers=owner, json=profile)
    saved.raise_for_status()
    review["reviewed_profile_version"] = saved.json()["version"]
    case.assertEqual(check(), 409)
    profile["evidence_references"][0]["reference"] = "private://synthetic/sample"
    updated = client.put(path + "/profile", headers=owner, json=profile)
    updated.raise_for_status()
    case.assertEqual(check(), 409)
    review["reviewed_profile_version"] = updated.json()["version"]
    case.assertEqual(client.post(path + "/review", headers={"Authorization": f"Bearer test:{candidate}:reviewer"}, json=review).status_code, 409)
    client.post(path + "/review", headers=case.admin, json={"status": "assessment", "missing_information": ["Work history"]}).raise_for_status()
    case.assertEqual(check(), 409)
    case.assertEqual(client.get(path + "/application", headers=owner).json()["status"], "assessment")
