from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required
from models import db, Usuario, Cita
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey123'

database_url = os.environ.get("DATABASE_URL")

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        password = request.form['password']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        rol = 'admin' if correo == 'admin@clinica.com' else 'paciente'

        nuevo_usuario = Usuario(
            nombre=nombre,
            correo=correo,
            password=hashed_password,
            rol=rol
        )

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Usuario registrado correctamente')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']

        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario and bcrypt.check_password_hash(usuario.password, password):
            login_user(usuario)
            return redirect(url_for('dashboard'))

        flash('Credenciales incorrectas')

    return render_template('login.html')


@app.route('/admin')
@login_required
def admin():
    from flask_login import current_user

    if current_user.rol != 'admin':
        flash('Acceso denegado')
        return redirect(url_for('dashboard'))

    todas_citas = Cita.query.all()
    return render_template('admin.html', citas=todas_citas)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/citas', methods=['GET', 'POST'])
@login_required
def citas():
    from flask_login import current_user

    if request.method == 'POST':
        fecha = request.form['fecha']
        hora = request.form['hora']
        medico = request.form['medico']

        cita_existente = Cita.query.filter_by(
            fecha=fecha,
            hora=hora,
            medico=medico
        ).first()

        if cita_existente:
            flash('Ese horario ya está ocupado')
        else:
            nueva_cita = Cita(
                fecha=fecha,
                hora=hora,
                medico=medico,
                usuario_id=current_user.id
            )

            db.session.add(nueva_cita)
            db.session.commit()
            flash('Cita agendada correctamente')

    citas_usuario = Cita.query.filter_by(
        usuario_id=current_user.id
    ).all()

    return render_template(
        'citas.html',
        citas=citas_usuario
    )

@app.route('/cancelar_cita/<int:id>')
@login_required
def cancelar_cita(id):
    cita = Cita.query.get_or_404(id)

    db.session.delete(cita)
    db.session.commit()

    flash('Cita cancelada')
    return redirect(url_for('citas'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/eliminar_admin/<int:id>')
@login_required
def eliminar_admin(id):
    from flask_login import current_user

    if current_user.rol != 'admin':
        flash('Acceso denegado')
        return redirect(url_for('dashboard'))

    cita = Cita.query.get_or_404(id)
    db.session.delete(cita)
    db.session.commit()

    flash('Cita eliminada correctamente')
    return redirect(url_for('admin'))

@app.route('/editar_cita/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cita(id):
    from flask_login import current_user

    if current_user.rol != 'admin':
        flash('Acceso denegado')
        return redirect(url_for('dashboard'))

    cita = Cita.query.get_or_404(id)

    if request.method == 'POST':
        cita.fecha = request.form['fecha']
        cita.hora = request.form['hora']
        cita.medico = request.form['medico']

        db.session.commit()
        flash('Cita actualizada')
        return redirect(url_for('admin'))

    return render_template('editar_cita.html', cita=cita)

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    from flask_login import current_user

    if request.method == 'POST':
        current_user.nombre = request.form['nombre']
        current_user.correo = request.form['correo']

        nueva_password = request.form['password']

        if nueva_password:
            hashed_password = bcrypt.generate_password_hash(
                nueva_password
            ).decode('utf-8')
            current_user.password = hashed_password

        db.session.commit()
        flash('Perfil actualizado correctamente')
        return redirect(url_for('perfil'))

    return render_template('perfil.html')



if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)