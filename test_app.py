import unittest
from datetime import date, time
from app import create_app
from models import db, Usuario, Parqueadero, Reserva
from services.email_service import generate_password_reset_token, verify_password_reset_token

class AutoParkTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def login(self, email, password):
        return self.client.post('/auth/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/auth/logout', follow_redirects=True)

    def test_01_database_records_exist(self):
        """Verifica que la base de datos PostgreSQL contiene los registros iniciales."""
        admin = Usuario.query.filter_by(rol='admin').first()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.email, 'admin@parqueaderos.com')

        parqueaderos = Parqueadero.query.all()
        self.assertGreaterEqual(len(parqueaderos), 3)

        reservas = Reserva.query.all()
        self.assertGreaterEqual(len(reservas), 1)
        print("[OK] Test 1: Conexion y registros existentes en PostgreSQL verificados con exito.")

    def test_02_authentication_and_roles(self):
        """Verifica inicio de sesion de los 3 roles y redirecciones correspondientes."""
        # 1. Login Estudiante
        res_est = self.login('estudiante1@universidad.edu.co', 'Estudiante123!')
        self.assertEqual(res_est.status_code, 200)
        self.assertIn(b'Parqueaderos Disponibles', res_est.data)
        self.logout()

        # 2. Login Operador
        res_op = self.login('operador1@parqueaderos.com', 'Operador123!')
        self.assertEqual(res_op.status_code, 200)
        self.assertIn(b'Panel de Administrador de Parqueaderos', res_op.data)
        self.logout()

        # 3. Login Admin
        res_adm = self.login('admin@parqueaderos.com', 'Admin123!')
        self.assertEqual(res_adm.status_code, 200)
        self.assertIn(b'Panel de Administraci', res_adm.data)
        self.logout()
        print("[OK] Test 2: Autenticacion y control de acceso por roles verificado con exito.")

    def test_03_password_reset_token(self):
        """Verifica la generacion y validacion de tokens de recuperacion de contrasena."""
        email = 'estudiante1@universidad.edu.co'
        token = generate_password_reset_token(email)
        self.assertIsNotNone(token)
        
        verified_email = verify_password_reset_token(token)
        self.assertEqual(verified_email, email)

        # Token invalido
        invalid_email = verify_password_reset_token("token_invalido_falso")
        self.assertIsNone(invalid_email)
        print("[OK] Test 3: Tokens criptograficos para restablecimiento de contrasena verificados con exito.")

    def test_04_datatables_serverside_endpoint(self):
        """Verifica el endpoint Server-Side de DataTables para Reservas."""
        self.login('admin@parqueaderos.com', 'Admin123!')
        
        response = self.client.get('/admin/api/reservas/serverside?draw=1&start=0&length=5&search[value]=&order[0][column]=0&order[0][dir]=desc')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        
        self.assertIn('draw', json_data)
        self.assertEqual(json_data['draw'], 1)
        self.assertIn('recordsTotal', json_data)
        self.assertIn('recordsFiltered', json_data)
        self.assertIn('data', json_data)
        self.assertIsInstance(json_data['data'], list)
        self.assertGreater(json_data['recordsTotal'], 0)
        self.logout()
        print(f"[OK] Test 4: DataTables ServerSide funciona con {json_data['recordsTotal']} registros en PostgreSQL.")

    def test_05_highcharts_stats_endpoint(self):
        """Verifica que el endpoint de estadisticas para Highcharts retorne la estructura esperada."""
        self.login('operador1@parqueaderos.com', 'Operador123!')
        response = self.client.get('/parking-admin/api/stats')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()

        self.assertIn('parqueaderos', json_data)
        self.assertIn('estados', json_data)
        self.assertIn('tendencia', json_data)
        self.assertIn('categorias', json_data['parqueaderos'])
        self.logout()
        print("[OK] Test 5: Endpoint de Highcharts suministra datos estructurados correctamente.")

    def test_06_student_map_api(self):
        """Verifica el endpoint de parqueaderos para el mapa Leaflet."""
        self.login('estudiante1@universidad.edu.co', 'Estudiante123!')
        response = self.client.get('/student/api/parqueaderos')
        self.assertEqual(response.status_code, 200)
        parqueaderos = response.get_json()
        self.assertIsInstance(parqueaderos, list)
        self.assertGreaterEqual(len(parqueaderos), 1)

        primer_p = parqueaderos[0]
        self.assertIn('nombre', primer_p)
        self.assertIn('latitud', primer_p)
        self.assertIn('longitud', primer_p)
        self.assertIn('espacios_disponibles', primer_p)
        self.assertIn('tipo_vehiculo', primer_p)
        self.logout()
        print("[OK] Test 6: API de Parqueaderos para Leaflet mapa verificada con exito.")

    def test_07_crear_reserva_estudiante(self):
        """Verifica la creacion y posterior cancelacion de una reserva por parte de un estudiante."""
        self.login('estudiante1@universidad.edu.co', 'Estudiante123!')
        
        p = Parqueadero.query.filter(Parqueadero.estado == 'disponible', Parqueadero.espacios_disponibles > 0).first()
        self.assertIsNotNone(p)

        hoy_str = date.today().strftime('%Y-%m-%d')
        res = self.client.post('/student/reservas/crear', data=dict(
            parqueadero_id=p.id,
            fecha=hoy_str,
            hora_inicio='15:00',
            hora_finalizacion='17:00',
            tipo_vehiculo='carro',
            placa_vehiculo='TST-999',
            notas='Prueba automatizada'
        ), follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Reserva confirmada con', res.data)

        # Verificar en base de datos
        reserva_creada = Reserva.query.filter_by(placa_vehiculo='TST-999', estado='activa').first()
        self.assertIsNotNone(reserva_creada)

        # Cancelar la reserva
        res_cancel = self.client.post(f'/student/reservas/{reserva_creada.id}/cancelar', follow_redirects=True)
        self.assertEqual(res_cancel.status_code, 200)
        self.assertIn(b'ha sido cancelada', res_cancel.data)

        reserva_actualizada = db.session.get(Reserva, reserva_creada.id)
        self.assertEqual(reserva_actualizada.estado, 'cancelada')
        self.logout()
        print("[OK] Test 7: Flujo de creacion y cancelacion de reservas por estudiante completado exitosamente.")

if __name__ == '__main__':
    unittest.main()
