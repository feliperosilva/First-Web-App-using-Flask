# Versões
# Python 3.12.2
# Flask 3.0.3
# Werkzeug 3.0.4

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, login_user, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash # modulo para gerar hash passwords
from datetime import datetime, timedelta

app = Flask(__name__) # servidor de Flask
app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../database/management.db'
db = SQLAlchemy(app) # cursor para a base de dados

# Configurar um Login Manager
login_manager = LoginManager()
login_manager.init_app(app)

# Se usuário não tiver a sessão iniciada, redirecionada para página de login
login_manager.login_view = 'login'
login_manager.login_message = 'Login necessário.'
login_manager.login_message_category = "error"

@login_manager.user_loader
def load_user(id):
    return Registo.query.get(int(id))

# lugar ideal para criar a classe que gera a tabela na base de dados
# após criação do cursor e antes da criação das rotas

# classe que armazena os registos de novos usuários
class Registo(UserMixin, db.Model): # herda funções e métodos de UserMixin. Necessário para páginas que requerem login.
    __tablename__ = 'users' # criação da tabela users na base de dados

    id = db.Column(db.Integer, primary_key=True) # id único para cada entry

    # criação dos campos na base de dados
    first_name = db.Column(db.String(30), nullable=False) # nullable=False: não pode ter valores null(vazio)
    last_name = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False) # unique=True: dois users não podem ter emails iguais
    password_hash = db.Column(db.String(100), nullable=False)
    created = db.Column(db.DateTime, default=db.func.current_timestamp()) # default: mostrará data e hora(timestamp) de quando o registo foi criado - ajudará saber quais períodos a empresa tem mais criação de novos usuários

    def hash_pass(self, password):
        self.password_hash = generate_password_hash(password) # transforma o texto da pass numa versão hashed

    def check_pass(self, password):
        return check_password_hash(self.password_hash, password) # compara se o texto inserido é igual ao texto convertido em hash

    def full_name(self):
        return f'{self.first_name} {self.last_name}' # Retorna o nome do usuário


# classe que armazena os registos de novos carros que estarão disponíveis para aluguer
class Veiculos(db.Model):
    __tablename__ = 'veiculos' # criação da tabela veiculos na base de dados

    id = db.Column(db.Integer, primary_key=True)  # id único para cada entry

    # criação dos campos na base de dados
    marca_modelo = db.Column(db.String(30), nullable=False)
    tipo_veiculo = db.Column(db.String(30), nullable=False)
    categoria = db.Column(db.String(30), nullable=False)
    transmissao = db.Column(db.String(30), nullable=False)
    abastecimento = db.Column(db.String(30), nullable=False)
    num_lugares = db.Column(db.Integer, nullable=False)
    valor_diaria = db.Column(db.Float, nullable=False)
    ultima_revisao = db.Column(db.Date, nullable=False)
    proxima_revisao = db.Column(db.Date, nullable=False)
    ultima_inspecao = db.Column(db.Date, nullable=False)
    imagem = db.Column(db.String, nullable=False)
    disponivel = db.Column(db.Boolean, nullable=False)

class Reservas(db.Model):
    __tablename__ = 'reservas' # criação da tabela reservas na base de dados

    id = db.Column(db.Integer, primary_key=True)

    vehicle_id = db.Column(db.Integer, db.ForeignKey('veiculos.id'), unique=True, nullable=False,)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String, nullable=False)
    card_number = db.Column(db.String)
    expire_date = db.Column(db.String(10))
    cvv = db.Column(db.Integer)
    total = db.Column(db.Float, nullable=False)


with app.app_context(): # criar as tabelas
    db.create_all()

@app.route('/') # página inicial
def home():
    return render_template('index.html')

