from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from models import db, Party, Member, Message, User
import party

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'super_secret_key_for_yygs_hackathon'
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', username=session['username'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if username or email already exists
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