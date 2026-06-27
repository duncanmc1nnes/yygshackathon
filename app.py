from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from models import db, Party, Member, Message, User
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'super_secret_key_for_yygs_hackathon'
db.init_app(app)

with app.app_context():
    db.create_all()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def home():
    parties = Party.query.order_by(Party.created_at.desc()).all()
    return render_template('home.html', username=session['username'], parties=parties)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or Email already exists.', 'error')
        else:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username_or_email']
        password = request.form['password']

        user = User.query.filter(
            ((User.username == username_or_email) | (User.email == username_or_email)) &
            (User.password == password)
        ).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/party/create', methods=['GET', 'POST'])
@login_required
def create_party():
    if request.method == 'POST':
        new_party = Party(
            r_name=request.form['r_name'],
            c=request.form['c'],
            p_size=request.form['p_size'],
            p_host=session['username'],
            p_date=request.form['p_date']
        )
        db.session.add(new_party)
        db.session.commit()
        flash('Party created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_party.html')

@app.route('/party/<int:party_id>')
@login_required
def view_party(party_id):
    party = Party.query.get_or_404(party_id)
    return render_template('party.html', party=party)

@app.route('/party/<int:party_id>/join', methods=['POST'])
@login_required
def join_party(party_id):
    party = Party.query.get_or_404(party_id)

    already_member = Member.query.filter_by(name=session['username'], party_id=party_id).first()
    if already_member:
        flash('You are already in this party!', 'error')
        return redirect(url_for('view_party', party_id=party_id))

    if len(party.members) >= party.p_size:
        flash('This party is full!', 'error')
        return redirect(url_for('view_party', party_id=party_id))

    member = Member(name=session['username'], party_id=party_id)
    db.session.add(member)
    db.session.commit()
    flash('You joined the party!', 'success')
    return redirect(url_for('view_party', party_id=party_id))

@app.route('/party/<int:party_id>/message', methods=['POST'])
@login_required
def send_message(party_id):
    content = request.form['content']
    if content.strip():
        message = Message(content=content, sender=session['username'], party_id=party_id)
        db.session.add(message)
        db.session.commit()
    return redirect(url_for('view_party', party_id=party_id))

@app.route('/party/<int:party_id>/leave', methods=['POST'])
@login_required
def leave_party(party_id):
    member = Member.query.filter_by(name=session['username'], party_id=party_id).first()
    if member:
        db.session.delete(member)
        db.session.commit()
        flash('You left the party.', 'info')
    return redirect(url_for('home'))

@app.route('/party_search')
@login_required
def party_search():
    query = request.args.get('q', '')
    cuisine = request.args.get('cuisine', '')
    date = request.args.get('date', '')

    parties = Party.query

    if query:
        parties = parties.filter(Party.r_name.ilike(f'%{query}%'))
    if cuisine:
        parties = parties.filter(Party.c.ilike(f'%{cuisine}%'))
    if date:
        parties = parties.filter(Party.p_date == date)

    parties = parties.order_by(Party.created_at.desc()).all()

    return render_template('party_search.html', parties=parties, query=query, cuisine=cuisine, date=date)

if __name__ == '__main__':
    app.run(debug=True)
