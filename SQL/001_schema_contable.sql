-- Sistema Contable - Esquema principal para Supabase (PostgreSQL)
-- Basado en flujo contable: diario -> mayor -> balanza -> estados financieros.

create extension if not exists pgcrypto;

-- Catalogo de cuentas
create table if not exists public.catalogo_cuentas (
    id uuid primary key default gen_random_uuid(),
    codigo varchar(20) not null unique,
    nombre varchar(120) not null,
    grupo varchar(20) not null check (grupo in ('ACTIVO', 'PASIVO', 'CAPITAL', 'INGRESO', 'GASTO')),
    saldo_normal varchar(10) not null check (saldo_normal in ('DEBE', 'HABER')),
    permite_movimientos boolean not null default true,
    activa boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_catalogo_cuentas_grupo on public.catalogo_cuentas(grupo);

-- Asiento contable (cabecera)
create table if not exists public.asientos (
    id uuid primary key default gen_random_uuid(),
    numero_asiento bigint generated always as identity unique,
    fecha date not null,
    descripcion text not null,
    fuente varchar(30) not null default 'MANUAL',
    creado_por varchar(80),
    created_at timestamptz not null default now()
);

create index if not exists idx_asientos_fecha on public.asientos(fecha);

-- Movimientos del asiento (detalle)
create table if not exists public.movimientos_asiento (
    id uuid primary key default gen_random_uuid(),
    asiento_id uuid not null references public.asientos(id) on delete cascade,
    linea int not null,
    cuenta_id uuid not null references public.catalogo_cuentas(id),
    descripcion text,
    debe numeric(14,2) not null default 0 check (debe >= 0),
    haber numeric(14,2) not null default 0 check (haber >= 0),
    created_at timestamptz not null default now(),
    constraint uq_movimientos_asiento_linea unique (asiento_id, linea),
    constraint chk_movimiento_un_lado check (
        (debe > 0 and haber = 0) or
        (haber > 0 and debe = 0)
    )
);

create index if not exists idx_movimientos_asiento_asiento_id on public.movimientos_asiento(asiento_id);
create index if not exists idx_movimientos_asiento_cuenta_id on public.movimientos_asiento(cuenta_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger trg_catalogo_cuentas_updated_at
before update on public.catalogo_cuentas
for each row
execute function public.set_updated_at();

-- Valida que todo asiento quede cuadrado (partida doble).
create or replace function public.validar_partida_doble()
returns trigger
language plpgsql
as $$
declare
    v_asiento_id uuid;
    v_total_debe numeric(14,2);
    v_total_haber numeric(14,2);
    v_lineas int;
begin
    v_asiento_id := coalesce(new.asiento_id, old.asiento_id);

    select
        coalesce(sum(debe), 0),
        coalesce(sum(haber), 0),
        count(*)
    into v_total_debe, v_total_haber, v_lineas
    from public.movimientos_asiento
    where asiento_id = v_asiento_id;

    if v_lineas < 2 then
        raise exception 'El asiento % debe tener al menos 2 movimientos', v_asiento_id;
    end if;

    if v_total_debe <> v_total_haber then
        raise exception 'Partida doble no cumple en asiento % (Debe=%, Haber=%)', v_asiento_id, v_total_debe, v_total_haber;
    end if;

    return null;
end;
$$;

create constraint trigger trg_validar_partida_doble
after insert or update or delete on public.movimientos_asiento
deferrable initially deferred
for each row
execute function public.validar_partida_doble();

-- Funcion para crear asiento con movimientos en una sola operacion atomica.
-- p_movimientos (jsonb) formato:
-- [
--   {"codigo_cuenta": "101", "descripcion": "Caja", "debe": 1000, "haber": 0},
--   {"codigo_cuenta": "301", "descripcion": "Capital", "debe": 0, "haber": 1000}
-- ]
create or replace function public.fn_registrar_asiento(
    p_fecha date,
    p_descripcion text,
    p_fuente varchar,
    p_creado_por varchar,
    p_movimientos jsonb
)
returns uuid
language plpgsql
as $$
declare
    v_asiento_id uuid;
    v_item jsonb;
    v_linea int := 1;
    v_cuenta_id uuid;
    v_debe numeric(14,2);
    v_haber numeric(14,2);
    v_total_debe numeric(14,2) := 0;
    v_total_haber numeric(14,2) := 0;
begin
    if p_movimientos is null or jsonb_typeof(p_movimientos) <> 'array' then
        raise exception 'p_movimientos debe ser un arreglo json';
    end if;

    if jsonb_array_length(p_movimientos) < 2 then
        raise exception 'El asiento debe tener al menos 2 movimientos';
    end if;

    insert into public.asientos (fecha, descripcion, fuente, creado_por)
    values (p_fecha, p_descripcion, coalesce(p_fuente, 'MANUAL'), p_creado_por)
    returning id into v_asiento_id;

    for v_item in select * from jsonb_array_elements(p_movimientos)
    loop
        select id into v_cuenta_id
        from public.catalogo_cuentas
        where codigo = (v_item ->> 'codigo_cuenta')
          and activa = true
          and permite_movimientos = true;

        if v_cuenta_id is null then
            raise exception 'Cuenta % no existe o no permite movimientos', (v_item ->> 'codigo_cuenta');
        end if;

        v_debe := coalesce((v_item ->> 'debe')::numeric, 0);
        v_haber := coalesce((v_item ->> 'haber')::numeric, 0);

        if v_debe < 0 or v_haber < 0 then
            raise exception 'Los importes no pueden ser negativos';
        end if;

        if (v_debe = 0 and v_haber = 0) or (v_debe > 0 and v_haber > 0) then
            raise exception 'Cada movimiento debe tener importe solo en Debe o en Haber';
        end if;

        insert into public.movimientos_asiento (
            asiento_id, linea, cuenta_id, descripcion, debe, haber
        ) values (
            v_asiento_id,
            v_linea,
            v_cuenta_id,
            v_item ->> 'descripcion',
            v_debe,
            v_haber
        );

        v_total_debe := v_total_debe + v_debe;
        v_total_haber := v_total_haber + v_haber;
        v_linea := v_linea + 1;
    end loop;

    if v_total_debe <> v_total_haber then
        raise exception 'Partida doble no cumple (Debe=%, Haber=%)', v_total_debe, v_total_haber;
    end if;

    return v_asiento_id;
end;
$$;

-- Vista: libro diario
create or replace view public.v_libro_diario as
select
    p.id as asiento_id,
    p.numero_asiento,
    p.fecha,
    p.descripcion as descripcion_asiento,
    p.fuente,
    p.creado_por,
    m.linea,
    c.codigo as codigo_cuenta,
    c.nombre as nombre_cuenta,
    m.descripcion as descripcion_movimiento,
    m.debe,
    m.haber
from public.asientos p
join public.movimientos_asiento m on m.asiento_id = p.id
join public.catalogo_cuentas c on c.id = m.cuenta_id
order by p.fecha, p.numero_asiento, m.linea;

-- Vista: movimientos de mayor por cuenta
create or replace view public.v_mayor as
select
    c.codigo as codigo_cuenta,
    c.nombre as nombre_cuenta,
    c.grupo,
    p.fecha,
    p.numero_asiento,
    p.descripcion as descripcion_asiento,
    m.linea,
    m.descripcion as descripcion_movimiento,
    m.debe,
    m.haber
from public.movimientos_asiento m
join public.asientos p on p.id = m.asiento_id
join public.catalogo_cuentas c on c.id = m.cuenta_id
order by c.codigo, p.fecha, p.numero_asiento, m.linea;

-- Vista: saldos por cuenta (base para balanza y estados)
create or replace view public.v_saldos_cuentas as
select
    c.codigo,
    c.nombre,
    c.grupo,
    c.saldo_normal,
    coalesce(sum(m.debe), 0)::numeric(14,2) as total_debe,
    coalesce(sum(m.haber), 0)::numeric(14,2) as total_haber,
    (coalesce(sum(m.debe), 0) - coalesce(sum(m.haber), 0))::numeric(14,2) as saldo_neto,
    case
        when c.saldo_normal = 'DEBE' then (coalesce(sum(m.debe), 0) - coalesce(sum(m.haber), 0))
        else (coalesce(sum(m.haber), 0) - coalesce(sum(m.debe), 0))
    end::numeric(14,2) as saldo_segun_naturaleza
from public.catalogo_cuentas c
left join public.movimientos_asiento m on m.cuenta_id = c.id
left join public.asientos p on p.id = m.asiento_id
where c.activa = true
group by c.codigo, c.nombre, c.grupo, c.saldo_normal
order by c.codigo;

-- Vista: balanza de comprobacion
create or replace view public.v_balanza_comprobacion as
select
    codigo,
    nombre,
    grupo,
    total_debe,
    total_haber,
    case when saldo_neto >= 0 then saldo_neto else 0 end::numeric(14,2) as saldo_deudor,
    case when saldo_neto < 0 then abs(saldo_neto) else 0 end::numeric(14,2) as saldo_acreedor
from public.v_saldos_cuentas
order by codigo;

-- Seguridad minima sugerida: permitir lectura para usuarios autenticados.
grant usage on schema public to anon, authenticated;
grant select on public.catalogo_cuentas, public.asientos, public.movimientos_asiento to authenticated;
grant select on public.v_libro_diario, public.v_mayor, public.v_saldos_cuentas, public.v_balanza_comprobacion to authenticated;
grant execute on function public.fn_registrar_asiento(date, text, varchar, varchar, jsonb) to authenticated;
