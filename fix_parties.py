from app import app, db
from models import Party

with app.app_context():
    parties = Party.query.all()
    for p in parties:
        if p.p_size == 1:
            p.p_size = 6
    db.session.commit()
    print("Fixed party sizes!")
