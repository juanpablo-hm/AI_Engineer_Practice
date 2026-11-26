"""Reto Clase 6: crear_ticket idempotente."""

from __future__ import annotations

from agents.tools import POLITICAS, ToolRunner
from contracts.tool_schemas import BUSCAR_TICKET, CREAR_TICKET, BuscarTicketArgs, CrearTicketArgs
from tools.tickets import buscar_ticket, crear_ticket, idempotency_key

ARGS = CrearTicketArgs(
    asunto="Portal de pagos rechaza tarjetas",
    descripcion="Desde hoy el portal rechaza todas las tarjetas de crédito.",
    prioridad="alta",
)


def test_mismo_request_crea_un_solo_ticket():
    primero = crear_ticket(ARGS, request_id="r1")
    segundo = crear_ticket(ARGS, request_id="r1")
    assert primero["id"] == segundo["id"] == "T-2001"
    assert primero["duplicado_evitado"] is False
    assert segundo["duplicado_evitado"] is True


def test_otro_request_crea_otro_ticket():
    a = crear_ticket(ARGS, request_id="r1")
    b = crear_ticket(ARGS, request_id="r2")
    assert a["id"] != b["id"]


def test_llave_ignora_mayusculas_acentos_y_espacios():
    assert idempotency_key("r1", "Portal de pagos", "Rechaza tarjetas") == idempotency_key(
        "r1", "Pórtal  DE Pagos", "rechaza TarjetAS"
    )


def test_buscar_ticket_encuentra_el_nuevo():
    nuevo = crear_ticket(ARGS, request_id="r1")
    encontrado = buscar_ticket(BuscarTicketArgs(ticket_id=nuevo["id"]))
    assert encontrado["asunto"] == ARGS.asunto


def test_politica_es_escritura_idempotente():
    politica = POLITICAS["crear_ticket"]
    assert politica.permiso == "escritura"
    assert politica.idempotente is True


def test_el_modelo_no_ve_request_id():
    assert set(CrearTicketArgs.model_fields) == {"asunto", "descripcion", "prioridad"}


def test_runner_inyecta_request_id():
    runner = ToolRunner([CREAR_TICKET, BUSCAR_TICKET], rol="operador", request_id="sesion-x")
    a = runner.call("crear_ticket", ARGS.model_dump())
    b = runner.call("crear_ticket", ARGS.model_dump())
    assert a["id"] == b["id"]
    assert b["duplicado_evitado"] is True


def test_rol_lectura_no_puede_crear():
    runner = ToolRunner([CREAR_TICKET], rol="lectura")
    result = runner.call("crear_ticket", ARGS.model_dump())
    assert result["error"]["tipo"] == "permiso"
