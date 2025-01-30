from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from collections import Counter

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hackathon.db'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Add this line here
db = SQLAlchemy(app)

from flask import request, redirect, url_for
from werkzeug.utils import secure_filename
import os

# Configure upload folder for profile pictures
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('You need to log in to edit your profile!')
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(session['user_id'])
    
    if request.method == 'POST':
        # Update user details
        user.bio = request.form.get('bio')
        user.location = request.form.get('location')
        user.github = request.form.get('github')
        user.linkedin = request.form.get('linkedin')
        
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                user.profile_picture = f'/static/uploads/{filename}'
        
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('profile', user_id=user.id))
    
    return render_template('edit_profile.html', user=user)
# Define skill categories
SKILL_CATEGORIES = {
    "language": ["english", "hindi", "marathi", "spanish", "french"],
    "coding": ["python", "java", "c++", "c", "javascript"],
    "web3": ["blockchain", "remix developer", "smart contracts", "ethereum"],
    "data science": ["machine learning", "deep learning", "data analysis", "statistics"],
    "design": ["ui/ux design", "graphic design", "illustration"]
}

# Create all database tables
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    recommendations = []
    if 'user_id' in session:
        # Use the last searched category for recommendations
        last_searched_category = session.get('last_searched_category')
        if last_searched_category:
            category_skills = SKILL_CATEGORIES[last_searched_category]
            users = User.query.filter(
                db.or_(*[User.skills.like(f'%{skill}%') for skill in category_skills])
            ).limit(6).all()
            recommendations = users
        else:
            recommendations = get_recommendations(session['user_id'])
    return render_template('index.html', recommendations=recommendations)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        skills = request.form['skills'].lower()  # Convert skills to lowercase
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, skills=skills)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful!')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Store user_id in session
            flash('Logged in successfully!')
            return redirect(url_for('index'))
        
        flash('Invalid username or password!')
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('You need to log in to access the dashboard!')
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(session['user_id'])
    recommendations = get_recommendations(user.id)  # Fetch recommendations
    
    return render_template('dashboard.html', user=user, recommendations=recommendations)


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Clear the user's session
    flash('You have been logged out successfully!')
    return redirect(url_for('index'))


@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('profile.html', user=user)


#new added routes
@app.route('/send-friend-request/<int:receiver_id>', methods=['POST'])
def send_friend_request(receiver_id):
    if 'user_id' not in session:
        flash('You need to log in to send friend requests!')
        return redirect(url_for('login'))
    
    sender_id = session['user_id']
    if sender_id == receiver_id:
        flash('You cannot send a friend request to yourself!')
        return redirect(url_for('find_teammates'))
    
    # Check if a request already exists
    existing_request = FriendRequest.query.filter_by(
        sender_id=sender_id, receiver_id=receiver_id, status='pending'
    ).first()
    if existing_request:
        flash('Friend request already sent!')
        return redirect(url_for('find_teammates'))
    
    # Create a new friend request
    new_request = FriendRequest(sender_id=sender_id, receiver_id=receiver_id)
    db.session.add(new_request)
    db.session.commit()
    
    flash('Friend request sent successfully!')
    return redirect(url_for('find_teammates'))

@app.route('/accept-friend-request/<int:request_id>', methods=['POST'])
def accept_friend_request(request_id):
    if 'user_id' not in session:
        flash('You need to log in to manage friend requests!')
        return redirect(url_for('login'))
    
    friend_request = FriendRequest.query.get_or_404(request_id)
    if friend_request.receiver_id != session['user_id']:
        flash('You are not authorized to accept this request!')
        return redirect(url_for('index'))
    
    # Accept the request
    friend_request.status = 'accepted'
    db.session.commit()
    
    flash('Friend request accepted!')
    return redirect(url_for('index'))

@app.route('/reject-friend-request/<int:request_id>', methods=['POST'])
def reject_friend_request(request_id):
    if 'user_id' not in session:
        flash('You need to log in to manage friend requests!')
        return redirect(url_for('login'))
    
    friend_request = FriendRequest.query.get_or_404(request_id)
    if friend_request.receiver_id != session['user_id']:
        flash('You are not authorized to reject this request!')
        return redirect(url_for('index'))
    
    # Reject the request
    friend_request.status = 'rejected'
    db.session.commit()
    
    flash('Friend request rejected!')
    return redirect(url_for('index'))

