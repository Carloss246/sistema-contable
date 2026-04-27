-- Catalogo de cuentas segun las tablas compartidas (Elementos 1 al 8).
-- Nota: las cuentas en blanco de la imagen (15, 53, 54, 55, 86) no se incluyen.

create temporary table if not exists tmp_catalogo_cuentas_seed (
    codigo varchar(20) primary key,
    nombre varchar(120) not null,
    grupo varchar(20) not null,
    saldo_normal varchar(10) not null
) on commit drop;

truncate table tmp_catalogo_cuentas_seed;

insert into tmp_catalogo_cuentas_seed (codigo, nombre, grupo, saldo_normal)
values
    -- Elemento 1: Cuentas del Activo
    ('10', 'Efectivo y equivalentes de efectivo', 'ACTIVO', 'DEBE'),
    ('11', 'Inversiones financieras', 'ACTIVO', 'DEBE'),
    ('12', 'Cuentas por cobrar comerciales - Terceros', 'ACTIVO', 'DEBE'),
    ('13', 'Cuentas por cobrar comerciales - Relacionadas', 'ACTIVO', 'DEBE'),
    ('14', 'Cuentas por cobrar al personal, a los accionistas (socios), directores y gerentes', 'ACTIVO', 'DEBE'),
    ('16', 'Cuentas por cobrar diversas - Terceros', 'ACTIVO', 'DEBE'),
    ('17', 'Cuentas por cobrar diversas - Relacionadas', 'ACTIVO', 'DEBE'),
    ('18', 'Servicios y otros contratados por anticipado', 'ACTIVO', 'DEBE'),
    ('19', 'Estimacion de cuentas de cobranza dudosa', 'ACTIVO', 'HABER'),

    -- Elemento 2: Cuentas del Activo
    ('20', 'Mercaderias', 'ACTIVO', 'DEBE'),
    ('21', 'Productos terminados', 'ACTIVO', 'DEBE'),
    ('22', 'Subproductos, desechos y desperdicios', 'ACTIVO', 'DEBE'),
    ('23', 'Productos en proceso', 'ACTIVO', 'DEBE'),
    ('24', 'Materias primas', 'ACTIVO', 'DEBE'),
    ('25', 'Materiales auxiliares, suministros y repuestos', 'ACTIVO', 'DEBE'),
    ('26', 'Envases y embalajes', 'ACTIVO', 'DEBE'),
    ('27', 'Activos no corrientes mantenidos para la venta', 'ACTIVO', 'DEBE'),
    ('28', 'Existencias por recibir', 'ACTIVO', 'DEBE'),
    ('29', 'Desvalorizacion de existencias', 'ACTIVO', 'HABER'),

    -- Elemento 3: Cuentas del Activo
    ('30', 'Inversiones mobiliarias', 'ACTIVO', 'DEBE'),
    ('31', 'Inversiones inmobiliarias', 'ACTIVO', 'DEBE'),
    ('32', 'Activos adquiridos en arrendamiento financiero', 'ACTIVO', 'DEBE'),
    ('33', 'Inmuebles, maquinaria y equipo', 'ACTIVO', 'DEBE'),
    ('34', 'Intangibles', 'ACTIVO', 'DEBE'),
    ('35', 'Activos biologicos', 'ACTIVO', 'DEBE'),
    ('36', 'Desvalorizacion de activo inmovilizado', 'ACTIVO', 'HABER'),
    ('37', 'Activo diferido', 'ACTIVO', 'DEBE'),
    ('38', 'Otros activos', 'ACTIVO', 'DEBE'),
    ('39', 'Depreciacion, amortizacion y agotamiento acumulados', 'ACTIVO', 'HABER'),

    -- Elemento 4: Cuentas del Pasivo
    ('40', 'Tributos, contraprestaciones y aportes al sistema de pensiones y de salud por pagar', 'PASIVO', 'HABER'),
    ('41', 'Remuneraciones y participaciones por pagar', 'PASIVO', 'HABER'),
    ('42', 'Cuentas por pagar comerciales - Terceros', 'PASIVO', 'HABER'),
    ('43', 'Cuentas por pagar comerciales - Relacionadas', 'PASIVO', 'HABER'),
    ('44', 'Cuentas por pagar a los accionistas (socios), directores y gerentes', 'PASIVO', 'HABER'),
    ('45', 'Obligaciones financieras', 'PASIVO', 'HABER'),
    ('46', 'Cuentas por pagar diversas - Terceros', 'PASIVO', 'HABER'),
    ('47', 'Cuentas por pagar diversas - Relacionadas', 'PASIVO', 'HABER'),
    ('48', 'Provisiones', 'PASIVO', 'HABER'),
    ('49', 'Pasivo diferido', 'PASIVO', 'HABER'),

    -- Elemento 5: Cuentas del Patrimonio
    ('50', 'Capital', 'CAPITAL', 'HABER'),
    ('51', 'Acciones de inversion', 'CAPITAL', 'HABER'),
    ('52', 'Capital adicional', 'CAPITAL', 'HABER'),
    ('56', 'Resultados no realizados', 'CAPITAL', 'HABER'),
    ('57', 'Excedente de revaluacion', 'CAPITAL', 'HABER'),
    ('58', 'Reservas', 'CAPITAL', 'HABER'),
    ('59', 'Resultados acumulados', 'CAPITAL', 'HABER'),

    -- Elemento 6: Cuentas de Gastos por naturaleza
    ('60', 'Compras', 'GASTO', 'DEBE'),
    ('61', 'Variacion de existencias', 'GASTO', 'DEBE'),
    ('62', 'Gastos de personal, directores y gerentes', 'GASTO', 'DEBE'),
    ('63', 'Gastos de servicios prestados por terceros', 'GASTO', 'DEBE'),
    ('64', 'Gastos por tributos', 'GASTO', 'DEBE'),
    ('65', 'Otros gastos de gestion', 'GASTO', 'DEBE'),
    ('66', 'Perdida por medicion de activos no financieros al valor razonable', 'GASTO', 'DEBE'),
    ('67', 'Gastos financieros', 'GASTO', 'DEBE'),
    ('68', 'Valuacion y deterioro de activos y provisiones', 'GASTO', 'DEBE'),
    ('69', 'Costo de ventas', 'GASTO', 'DEBE'),

    -- Elemento 7: Cuentas de Ingresos por naturaleza
    ('70', 'Ventas', 'INGRESO', 'HABER'),
    ('71', 'Variacion de la produccion almacenada', 'INGRESO', 'HABER'),
    ('72', 'Produccion de activo inmovilizado', 'INGRESO', 'HABER'),
    ('73', 'Descuentos, rebajas y bonificaciones obtenidos', 'INGRESO', 'HABER'),
    ('74', 'Descuentos, rebajas y bonificaciones concedidos', 'INGRESO', 'DEBE'),
    ('75', 'Otros ingresos de gestion', 'INGRESO', 'HABER'),
    ('76', 'Ganancia por medicion de activos no financieros al valor razonable', 'INGRESO', 'HABER'),
    ('77', 'Ingresos financieros', 'INGRESO', 'HABER'),
    ('78', 'Cargas cubiertas por provisiones', 'INGRESO', 'HABER'),
    ('79', 'Cargas imputables a cuentas de costos y gastos', 'INGRESO', 'HABER'),

    -- Elemento 8: Cuentas de saldos intermedios de gestion y determinacion de resultados
    ('80', 'Margen comercial', 'INGRESO', 'HABER'),
    ('81', 'Produccion del ejercicio', 'INGRESO', 'HABER'),
    ('82', 'Valor agregado', 'INGRESO', 'HABER'),
    ('83', 'Excedente bruto (insuficiencia bruta) de explotacion', 'INGRESO', 'HABER'),
    ('84', 'Resultado de explotacion', 'INGRESO', 'HABER'),
    ('85', 'Resultado antes de participaciones e impuestos', 'INGRESO', 'HABER'),
    ('87', 'Participaciones de los trabajadores', 'GASTO', 'DEBE'),
    ('88', 'Impuesto a la renta', 'GASTO', 'DEBE'),
    ('89', 'Determinacion del resultado del ejercicio', 'INGRESO', 'HABER');

update public.catalogo_cuentas c
set activa = false
where c.codigo not in (select codigo from tmp_catalogo_cuentas_seed);

insert into public.catalogo_cuentas (codigo, nombre, grupo, saldo_normal)
select codigo, nombre, grupo, saldo_normal
from tmp_catalogo_cuentas_seed
on conflict (codigo) do update
set
    nombre = excluded.nombre,
    grupo = excluded.grupo,
    saldo_normal = excluded.saldo_normal,
    activa = true;
