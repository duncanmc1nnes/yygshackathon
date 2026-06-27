from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import db, Party, Member, Message
import party

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/party/create', methods=['POST'])
def create_party():
    party = Party(
        r_name=request.form['r_name'],
        c=request.form['c'],
        p_size=request.form['p_size'],
        p_host=request.form['p_host'],
        p_date=request.form['p_date']
    )
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