@app.route('/veiculos', methods=['GET', 'POST']) # página veículos
def veiculos():

    # se estiver logado com a conta de admin, pede para fazer logout antes de continuar
    if current_user.is_authenticated and current_user.email == 'admin@luxurywheels.pt':
        flash('Faça logout da conta de admin antes de continuar.', 'error')
        return redirect(url_for('novo_veiculo'))  # Redirect to the admin page

    vehicles = Veiculos.query.all()

    today = datetime.today().date()

    # loop que mostra todos os carros disponíveis
    for vehicle in vehicles:
        # confere se a última inspeção foi há mais de um ano
        # ou se a próxima revisão já está vencida
        # caso se confirme, carro fica indisponível
        if vehicle.ultima_inspecao < (today - timedelta(days=365)) or vehicle.proxima_revisao < today:
            vehicle.disponivel = False
        else:
            # se o carro estiver agendado, fica indisponível
            booked = Reservas.query.filter_by(vehicle_id=vehicle.id).first()
            if booked:
                vehicle.disponivel = False
            else:
                # caso nenhum caso se confirme, carro fica disponível
                vehicle.disponivel = True

    # faz commit na base de dados
    db.session.commit()

    query = Veiculos.query.filter_by(disponivel=True)

    # filtros para que se mostre os veículos disn+pníveis na página de Veículos
    if request.method == 'POST':
        tipo_veiculo = request.form.get('tipo_veiculo')  # Carro ou Moto
        categoria = request.form.get('categoria')  # Mini, Pequeno, Médio, Grande, Luxo
        transmissao = request.form.get('transmissao')  # Manual ou Automático
        valor_diaria = request.form.get('valor_diaria')  # até 50€, até 100€, até 150€, até 200€
        num_lugares = request.form.get('num_lugares')  # 1-4, 5-6, 7+

        # Apply filters based on user input
        if tipo_veiculo and tipo_veiculo != 'Selecionar':
            query = query.filter_by(tipo_veiculo=tipo_veiculo)

        if categoria and categoria != 'Selecionar':
            query = query.filter_by(categoria=categoria)

        if transmissao and transmissao != 'Selecionar':
            query = query.filter_by(transmissao=transmissao)

        if valor_diaria and valor_diaria != 'Selecionar':
            # Translate the filter values into numeric ranges
            if valor_diaria == 'até 50€':
                query = query.filter(Veiculos.valor_diaria <= 50.0)
            elif valor_diaria == 'até 100€':
                query = query.filter(Veiculos.valor_diaria <= 100.0)
            elif valor_diaria == 'até 150€':
                query = query.filter(Veiculos.valor_diaria <= 150.0)
            elif valor_diaria == 'até 200€':
                query = query.filter(Veiculos.valor_diaria <= 200.0)

        if num_lugares and num_lugares != 'Selecionar':
            # Translate number of seats options into numeric ranges
            if num_lugares == '1-4':
                query = query.filter(Veiculos.num_lugares.between(1, 4))
            elif num_lugares == '5-6':
                query = query.filter(Veiculos.num_lugares.between(5, 6))
            elif num_lugares == '7+':
                query = query.filter(Veiculos.num_lugares >= 7)

    # Faz o query e mostra os veículos filtrados
    available_vehicles = query.all()

    if not available_vehicles:
        flash('Não há veículos disponíveis com o(s) filtro(s) escolhido(s).', 'error')

    return render_template('veiculos.html', vehicles=available_vehicles)

@app.route('/login') # página login
def login():
    # se estiver logado com a conta de admin, pede para fazer logout antes de continuar
    if current_user.is_authenticated and current_user.email == 'admin@luxurywheels.pt':
        flash('Faça logout da conta de admin antes de continuar.', 'error')
        return redirect(url_for('novo_veiculo'))  # Redirect to the admin page

    return render_template('login.html')

@app.route('/login', methods=['POST']) # formulário login que receber email/password de um usuário e confere na base de dados
def user_login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = Registo.query.filter_by(email=email).first()

    # Se os campos não estiverem preenchidos
    if not email or not password:
        flash('Por favor, preencher todos os campos.', 'error')
        return render_template('login.html')

    # Se as credenciais estiverem corretas
    if user and user.check_pass(password):
        login_user(user) # faz login do usuário

        # criar um usuário admin para gerenciar a página que adiciona novos carros à base de dados.
        # login admin - email: admin@luxurywheels.pt, password: 1234567890 (isto na minha base de dados)
        if email == 'admin@luxurywheels.pt':
            return redirect(url_for('novo_veiculo'))
        return redirect(url_for('veiculos'))

    # erro de login
    else:
        flash('Email/password inválido. Tente novamente.', 'error')
        return render_template('login.html')

@app.route('/registo') # página registo
def registo():
    # se estiver logado com a conta de admin, pede para fazer logout antes de continuar
    if current_user.is_authenticated and current_user.email == 'admin@luxurywheels.pt':
        flash('Faça logout da conta de admin antes de continuar.', 'error')
        return redirect(url_for('novo_veiculo'))  # Redirect to the admin page

    return render_template('registo.html')

