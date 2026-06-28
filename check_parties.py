from app import app, db
import party
from models import Party, Member

with app.app_context():
    parties = Party.query.all()
    for p in parties:
        print(f"Party {p.id}: {p.r_name}, p_size={p.p_size}, members={len(p.members)}")
