"""
Script de datos de prueba para navegacion de meses en GastuApp.
Crea movimientos en los ultimos 3 meses para el primer superusuario.

Uso:
    python manage.py shell < seed_meses_anteriores.py
    o bien:
    python manage.py shell -c "exec(open('seed_meses_anteriores.py').read())"
"""
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from categorias.models import Categoria
from movimientos.models import Movimiento

User = get_user_model()

# Usar el primer superusuario (cambia el username si necesitas otro)
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()

if not user:
    print("ERROR: no hay usuarios en la base de datos. Crea uno con createsuperuser.")
else:
    print(f"Creando datos para: {user.username}")

    cat_ing = Categoria.objects.filter(tipo='INGRESO', activo=True).first()
    cat_egr = Categoria.objects.filter(tipo='EGRESO',  activo=True).first()

    if not cat_ing or not cat_egr:
        print("ERROR: no hay categorias activas. Carga el fixture: python manage.py loaddata categorias_iniciales")
    else:
        hoy = date.today()

        # Datos por mes: (mes_offset, [(tipo, descripcion, monto, dia), ...])
        meses_data = [
            (-1, [
                ('INGRESO', 'Salario febrero',    Decimal('2800000'), 5),
                ('INGRESO', 'Freelance febrero',  Decimal('450000'),  12),
                ('EGRESO',  'Arriendo febrero',   Decimal('800000'),  3),
                ('EGRESO',  'Mercado febrero',     Decimal('320000'),  8),
                ('EGRESO',  'Transporte febrero',  Decimal('95000'),   10),
                ('EGRESO',  'Servicios febrero',   Decimal('180000'),  15),
                ('EGRESO',  'Entretenimiento feb', Decimal('120000'),  20),
            ]),
            (-2, [
                ('INGRESO', 'Salario enero',      Decimal('2800000'), 5),
                ('INGRESO', 'Bono enero',          Decimal('700000'),  10),
                ('EGRESO',  'Arriendo enero',      Decimal('800000'),  3),
                ('EGRESO',  'Mercado enero',        Decimal('290000'),  7),
                ('EGRESO',  'Transporte enero',     Decimal('88000'),   9),
                ('EGRESO',  'Servicios enero',      Decimal('165000'),  14),
                ('EGRESO',  'Ropa enero',           Decimal('250000'),  22),
                ('EGRESO',  'Salud enero',          Decimal('140000'),  25),
            ]),
            (-3, [
                ('INGRESO', 'Salario diciembre',  Decimal('2800000'), 5),
                ('EGRESO',  'Arriendo diciembre',  Decimal('800000'),  3),
                ('EGRESO',  'Mercado diciembre',    Decimal('350000'),  8),
                ('EGRESO',  'Regalos diciembre',    Decimal('480000'),  15),
                ('EGRESO',  'Transporte diciembre', Decimal('110000'),  10),
            ]),
        ]

        creados = 0
        for offset, registros in meses_data:
            # Calcular mes y año destino
            mes_target = hoy.month + offset
            anio_target = hoy.year
            while mes_target <= 0:
                mes_target += 12
                anio_target -= 1

            for tipo, desc, monto, dia in registros:
                cat = cat_ing if tipo == 'INGRESO' else cat_egr
                # Verificar que el dia exista en ese mes
                import calendar
                ultimo_dia = calendar.monthrange(anio_target, mes_target)[1]
                dia_real = min(dia, ultimo_dia)
                fecha_destino = date(anio_target, mes_target, dia_real)

                # Crear con fecha de hoy primero (auto_now_add no permite otra cosa)
                mov = Movimiento.objects.create(
                    usuario=user,
                    tipo=tipo,
                    categoria=cat,
                    descripcion=desc,
                    monto=monto,
                    activo=True,
                )
                # Luego pisar fecha_registro con update() que bypasea auto_now_add
                Movimiento.objects.filter(pk=mov.pk).update(
                    fecha_registro=fecha_destino
                )
                creados += 1

        print(f"Creados {creados} movimientos en los ultimos 3 meses.")
        print("Ahora recalcula los resumenes:")
        print()
        print("  from dashboard.services import actualizar_resumen")
        print("  from movimientos.models import Movimiento")
        print("  from django.db.models import Min")
        print("  fechas = Movimiento.objects.filter(usuario=user).values_list('fecha_registro', flat=True)")
        print("  meses = set((f.month, f.year) for f in fechas)")
        print("  [actualizar_resumen(user, m, a) for m, a in meses]")
        print("  print('Resumenes actualizados.')")