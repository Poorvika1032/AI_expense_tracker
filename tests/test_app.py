import sqlite3

import app as application


def test_expense_is_scoped_to_own_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(application, "DB_PATH", db_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO users(name,email,password) VALUES('Traveler','t@example.com','hash')")
        conn.execute("INSERT INTO users(name,email,password) VALUES('Other','o@example.com','hash')")
        conn.execute("INSERT INTO travel_history(user_id,source,destination,travelers,days,transportation,predicted_expense,budget) VALUES(1,'A','B',1,2,'Train',1000,1500)")
        conn.execute("INSERT INTO travel_history(user_id,source,destination,travelers,days,transportation,predicted_expense,budget) VALUES(2,'C','D',1,2,'Bus',900,1200)")
    application.app.config.update(TESTING=True)
    client = application.app.test_client()
    with client.session_transaction() as sess:
        sess.update(user_id=1, user="Traveler", role="USER", csrf_token="test-token")
    response = client.post("/trips/1/expenses", data={
        "csrf_token": "test-token", "category": "Food", "description": "Lunch",
        "amount": "250", "expense_date": "2026-10-09"
    })
    assert response.status_code == 302
    assert client.get("/trips/2").status_code == 404
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT amount FROM expenses").fetchone()[0] == 250


def test_post_requires_csrf_token():
    client = application.app.test_client()
    response = client.post("/login", data={"email": "nobody@example.com", "password": "bad"})
    assert response.status_code == 400

def test_prediction_and_role_guard_with_scoped_database(tmp_path, monkeypatch):
    import re

    db_path = tmp_path / "prediction.db"
    monkeypatch.setattr(application, "DB_PATH", db_path)
    application.create_database()
    application.app.config.update(TESTING=True)
    client = application.app.test_client()
    page = client.get("/register")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)).group(1)
    response = client.post("/register", data={"csrf_token": token, "name": "Test User",
        "email": "test@example.com", "password": "secure-pass-123"})
    assert response.status_code == 302
    login_page = client.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', login_page).group(1)
    response = client.post("/login", data={"csrf_token": token,
        "email": "test@example.com", "password": "secure-pass-123"})
    assert response.status_code == 302
    assert client.get("/admin").status_code == 403
    prediction_page = client.get("/dashboard").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', prediction_page).group(1)
    assert "Live trip preview" in prediction_page
    what_if_page = client.get("/what-if").get_data(as_text=True)
    assert "type=\"range\"" in what_if_page and "what_if.js" in what_if_page
    assert client.get("/calendar").status_code == 200
    assert client.get("/assistant").status_code == 200
    assistant_response = client.post("/assistant", data={"csrf_token": token, "question": "estimate this route",
        "source": "Bangalore", "destination": "Mysore", "days": "2", "travelers": "2",
        "transportation": "Train", "budget": "10000"})
    assert assistant_response.status_code == 200
    assert "lowest estimate" in assistant_response.get_data(as_text=True)
    response = client.post("/predict", data={"csrf_token": token, "source": "Bangalore",
        "destination": "Mysore", "travelers": "2", "days": "2",
        "transportation": "Train", "budget": "10000"})
    assert response.status_code == 200
    assert "Total Estimated Cost" in response.get_data(as_text=True)
    assert client.post("/logout", data={"csrf_token": token}).status_code == 302