@app.route('/friend-requests')
def friend_requests():
    if 'user_id' not in session:
        flash('You need to log in to view friend requests!')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    received_requests = FriendRequest.query.filter_by(
        receiver_id=user_id, status='pending'
    ).all()
    
    return render_template('friend_requests.html', requests=received_requests)

#created a new route /friends that fetches all accepted friend requests for the logged-in user.
@app.route('/friends')
def friends():
    if 'user_id' not in session:
        flash('You need to log in to view your friends!')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Fetch all accepted friend requests
    accepted_requests = FriendRequest.query.filter(
        db.or_(
            (FriendRequest.sender_id == user_id) & (FriendRequest.status == 'accepted'),
            (FriendRequest.receiver_id == user_id) & (FriendRequest.status == 'accepted')
        )
    ).all()
    
    # Extract friend objects
    friends = []
    for request in accepted_requests:
        friend = request.sender if request.sender_id != user_id else request.receiver
        friends.append(friend)
    
    return render_template('friends.html', friends=friends)


@app.route('/search', methods=['GET'])
def search():
    skill = request.args.get('skill', '').lower().strip()
    page = request.args.get('page', 1, type=int)  # Get the current page number
    per_page = 6  # Number of users per page

    if skill and 'user_id' in session:
        # Store search history
        search_history = SearchHistory(
            user_id=session['user_id'],
            search_term=skill
        )
        db.session.add(search_history)
        db.session.commit()

        # Determine the category of the searched skill
        skill_category = None
        for category, skills in SKILL_CATEGORIES.items():
            if skill in skills:
                skill_category = category
                break
        
        # Store the category in the session
        if skill_category:
            session['last_searched_category'] = skill_category

        # Paginate search results
        query = User.query.filter(User.skills.like(f'%{skill}%'))
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items
    else:
        query = User.query
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items

    return render_template('find_teammates.html', users=users, search_query=skill, pagination=pagination)
#now functions 

def get_recommendations(user_id):
    recent_searches = SearchHistory.query.filter_by(user_id=user_id)\
        .order_by(SearchHistory.timestamp.desc())\
        .limit(5)\
        .all()
    
    search_terms = [search.search_term for search in recent_searches]
    
    if not search_terms:
        return User.query.filter(User.id != user_id).limit(6).all()
    
    recommended_users = []
    for term in search_terms:
        term_category = None
        for category, skills in SKILL_CATEGORIES.items():
            if term.lower() in skills:
                term_category = category
                break
        
        if term_category:
            category_skills = SKILL_CATEGORIES[term_category]
            users = User.query.filter(
                User.id != user_id,
                db.or_(*[User.skills.like(f'%{skill}%') for skill in category_skills])
            ).all()
            
            for user in users:
                # Calculate a score based on matching skills
                user_skills = set(user.skills.lower().split(','))
                score = len(user_skills.intersection(search_terms))
                recommended_users.append((user, score))
    
    # Sort users by score (descending) and remove duplicates
    seen = set()
    sorted_users = sorted(recommended_users, key=lambda x: x[1], reverse=True)
    recommendations = [user for user, _ in sorted_users if user.id not in seen and not seen.add(user.id)]
    
    return recommendations[:6]

# Add this to your existing models
class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    search_term = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Modify User model to add relationship
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    skills = db.Column(db.String(300), nullable=False)
    search_history = db.relationship('SearchHistory', backref='user', lazy=True)
    bio = db.Column(db.String(500), nullable=True)  # New field
    location = db.Column(db.String(100), nullable=True)  # New field
    github = db.Column(db.String(200), nullable=True)  # New field
    linkedin = db.Column(db.String(200), nullable=True)  # New field
    profile_picture = db.Column(db.String(200), nullable=True)  # Profile picture URL


class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_requests')

    
# After your User model definition and before your routes, add:
def init_db():
    with app.app_context(): 
        db.create_all()

from flask import request
@app.route('/find-teammates')
def find_teammates():
    if 'user_id' not in session:
        flash('You need to log in to find teammates!')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get the last searched category from the session
    last_searched_category = session.get('last_searched_category')
    
    if last_searched_category:
        # Fetch users with skills in the same category
        category_skills = SKILL_CATEGORIES[last_searched_category]
        users = User.query.filter(
            db.or_(*[User.skills.like(f'%{skill}%') for skill in category_skills])
        ).filter(User.id != user_id).all()
    else:
        # Fallback: Show all users if no category is found
        users = User.query.filter(User.id != user_id).all()
    
    return render_template('find_teammates.html', users=users)

if __name__ == '__main__':
    init_db()  # Initialize database
    app.run(debug=True)