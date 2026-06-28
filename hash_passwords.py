from app import app, db, User, generate_sha256

with app.app_context():
    users = User.query.all()
    for u in users:
        if len(u.password) != 64: # SHA256 length is 64 hex characters
            print(f"Updating password for {u.username}")
            u.password = generate_sha256(u.password)
    db.session.commit()
    print("Database updated!")
