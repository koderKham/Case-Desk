import os
import tempfile
from pathlib import Path

import pytest

import app as case_app


@pytest.fixture()
def client(tmp_path):
    test_db = tmp_path / "test.db"
    test_uploads = tmp_path / "uploads"
    test_uploads.mkdir()

    case_app.app.config.update(
        TESTING=True,
        DATABASE=str(test_db),
        UPLOAD_FOLDER=str(test_uploads),
        SECRET_KEY="test-secret",
    )

    with case_app.app.app_context():
        case_app.init_db()
        case_app.seed_db()

    with case_app.app.test_client() as client:
        yield client


def login(client):
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "token"
    return client.post(
        "/login",
        data={"email": "admin@example.com", "password": "ChangeMe123!", "_csrf_token": "token"},
        follow_redirects=True,
    )


def test_login_and_dashboard(client):
    response = login(client)
    assert response.status_code == 200
    assert b"Firm Dashboard" in response.data


def test_create_person_with_multiple_roles(client):
    login(client)
    with client.session_transaction() as sess:
        token = sess["_csrf_token"]
    response = client.post(
        "/people/new",
        data={
            "_csrf_token": token,
            "person_type": "Individual",
            "first_name": "Andre",
            "last_name": "Daley",
            "roles": ["Client", "Heir"],
            "email": "andre@example.com",
            "phone": "954-555-0000",
            "address": "",
            "city": "Fort Lauderdale",
            "state": "FL",
            "zip_code": "33301",
            "notes": "Test client",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Andre Daley" in response.data
    assert b"Heir" in response.data


def test_create_business_and_link_witness_to_matter(client):
    login(client)
    with client.session_transaction() as sess:
        token = sess["_csrf_token"]
    response = client.post(
        "/people/new",
        data={
            "_csrf_token": token,
            "person_type": "Business",
            "organization_name": "Blue Martini",
            "roles": ["Witness"],
            "state": "FL",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Blue Martini" in response.data
    with case_app.app.app_context():
        db = case_app.get_db()
        person_id = db.execute("SELECT id FROM persons WHERE organization_name='Blue Martini'").fetchone()[0]
        matter_id = db.execute("SELECT id FROM matters ORDER BY id LIMIT 1").fetchone()[0]
    response = client.post(
        f"/matters/{matter_id}/people",
        data={"_csrf_token": token, "person_id": person_id, "role": "Witness", "relationship_notes": "Records custodian"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Records custodian" in response.data


def test_search(client):
    login(client)
    response = client.get("/search?q=Jordan")
    assert response.status_code == 200
    assert b"Jordan Smith" in response.data


def test_create_criminal_intake(client):
    login(client)
    with client.session_transaction() as sess:
        token = sess["_csrf_token"]
    response = client.post(
        "/intakes/new/criminal",
        data={
            "_csrf_token": token,
            "first_name": "Brandon",
            "last_name": "Williams",
            "email": "brandon@example.com",
            "phone": "954-555-1000",
            "preferred_contact": "Phone",
            "state": "FL",
            "charges": "Battery",
            "custody_status": "Released on Bond",
            "client_account": "Test intake facts.",
            "conflict_names": "State of Florida; John Doe",
            "urgency": "Arraignment next week",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Brandon Williams" in response.data
    assert b"Battery" in response.data
    assert b"Criminal Defense" in response.data


def test_convert_intake_to_client_and_matter(client):
    login(client)
    with client.session_transaction() as sess:
        token = sess["_csrf_token"]
    create = client.post(
        "/intakes/new/probate",
        data={
            "_csrf_token": token,
            "first_name": "Ursil",
            "last_name": "Douglas",
            "state": "FL",
            "decedent_name": "Sample Decedent",
            "relationship_to_decedent": "Family member",
        },
        follow_redirects=False,
    )
    assert create.status_code == 302
    detail_url = create.headers["Location"]
    intake_id = int(detail_url.rstrip("/").split("/")[-1])
    response = client.post(
        f"/intakes/{intake_id}/convert",
        data={"_csrf_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Estate of Sample Decedent" in response.data