def test_wishlist_and_dataset_recommendations(tmp_path, monkeypatch):
    import re

    db_path = tmp_path / "wishlist.db"
    monkeypatch.setattr(application, "DB_PATH", db_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO users(name,email,password) VALUES('Traveler','t@example.com','hash')")
    client = application.app.test_client()
    with client.session_transaction() as sess:
        sess.update(user_id=1, user="Traveler", role="USER", csrf_token="token")
    response = client.post("/wishlist", data={"csrf_token": "token", "destination": "Goa",
        "estimated_cost": "5000", "target_date": "2027-01-01", "notes": "Beach trip"})
    assert response.status_code == 200
    assert "Goa" in response.get_data(as_text=True)
    response = client.post("/recommendations", data={"csrf_token": "token", "source": "Bangalore",
        "travelers": "2", "days": "2", "budget": "10000", "transportation": "Train"})
    assert response.status_code == 200
    assert "Model estimate" in response.get_data(as_text=True)

def test_admin_dataset_upload_and_model_version_training(tmp_path, monkeypatch):
    from io import BytesIO

    db_path = tmp_path / "admin.db"
    monkeypatch.setattr(application, "DB_PATH", db_path)
    monkeypatch.setattr(application, "BASE_DIR", tmp_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO users(name,email,password,role) VALUES('Admin','admin@example.com','hash','ADMIN')")
    client = application.app.test_client()
    with client.session_transaction() as sess:
        sess.update(user_id=1,user="Admin",role="ADMIN",csrf_token="admin-token")
    data = application.DATA_PATH.read_bytes()
    uploaded = client.post("/admin/dataset", data={"csrf_token":"admin-token",
        "dataset":(BytesIO(data),"travel.csv")}, content_type="multipart/form-data")
    assert uploaded.status_code == 200
    assert "Duplicate rows" in uploaded.get_data(as_text=True)
    with sqlite3.connect(db_path) as conn:
        stored = conn.execute("SELECT stored_name FROM datasets").fetchone()[0]
    response = client.post("/admin/model/train", data={"csrf_token":"admin-token","dataset":stored})
    assert response.status_code == 302
    with sqlite3.connect(db_path) as conn:
        version = conn.execute("SELECT version,is_active,dataset_size FROM model_versions").fetchone()
    assert version[0] == "v1" and version[1] == 1 and version[2] >= 4
    assert client.get("/admin/models").status_code == 200


def test_pdf_report_has_pdf_signature():
    client = application.app.test_client()
    with client.session_transaction() as sess:
        sess.update(user_id=1,user="Traveler",role="USER",csrf_token="token")
    response = client.get("/reports/export.pdf")
    assert response.status_code == 200
    assert response.data.startswith(b"%PDF-1.4")

def test_authenticated_json_prediction_requires_csrf(tmp_path, monkeypatch):
    db_path=tmp_path/"api.db"
    monkeypatch.setattr(application,"DB_PATH",db_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO users(name,email,password) VALUES('Traveler','api@example.com','hash')")
    client=application.app.test_client()
    with client.session_transaction() as sess:
        sess.update(user_id=1,user="Traveler",role="USER",csrf_token="api-token")
    denied=client.post("/api/predict",json={"source":"Bangalore","destination":"Mysore","travelers":2,"days":2,"budget":10000})
    assert denied.status_code==400
    response=client.post("/api/predict",json={"source":"Bangalore","destination":"Mysore","travelers":2,"days":2,"budget":10000},headers={"X-CSRF-Token":"api-token"})
    assert response.status_code==200
    payload=response.get_json()
    assert payload["success"] and "predictions" in payload["data"]
from io import BytesIO
from PIL import Image


def test_profile_theme_and_safe_image_upload(tmp_path, monkeypatch):
    db_path=tmp_path/"profile.db"
    monkeypatch.setattr(application,"DB_PATH",db_path)
    monkeypatch.setattr(application,"BASE_DIR",tmp_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO users(name,email,password) VALUES('Traveler','profile@example.com','hash')")
    client=application.app.test_client()
    with client.session_transaction() as sess:sess.update(user_id=1,user="Traveler",role="USER",csrf_token="profile-token")
    image=Image.new("RGB",(8,8),(20,80,180)); buffer=BytesIO();image.save(buffer,format="PNG");buffer.seek(0)
    response=client.post("/profile",data={"csrf_token":"profile-token","name":"Traveler","email":"profile@example.com","preferred_transport":"Train","default_budget":"5000","currency":"INR","theme":"dark","profile_image":(buffer,"avatar.png")},content_type="multipart/form-data")
    assert response.status_code==302
    with sqlite3.connect(db_path) as conn:
        theme,filename=conn.execute("SELECT theme,profile_image FROM users WHERE id=1").fetchone()
    assert theme=="dark" and filename.endswith(".png")
    assert (tmp_path/"static"/"uploads"/"profiles"/filename).is_file()
    with client.session_transaction() as sess: assert sess["theme"]=="dark"


def test_excel_report_export(tmp_path, monkeypatch):
    db_path=tmp_path/"excel.db"
    monkeypatch.setattr(application,"DB_PATH",db_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:conn.execute("INSERT INTO users(name,email,password) VALUES('Traveler','excel@example.com','hash')")
    client=application.app.test_client()
    with client.session_transaction() as sess:sess.update(user_id=1,user="Traveler",role="USER",csrf_token="excel-token")
    response=client.get("/reports/export.xlsx")
    assert response.status_code==200 and response.data[:2]==b"PK"
    assert "spreadsheetml" in response.mimetype

def test_admin_user_delete_cleans_owned_records_and_cannot_delete_self(tmp_path, monkeypatch):
    db_path=tmp_path/"delete.db"
    monkeypatch.setattr(application,"DB_PATH",db_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO users(name,email,password,role) VALUES('Admin','admin@example.com','hash','ADMIN')")
        conn.execute("INSERT INTO users(name,email,password) VALUES('Traveler','user@example.com','hash')")
        conn.execute("INSERT INTO travel_history(user_id,source,destination,travelers,days,transportation,predicted_expense,budget) VALUES(2,'A','B',1,1,'Bus',500,600)")
        conn.execute("INSERT INTO expenses(trip_id,user_id,category,amount,expense_date) VALUES(1,2,'Food',50,'2026-10-09')")
    client=application.app.test_client()
    with client.session_transaction() as sess:sess.update(user_id=1,user='Admin',role='ADMIN',csrf_token='delete-token')
    assert client.post('/admin/users/1/delete',data={'csrf_token':'delete-token'}).status_code==400
    assert client.post('/admin/users/2/delete',data={'csrf_token':'delete-token'}).status_code==302
    with sqlite3.connect(db_path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM users WHERE id=2').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM travel_history').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]==0


def test_daily_forecast_reports_insufficient_data(tmp_path, monkeypatch):
    db_path=tmp_path/"daily.db"
    monkeypatch.setattr(application,"DB_PATH",db_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO users(name,email,password) VALUES('Traveler','daily@example.com','hash')")
        conn.execute("INSERT INTO travel_history(user_id,source,destination,travelers,days,transportation,predicted_expense,budget) VALUES(1,'A','B',1,2,'Bus',500,600)")
    client=application.app.test_client()
    with client.session_transaction() as sess:sess.update(user_id=1,user='Traveler',role='USER',csrf_token='daily-token')
    response=client.get('/trips/1/daily-forecast')
    assert response.status_code==200
    assert 'not enough dated expense history' in response.get_data(as_text=True)

def test_currency_conversion_uses_cached_reference_rate(tmp_path, monkeypatch):
    db_path=tmp_path/"rates.db"
    monkeypatch.setattr(application,"DB_PATH",db_path)
    application.create_database()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO exchange_rates(base,quote,rate,rate_date) VALUES('INR','USD',0.012,'2026-10-08')")
    rate,rate_date=application.get_exchange_rate("INR","USD")
    assert rate==0.012 and rate_date=="2026-10-08"
