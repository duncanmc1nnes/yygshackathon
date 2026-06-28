from app import app, db
import party

with app.app_context():
    # Attempt to join party 1 with user id 4
    result = party.join_party(party_id=1, username='test123', user_id=4)
    print("Join party result:", result)
