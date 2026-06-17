from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'  # Смените на реальный секретный ключ

# Настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Флаг администратора

    def __repr__(self):
        return f'<User {self.email}>'

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('index'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('У вас нет доступа к этой странице', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Создание базы данных и администратора по умолчанию
with app.app_context():
    db.create_all()
    
    # Создание администратора по умолчанию, если его нет
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            name='Администратор',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Администратор создан: admin@example.com / admin123")

@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return render_template('index.html', user=user)

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Проверка на существующего пользователя
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Пользователь с таким email уже существует', 'error')
        return redirect(url_for('index'))
    
    # Создание нового пользователя
    hashed_password = generate_password_hash(password)
    new_user = User(name=name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    flash('Регистрация успешна! Теперь вы можете войти', 'success')
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['is_admin'] = user.is_admin
        flash(f'Добро пожаловать, {user.name}!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Неверный email или пароль', 'error')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))

# Админ-панель
@app.route('/admin')
@admin_required
def admin_panel():
    users = User.query.all()
    return render_template('admin.html', users=users, user=User.query.get(session['user_id']))

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    # Нельзя удалить самого себя
    if user_id == session['user_id']:
        flash('Вы не можете удалить самого себя', 'error')
        return redirect(url_for('admin_panel'))
    
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'Пользователь {user_to_delete.name} удален', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/make_admin/<int:user_id>')
@admin_required
def make_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash(f'Пользователь {user.name} теперь администратор', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove_admin/<int:user_id>')
@admin_required
def remove_admin(user_id):
    # Нельзя лишить прав самого себя
    if user_id == session['user_id']:
        flash('Вы не можете лишить прав администратора самого себя', 'error')
        return redirect(url_for('admin_panel'))
    
    user = User.query.get_or_404(user_id)
    user.is_admin = False
    db.session.commit()
    flash(f'Пользователь {user.name} больше не администратор', 'success')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)