# rota que transfere os dados inseridos no form da página registo para a base de dados
@app.route('/registo', methods=['POST'])
def registar():
    # criação de novo usuário
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    password = request.form.get('password')

    user = Registo.query.filter_by(email=email).first()

    # se faltar informação
    if not first_name or not last_name or not email or not password:
        flash('Por favor, preencher todos os campos.', 'error')
        return render_template('registo.html')

    # se já tiver o email registado
    if user:
        flash('Email já registado. Escolha outro email ou faça login.', 'error')
        return render_template('registo.html')

    else:
        new_user = Registo(first_name=first_name,last_name=last_name,email=email)
        new_user.hash_pass(password)

        db.session.add(new_user)
        db.session.commit()
        flash('Registo efetuado com sucesso.', 'success')
        return redirect(url_for('login')) # após registo, redirecionar para a página de login

@app.route('/contactos') # página contactos
def contactos():
    # se estiver logado com a conta de admin, pede para fazer logout antes de continuar
    if current_user.is_authenticated and current_user.email == 'admin@luxurywheels.pt':
        flash('Faça logout da conta de admin antes de continuar.', 'error')
        return redirect(url_for('novo_veiculo'))  # Redirect to the admin page

    return render_template('contactos.html')

@app.route('/logout')
@login_required
def logout():
    # logout com sucesso
    flash('Sessão terminada com sucesso.', 'success')
    logout_user()
    return redirect(url_for('login'))

@app.route('/novo_veiculo', methods=['GET','POST'])
def novo_veiculo():
    # inserção de novo veiculo na base de dados (necessita fazer login com a conta de admin)
    if request.method == 'POST':
        marca_modelo = request.form.get('marca_modelo')
        tipo_veiculo = request.form.get('tipo_veiculo')
        categoria = request.form.get('categoria')
        transmissao = request.form.get('transmissao')
        abastecimento = request.form.get('abastecimento')
        num_lugares = int(request.form.get('num_lugares')) # converter str para int
        valor_diaria = float(request.form.get('valor_diaria')) # converter str para float
        ultima_revisao = datetime.strptime(request.form.get('ultima_revisao'), '%d/%m/%Y').date()
        proxima_revisao = datetime.strptime(request.form.get('proxima_revisao'), '%d/%m/%Y').date()
        ultima_inspecao = datetime.strptime(request.form.get('ultima_inspecao'), '%d/%m/%Y').date()
        imagem = request.form.get('imagem')
        disponivel = True

        novo_veiculo = Veiculos(
            marca_modelo=marca_modelo,
            tipo_veiculo=tipo_veiculo,
            categoria=categoria,
            transmissao=transmissao,
            abastecimento=abastecimento,
            num_lugares=num_lugares,
            valor_diaria=valor_diaria,
            ultima_revisao=ultima_revisao,
            proxima_revisao=proxima_revisao,
            ultima_inspecao=ultima_inspecao,
            imagem=imagem,
            disponivel=disponivel
        )

        db.session.add(novo_veiculo)
        db.session.commit()

        flash(f'Veículo {novo_veiculo.marca_modelo} adicionado com sucesso.', 'success')

        return redirect(url_for('novo_veiculo'))

    return render_template('novo_veiculo.html')


