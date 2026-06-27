from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import db, Party, Member, Message

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    parties = Party.query.all()
    return render_template('home.html', parties=parties)

@app.route('/party/create', methods=['POST'])
def create_party():
    restaurant = request.form['restaurant']
    creator = request.form['creator']
    time = request.form['time']
    party = Party(restaurant=restaurant, creator=creator, time=time)
    db.session.add(party)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/party/<int:party_id>')
def party(party_id):
    party = Party.query.get_or_404(party_id)
    return render_template('party.html', party=party)

@app.route('/party/<int:party_id>/join', methods=['POST'])
def join_party(party_id):
    name = request.form['name']
    member = Member(name=name, party_id=party_id)
    db.session.add(member)
    db.session.commit()
    return redirect(url_for('party', party_id=party_id))

@app.route('/party/<int:party_id>/message', methods=['POST'])
def send_message(party_id):
    content = request.form['content']
    sender = request.form['sender']
    message = Message(content=content, sender=sender, party_id=party_id)
    db.session.add(message)
    db.session.commit()
    return redirect(url_for('party', party_id=party_id))

if __name__ == '__main__':
    app.run(debug=True)