# rota que busca o id do veículo escolhido
@app.route('/reservar_veiculo/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def reservar_veiculo(vehicle_id):
    # se estiver logado com a conta de admin, pede para fazer logout antes de continuar
    if current_user.is_authenticated and current_user.email == 'admin@luxurywheels.pt':
        flash('Faça logout da conta de admin antes de continuar.', 'error')
        return redirect(url_for('novo_veiculo'))  # Redirect to the admin page

    # Busca o veículo na base de dados pelo ID
    vehicle = Veiculos.query.get(vehicle_id)

    if request.method == 'POST':
        # escolhe as datas
        if request.form.get('action') == 'confirm_dates':
            start_date = datetime.strptime(request.form.get('start_date'), '%d/%m/%Y').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%d/%m/%Y').date()

            today = datetime.today().date() # variável para o dia de hoje

            if start_date < today:
                flash('A data de levantamento não pode ser numa data passada.', 'date_error')
                return render_template('reservar_veiculo.html', vehicle_id=vehicle_id, vehicle=vehicle)

            if end_date < start_date:
                flash('A data de devolução não pode ser anterior à data de levantamento.', 'date_error')
                return render_template('reservar_veiculo.html', vehicle_id=vehicle_id, vehicle=vehicle)

            # Calcular o total a pagar baseado no número de dias e no valor diário do veículo
            days_booked = (end_date - start_date).days + 1
            total = round(days_booked * vehicle.valor_diaria, 2)
            return render_template('reservar_veiculo.html', vehicle_id=vehicle_id, vehicle=vehicle, total=total, start_date=start_date, end_date=end_date)

        # escolhe forma de pagamento
        elif request.form.get('action') == 'confirm_payment':
            start_date = datetime.strptime(request.form.get('start_date'), '%d/%m/%Y').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%d/%m/%Y').date()
            total = (request.form.get('total'))
            payment_method = request.form.get('payment_method')

            if not payment_method:
                flash('Por favor, escolha um método de pagamento.', 'card_error')
                return render_template('reservar_veiculo.html', vehicle_id=vehicle_id, vehicle=vehicle, total=total, start_date=start_date, end_date=end_date)

            if payment_method == 'Cartão':
                card_number = request.form.get('card_number')
                expire_date_str = request.form.get('expire_date') # formato str
                cvv = request.form.get('cvv')

                if not card_number or not expire_date_str or not cvv:
                    flash('Necessário todas as informações do cartão.', 'card_error')
                    return render_template('reservar_veiculo.html', vehicle_id=vehicle_id, vehicle=vehicle, start_date=start_date, end_date=end_date, payment_method=payment_method)

                if expire_date_str:
                    expire_date = datetime.strptime(expire_date_str, '%m/%Y') # formato data
                    expire_month = expire_date.month
                    expire_year = expire_date.year

                    today = datetime.today()
                    current_month = today.month
                    current_year = today.year

                    if (expire_year < current_year) or (expire_year == current_year and expire_month < current_month):
                        flash('Cartão expirado. Utilize outro cartão ou outro método de pagamento.', 'card_error')
                        return render_template('reservar_veiculo.html', vehicle_id=vehicle_id, vehicle=vehicle, total=total, start_date=start_date, end_date=end_date, payment_method=payment_method, card_number=card_number, expire_date_str=expire_date_str, cvv=cvv)

                last_four_digits = card_number[-4:]
                masked_number = f'xxxx-xxxx-xxxx-{last_four_digits}' #forma mais segura para guardar número de cartão de crédito/débito
            else:
                masked_number = None
                expire_date_str = None
                cvv = None

            # cria nova reserva
            nova_reserva = Reservas (
                vehicle_id=vehicle_id,
                user_id=current_user.id, # usuário que está logado no momento
                start_date=start_date,
                end_date=end_date,
                payment_method=payment_method,
                card_number=masked_number, # guarda versão segura na base de dados
                expire_date=expire_date_str,
                cvv=cvv,
                total=total
            )
            db.session.add(nova_reserva)
            db.session.commit()

            return redirect(url_for('minhas_reservas', user_id=current_user.id))

    # Passa o carro escolhido para o próximo template
    return render_template('reservar_veiculo.html', vehicle_id=vehicle_id, vehicle=vehicle)



@app.route('/minhas_reservas/<int:user_id>', methods=['GET','POST'])
@login_required
def minhas_reservas(user_id, action=None, reserva=None):
    # se estiver logado com a conta de admin, pede para fazer logout antes de continuar
    if current_user.is_authenticated and current_user.email == 'admin@luxurywheels.pt':
        flash('Faça logout da conta de admin antes de continuar.', 'error')
        return redirect(url_for('novo_veiculo'))

    bookings = Reservas.query.filter_by(user_id=user_id).all()

    # lista de carros reservados
    vehicles = []
    bookings_info = []

    # busca carros pelo seu id e append na lista
    for booking in bookings:
        vehicle = Veiculos.query.get(booking.vehicle_id)
        vehicles.append(vehicle)
        num_days = (booking.end_date - booking.start_date).days + 1
        bookings_info.append({
            'vehicle': vehicle,
            'num_days': num_days,
            'booking': booking
        })

    if request.method == 'POST':
        reserva_id = request.form.get('reserva_id')
        reserva = Reservas.query.get(reserva_id)
        action = request.form.get('action')
        today = datetime.today().date()

        # atualiza datas na reserva
        if action == 'update_dates':
            if reserva:
                if 'start_date' in request.form and 'end_date' in request.form:
                    new_start_date = datetime.strptime(request.form.get('start_date'), '%d/%m/%Y').date()
                    new_end_date = datetime.strptime(request.form.get('end_date'), '%d/%m/%Y').date()

                if new_start_date < today:
                    flash('A data de levantamento não pode ser numa data passada.', 'update-error')
                    return render_template('minhas_reservas.html', bookings=bookings_info, start_date=new_start_date, end_date=new_end_date)

                elif new_end_date < new_start_date:
                    flash('A data de devolução não pode ser anterior à data de levantamento.', 'update-error')
                    return render_template('minhas_reservas.html', bookings=bookings_info, start_date=new_start_date, end_date=new_end_date)

                reserva.start_date = new_start_date
                reserva.end_date = new_end_date

                db.session.commit()

            return redirect(url_for('atualizar_reserva', id=reserva.id))

        # cancela reserva
        elif action == 'cancel':
            db.session.delete(reserva)
            db.session.commit()

            flash('Sua reserva foi cancelada com sucesso', 'cancel-success')

            return redirect(url_for('minhas_reservas', user_id=current_user.id))

    return render_template('minhas_reservas.html', user_id=current_user.id, bookings=bookings_info)

@app.route('/atualizar_reserva/<int:id>', methods=['GET','POST'])
@login_required
def atualizar_reserva(id):
    # se estiver logado com a conta de admin, pede para fazer logout antes de continuar
    if current_user.is_authenticated and current_user.email == 'admin@luxurywheels.pt':
        flash('Faça logout da conta de admin antes de continuar.', 'error')
        return redirect(url_for('novo_veiculo'))  # Redirect to the admin page

    reserva = Reservas.query.get(id)

    # caso as datas tenham sido atualizadas
    new_start_date = reserva.start_date
    new_end_date = reserva.end_date

    # calcula novo total e a diferença entre os totais antigos e novos
    vehicle = Veiculos.query.get(reserva.vehicle_id)
    num_days = (new_end_date - new_start_date).days + 1
    update_total = round(vehicle.valor_diaria * num_days, 2)

    difference = abs(round(update_total - reserva.total, 2))

    if request.method == 'POST':
        if not update_total > reserva.total: # se não tiver nenhum valor a pagar
            return redirect(url_for('minhas_reservas', user_id=current_user.id))

        elif update_total > reserva.total: # caso tenha algo a pagar
            payment_method = request.form.get('payment_method')

            if not payment_method:
                flash('Por favor, escolha um método de pagamento.', 'card_error')
                return render_template('atualizar_reserva.html', reserva=reserva, vehicle=vehicle, num_days=num_days, update_total=update_total, difference=difference)

            if payment_method == 'Cartão':
                card_number = request.form.get('card_number')
                expire_date_str = request.form.get('expire_date')  # formato str
                cvv = request.form.get('cvv')

                if not card_number or not expire_date_str or not cvv:
                    flash('Necessário todas as informações do cartão.', 'card_error')
                    return render_template('atualizar_reserva.html', reserva=reserva, vehicle=vehicle, num_days=num_days, update_total=update_total, difference=difference, payment_method=payment_method, card_number=card_number, expire_date_str=expire_date_str, cvv=cvv)

                if expire_date_str:
                    expire_date = datetime.strptime(expire_date_str, '%m/%Y')  # formato data
                    expire_month = expire_date.month
                    expire_year = expire_date.year

                    today = datetime.today()
                    current_month = today.month
                    current_year = today.year

                    if (expire_year < current_year) or (expire_year == current_year and expire_month < current_month):
                        flash('Cartão expirado. Utilize outro cartão ou outro método de pagamento.', 'card_error')
                        return render_template('atualizar_reserva.html', reserva=reserva, vehicle=vehicle, num_days=num_days, update_total=update_total, difference=difference, payment_method=payment_method, card_number=card_number, expire_date_str=expire_date_str, cvv=cvv)

                last_four_digits = card_number[-4:]
                masked_number = f'xxxx-xxxx-xxxx-{last_four_digits}'

            else:
                masked_number = None
                expire_date_str = None
                cvv = None

            reserva.total = update_total
            reserva.payment_method = payment_method
            reserva.card_number = masked_number
            reserva.expire_date = expire_date_str
            reserva.cvv = cvv
            db.session.commit()

            return redirect(url_for('minhas_reservas', user_id=current_user.id))

    return render_template('atualizar_reserva.html', reserva=reserva, vehicle=vehicle, num_days=num_days, update_total=update_total, difference=difference)


if __name__ == '__main__':
    app.run(debug=True) # quando reinicia-se o servidor ou modifica o código, o servidor Flask reinicia-se sozinho

